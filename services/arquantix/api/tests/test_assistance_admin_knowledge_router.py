"""Tests d'intégration du router admin ``/api/admin/assistance/knowledge``.

Couvre :
  - GET /summary (compteurs par topic + ALLOWED_TOPICS)
  - GET / (pagination + filtres topic / is_active / search)
  - GET /{slug} (détail, 404 si inconnu)
  - POST / (validation : slug invalide, topic inconnu, slug dup)
  - PUT /{slug} (champs partiels, 404, validation)
  - DELETE /{slug} (204, 404)
  - GET /preview-block (bloc Markdown avec / sans refresh)
  - Auth : 401/403 si X-Actor-Roles absent ou non-admin
  - Effet de bord : invalidate_cache appelé après chaque mutation

Les tests utilisent la fixture transactionnelle ``client`` du conftest qui
roll back tout INSERT/UPDATE en fin de test.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin-knowledge@example.com",
    "X-Actor-Roles": "admin",
}

OPS_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-ops-knowledge@example.com",
    "X-Actor-Roles": "ops",
}

CLIENT_HEADERS = {
    "X-Actor-Type": "user",
    "X-Actor-Id": "test-user@example.com",
    "X-Actor-Roles": "client",
}


BASE = "/api/admin/assistance/knowledge"


def _create_payload(slug: str = "kind_test_buy_xyz", **overrides) -> dict:
    base = {
        "slug": slug,
        "topic": "transaction_kind",
        "title": "Achat XYZ (test)",
        "body": "Type de transaction de test pour le router admin.",
        "metadata": {
            "code": "buy_xyz",
            "label_fr": "Achat XYZ",
            "direction": "trade",
            "linked_knowledge_slug": "swap_settlement_immediate",
            "display_order": 99,
        },
        "is_active": True,
    }
    base.update(overrides)
    return base


# ───────────────────────────────────── Auth ─────────────────────────────────


class TestAuth:
    def test_no_headers_rejected(self, client: TestClient):
        res = client.get(f"{BASE}/")
        assert res.status_code in (401, 403)

    def test_client_role_rejected(self, client: TestClient):
        res = client.get(f"{BASE}/", headers=CLIENT_HEADERS)
        assert res.status_code in (401, 403)

    def test_admin_role_accepted(self, client: TestClient):
        res = client.get(f"{BASE}/", headers=ADMIN_HEADERS)
        assert res.status_code == 200

    def test_ops_role_accepted(self, client: TestClient):
        res = client.get(f"{BASE}/", headers=OPS_HEADERS)
        assert res.status_code == 200


# ─────────────────────────────────── Summary ────────────────────────────────


class TestSummary:
    def test_returns_topics_and_allowed_list(self, client: TestClient):
        res = client.get(f"{BASE}/summary", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        body = res.json()
        assert "by_topic" in body
        assert "allowed_topics" in body
        # Au minimum les 4 topics autorisés sont déclarés.
        assert {"transaction_kind", "definition", "delay", "faq"}.issubset(
            set(body["allowed_topics"])
        )


# ──────────────────────────────────── List ──────────────────────────────────


class TestList:
    def test_lists_with_pagination(self, client: TestClient):
        res = client.get(
            f"{BASE}/?skip=0&limit=5", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        assert "items" in body and "total" in body
        assert body["skip"] == 0
        assert body["limit"] == 5
        assert len(body["items"]) <= 5

    def test_filter_by_topic(self, client: TestClient):
        res = client.get(
            f"{BASE}/?topic=delay", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["topic"] == "delay"

    def test_filter_by_is_active(self, client: TestClient):
        res = client.get(
            f"{BASE}/?is_active=true", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["is_active"] is True

    def test_search_substring(self, client: TestClient):
        # Search un substring sans accent présent en slug + body.
        # Les rows seedées en C.1 incluent crypto, vault, etc.
        res = client.get(
            f"{BASE}/?search=crypto&limit=200", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        items = res.json()["items"]
        assert items, "search 'crypto' should match seeded rows"


# ─────────────────────────────────── Detail ─────────────────────────────────


class TestDetail:
    def test_existing_slug_returns_200(self, client: TestClient):
        res = client.get(
            f"{BASE}/product_basics_vault", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        assert body["slug"] == "product_basics_vault"
        assert body["topic"] == "definition"
        assert "body" in body

    def test_unknown_slug_returns_404(self, client: TestClient):
        res = client.get(
            f"{BASE}/does-not-exist-xyz", headers=ADMIN_HEADERS
        )
        assert res.status_code == 404


# ─────────────────────────────────── Create ─────────────────────────────────


class TestCreate:
    def test_create_then_get(self, client: TestClient):
        payload = _create_payload(slug="kind_test_create_xyz")
        with patch(
            "services.assistance.admin_knowledge_router.invalidate_catalog_cache"
        ) as mock_inv:
            res = client.post(
                f"{BASE}/", json=payload, headers=ADMIN_HEADERS
            )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["slug"] == payload["slug"]
        assert body["metadata"]["code"] == "buy_xyz"
        # Cache invalidé après commit
        mock_inv.assert_called_once()

        # Lookup confirme que la row existe (transaction de test → rollback à la fin)
        res2 = client.get(
            f"{BASE}/{payload['slug']}", headers=ADMIN_HEADERS
        )
        assert res2.status_code == 200

    def test_invalid_slug_400(self, client: TestClient):
        payload = _create_payload(slug="UPPERCASE")
        res = client.post(f"{BASE}/", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 400

    def test_invalid_topic_400(self, client: TestClient):
        payload = _create_payload(slug="kind_test_topic", topic="not_a_real_topic")
        res = client.post(f"{BASE}/", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 400

    def test_duplicate_slug_400(self, client: TestClient):
        payload = _create_payload(slug="product_basics_vault")  # déjà seedé
        res = client.post(f"{BASE}/", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 400
        assert "exists" in res.text.lower()

    def test_missing_body_422(self, client: TestClient):
        # Pydantic refuse body vide → 422
        payload = _create_payload(slug="kind_test_empty_body", body="")
        res = client.post(f"{BASE}/", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 422


# ─────────────────────────────────── Update ─────────────────────────────────


class TestUpdate:
    def _seed(self, client: TestClient, slug: str = "kind_test_update_zzz") -> dict:
        payload = _create_payload(slug=slug)
        res = client.post(f"{BASE}/", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 201, res.text
        return res.json()

    def test_update_partial_title(self, client: TestClient):
        self._seed(client)
        with patch(
            "services.assistance.admin_knowledge_router.invalidate_catalog_cache"
        ) as mock_inv:
            res = client.put(
                f"{BASE}/kind_test_update_zzz",
                json={"title": "Nouveau titre"},
                headers=ADMIN_HEADERS,
            )
        assert res.status_code == 200, res.text
        assert res.json()["title"] == "Nouveau titre"
        mock_inv.assert_called_once()

    def test_update_unknown_404(self, client: TestClient):
        res = client.put(
            f"{BASE}/does-not-exist",
            json={"title": "X"},
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 404

    def test_update_invalid_topic_400(self, client: TestClient):
        self._seed(client, slug="kind_test_update_invtopic")
        res = client.put(
            f"{BASE}/kind_test_update_invtopic",
            json={"topic": "garbage"},
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 400

    def test_toggle_is_active(self, client: TestClient):
        self._seed(client, slug="kind_test_update_toggle")
        res = client.put(
            f"{BASE}/kind_test_update_toggle",
            json={"is_active": False},
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is False


# ─────────────────────────────────── Delete ─────────────────────────────────


class TestDelete:
    def test_delete_existing(self, client: TestClient):
        # Seed
        slug = "kind_test_delete_zzz"
        client.post(
            f"{BASE}/", json=_create_payload(slug=slug), headers=ADMIN_HEADERS
        )
        # Delete
        with patch(
            "services.assistance.admin_knowledge_router.invalidate_catalog_cache"
        ) as mock_inv:
            res = client.delete(f"{BASE}/{slug}", headers=ADMIN_HEADERS)
        assert res.status_code == 204
        mock_inv.assert_called_once()
        # Lookup → 404
        res2 = client.get(f"{BASE}/{slug}", headers=ADMIN_HEADERS)
        assert res2.status_code == 404

    def test_delete_unknown_404(self, client: TestClient):
        res = client.delete(f"{BASE}/does-not-exist", headers=ADMIN_HEADERS)
        assert res.status_code == 404


# ───────────────────────────────── Preview ──────────────────────────────────


class TestPreviewBlock:
    def test_returns_block_for_seeded_db(self, client: TestClient):
        res = client.get(
            f"{BASE}/preview-block?refresh=true", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        # En base seedée (C.1) il y a 13 transaction_kind + 6 product_basics.
        assert body["is_empty"] is False
        assert body["chars"] > 0
        assert body["lines"] > 0
        assert "Catalogue Vancelian" in (body["block"] or "")

    def test_refresh_flag_invalidates_cache(self, client: TestClient):
        with patch(
            "services.assistance.admin_knowledge_router.invalidate_catalog_cache"
        ) as mock_inv:
            client.get(
                f"{BASE}/preview-block?refresh=true", headers=ADMIN_HEADERS
            )
        mock_inv.assert_called_once()

    def test_no_refresh_does_not_invalidate(self, client: TestClient):
        with patch(
            "services.assistance.admin_knowledge_router.invalidate_catalog_cache"
        ) as mock_inv:
            client.get(
                f"{BASE}/preview-block", headers=ADMIN_HEADERS
            )
        mock_inv.assert_not_called()

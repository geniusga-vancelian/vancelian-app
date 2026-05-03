"""Tests unitaires de ``compliance_repo.fetch_transactions_list``.

On capture les arguments passés à ``db.execute(text(sql), params)`` pour
valider que :

  - les filtres ``category`` (deposits/withdrawals/cards/crypto/
    bank_transfer) produisent les bonnes clauses SQL ;
  - les filtres ``direction`` / ``status`` / ``since`` sont injectés ;
  - le clamp du ``limit`` (1..50) s'applique ;
  - un ``client_id`` invalide retourne ``[]`` sans toucher la DB.

Aucun accès Postgres : ``db.execute`` est un MagicMock.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from services.assistance.agents.repositories import compliance_repo


def _capture_db():
    """Mock de Session qui :
      - capture chaque appel ``execute(stmt, params)``
      - retourne 1 ligne canonique côté ``fetchall()``.
    """
    db = MagicMock()
    captured: dict[str, object] = {}

    canonical_row = MagicMock()
    canonical_row.id = "11111111-1111-1111-1111-111111111111"
    canonical_row.transaction_type = "deposit"
    canonical_row.transaction_kind = "bank_transfer_in"
    canonical_row.direction = "credit"
    canonical_row.status = "completed"
    canonical_row.amount = Decimal("42.00")
    canonical_row.currency = "EUR"
    canonical_row.created_at = datetime(2026, 5, 3, tzinfo=timezone.utc)

    def _execute(stmt, params=None):
        captured["sql"] = str(stmt)
        captured["params"] = params or {}
        result = MagicMock()
        result.fetchall.return_value = [canonical_row]
        return result

    db.execute.side_effect = _execute
    return db, captured


class TestNoClient:
    def test_invalid_client_id_returns_empty(self):
        out = compliance_repo.fetch_transactions_list(
            MagicMock(), client_id="not-a-uuid"
        )
        assert out == []

    def test_none_client_id_returns_empty(self):
        out = compliance_repo.fetch_transactions_list(
            MagicMock(), client_id=None
        )
        assert out == []


class TestCategoryMapping:
    def test_deposits_filters_direction_credit(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), category="deposits"
        )
        params = captured["params"]
        assert params.get("cat_direction") == "credit"
        assert "ct.direction = :cat_direction" in captured["sql"]

    def test_withdrawals_filters_direction_debit(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), category="withdrawals"
        )
        assert captured["params"].get("cat_direction") == "debit"

    def test_cards_filters_kind_card_in(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), category="cards"
        )
        params = captured["params"]
        assert any(
            v == "card_in" for k, v in params.items() if k.startswith("kind_")
        )
        assert "ct.transaction_kind IN" in captured["sql"]

    def test_bank_transfer_filters_two_kinds(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), category="bank_transfer"
        )
        params = captured["params"]
        kinds = [
            v for k, v in params.items() if k.startswith("kind_")
        ]
        assert "bank_transfer_in" in kinds
        assert "bank_transfer_out" in kinds

    def test_unknown_category_no_filter(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), category="rubbish"
        )
        sql = captured["sql"]
        # Pas de clause sur kind/direction issue d'une category.
        assert ":cat_direction" not in sql
        assert ":kind_0" not in sql


class TestExtraFilters:
    def test_direction_override(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), direction="debit"
        )
        assert captured["params"].get("direction") == "debit"
        assert "ct.direction = :direction" in captured["sql"]

    def test_invalid_direction_silently_dropped(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), direction="sideways"
        )
        assert "direction" not in captured["params"]

    def test_status_filter(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), status="pending"
        )
        assert captured["params"].get("status") == "pending"

    def test_invalid_status_silently_dropped(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), status="weird-state"
        )
        assert "status" not in captured["params"]

    def test_since_filter(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), since="2026-04-01"
        )
        assert captured["params"].get("since") == "2026-04-01"
        assert "ct.created_at >=" in captured["sql"]


class TestLimitClamp:
    def test_clamps_to_max_50(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), limit=999
        )
        assert captured["params"]["lim"] == 50

    def test_clamps_to_min_1(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4()), limit=0
        )
        assert captured["params"]["lim"] == 1

    def test_default_limit_20(self):
        db, captured = _capture_db()
        compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4())
        )
        assert captured["params"]["lim"] == 20


class TestRowMapping:
    def test_returns_dict_per_row(self):
        db, _ = _capture_db()
        out = compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4())
        )
        assert len(out) == 1
        item = out[0]
        for key in (
            "id",
            "transaction_type",
            "transaction_kind",
            "direction",
            "status",
            "amount",
            "currency",
            "created_at",
        ):
            assert key in item

    def test_sql_select_failure_returns_empty(self):
        db = MagicMock()
        db.execute.side_effect = RuntimeError("DB down")
        out = compliance_repo.fetch_transactions_list(
            db, client_id=str(uuid4())
        )
        assert out == []

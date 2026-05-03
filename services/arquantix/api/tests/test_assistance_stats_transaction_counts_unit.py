"""Tests unitaires du tool ``stats_transaction_counts`` — Phase 2c.5.

Couvre :
  - Absence de ``client_id`` → payload vide safe.
  - Mapping des labels FR par dimension (direction / status / kind / month).
  - Format du ``markdown_table`` selon la dimension demandée :
      * header column adapté ("Catégorie", "Statut", "Type", "Mois")
      * séparateur right-align sur la colonne Nombre
      * ligne *Total* uniquement si > 1 catégorie
  - Validation du ``group_by`` (valeur inconnue → ``direction``).
  - Propagation des filtres (``category``, ``direction``, ``status``,
    ``since``, ``group_by``) vers le repo.
  - Erreur repo → payload neutre avec ``error=repo_unavailable``.
  - ``filters_applied`` reflète les inputs.

Aucune dépendance Postgres : on mocke
``compliance_repo.fetch_transaction_counts``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.assistance.agents.tools.compliance import (
    stats_transaction_counts,
)
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(*, client_id: str | None = None) -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=client_id,
        person_id=None,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="compliance.transactional",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-stats-counts",
    )


# ─────────────────────────────────────────────────────────────────────
# A. No client_id → safe empty
# ─────────────────────────────────────────────────────────────────────


class TestNoClientContext:
    def test_returns_empty_payload(self):
        out = stats_transaction_counts.execute(_ctx(client_id=None))
        assert out["total"] == 0
        assert out["items"] == []
        assert "Aucune transaction" in out["markdown_table"]
        assert out["filters_applied"] == {}


# ─────────────────────────────────────────────────────────────────────
# B. Label mapping
# ─────────────────────────────────────────────────────────────────────


class TestLabelMapping:
    def _run(self, rows, *, group_by="direction"):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=rows,
        ):
            return stats_transaction_counts.execute(ctx, group_by=group_by)

    def test_direction_credit_label_fr(self):
        out = self._run([{"label": "credit", "count": 7}])
        assert out["items"][0]["label"] == "Entrées (dépôts)"

    def test_direction_debit_label_fr(self):
        out = self._run([{"label": "debit", "count": 2}])
        assert out["items"][0]["label"] == "Sorties (retraits)"

    def test_status_label_fr(self):
        out = self._run(
            [{"label": "pending", "count": 3}], group_by="status"
        )
        assert out["items"][0]["label"] == "En attente"

    def test_kind_label_fr_known(self):
        out = self._run(
            [{"label": "card_in", "count": 5}], group_by="kind"
        )
        assert out["items"][0]["label"] == "Dépôt par carte"

    def test_kind_label_humanized_when_unknown(self):
        out = self._run(
            [{"label": "weird_kind", "count": 1}], group_by="kind"
        )
        assert out["items"][0]["label"] == "Weird kind"

    def test_month_label_passes_through(self):
        out = self._run(
            [{"label": "2026-05", "count": 4}], group_by="month"
        )
        assert out["items"][0]["label"] == "2026-05"

    def test_unknown_status_label_falls_back_to_capitalized(self):
        out = self._run(
            [{"label": "weird", "count": 1}], group_by="status"
        )
        assert out["items"][0]["label"] == "Weird"

    def test_empty_label_falls_back_to_autre(self):
        out = self._run(
            [{"label": "", "count": 1}], group_by="status"
        )
        assert out["items"][0]["label"] == "Autre"


# ─────────────────────────────────────────────────────────────────────
# C. Markdown rendering
# ─────────────────────────────────────────────────────────────────────


class TestMarkdownRendering:
    def _run(self, rows, *, group_by="direction"):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=rows,
        ):
            return stats_transaction_counts.execute(ctx, group_by=group_by)

    def test_empty_rows_returns_message(self):
        out = self._run([])
        assert out["markdown_table"].startswith("_")
        assert "|" not in out["markdown_table"]

    def test_header_direction_default(self):
        out = self._run([{"label": "credit", "count": 7}])
        md = out["markdown_table"]
        assert "| Catégorie | Nombre |" in md
        assert "|---|---:|" in md

    def test_header_status_dimension(self):
        out = self._run(
            [{"label": "completed", "count": 5}], group_by="status"
        )
        assert "| Statut | Nombre |" in out["markdown_table"]

    def test_header_kind_dimension(self):
        out = self._run(
            [{"label": "card_in", "count": 5}], group_by="kind"
        )
        assert "| Type | Nombre |" in out["markdown_table"]

    def test_header_month_dimension(self):
        out = self._run(
            [{"label": "2026-05", "count": 5}], group_by="month"
        )
        assert "| Mois | Nombre |" in out["markdown_table"]

    def test_total_line_only_when_multi_rows(self):
        # 1 ligne → pas de total.
        out_single = self._run([{"label": "credit", "count": 7}])
        assert "_Total_" not in out_single["markdown_table"]

        # 2+ lignes → ligne total.
        out_multi = self._run(
            [
                {"label": "credit", "count": 7},
                {"label": "debit", "count": 3},
            ]
        )
        assert "_Total_" in out_multi["markdown_table"]
        assert "**10**" in out_multi["markdown_table"]

    def test_label_pipes_are_escaped(self):
        out = self._run(
            [{"label": "weird|kind", "count": 1}], group_by="kind"
        )
        # _humanize garde tel quel le label car il a déjà du contenu :
        # `weird|kind` → `Weird|kind` après capitalize → escape `\|`.
        assert "Weird\\|kind" in out["markdown_table"]


# ─────────────────────────────────────────────────────────────────────
# D. group_by validation
# ─────────────────────────────────────────────────────────────────────


class TestGroupByValidation:
    def test_unknown_group_by_falls_back_to_direction(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=[],
        ) as repo_mock:
            stats_transaction_counts.execute(ctx, group_by="not_a_dim")
        assert repo_mock.call_args.kwargs["group_by"] == "direction"

    def test_missing_group_by_defaults_to_direction(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=[],
        ) as repo_mock:
            stats_transaction_counts.execute(ctx)
        assert repo_mock.call_args.kwargs["group_by"] == "direction"


# ─────────────────────────────────────────────────────────────────────
# E. Filters propagation
# ─────────────────────────────────────────────────────────────────────


class TestFiltersPropagation:
    def test_passes_all_filters_to_repo(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=[],
        ) as repo_mock:
            stats_transaction_counts.execute(
                ctx,
                category="deposits",
                direction="credit",
                status="completed",
                since="2026-04-01",
                group_by="status",
            )
        kwargs = repo_mock.call_args.kwargs
        assert kwargs["category"] == "deposits"
        assert kwargs["direction"] == "credit"
        assert kwargs["status"] == "completed"
        assert kwargs["since"] == "2026-04-01"
        assert kwargs["group_by"] == "status"

    def test_filters_applied_includes_group_by(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=[],
        ):
            out = stats_transaction_counts.execute(
                ctx, category="cards", group_by="month"
            )
        assert out["filters_applied"]["group_by"] == "month"
        assert out["filters_applied"]["category"] == "cards"
        assert "direction" not in out["filters_applied"]


# ─────────────────────────────────────────────────────────────────────
# F. Total computation
# ─────────────────────────────────────────────────────────────────────


class TestTotalComputation:
    def test_total_is_sum_of_counts(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            return_value=[
                {"label": "credit", "count": 7},
                {"label": "debit", "count": 3},
            ],
        ):
            out = stats_transaction_counts.execute(ctx)
        assert out["total"] == 10


# ─────────────────────────────────────────────────────────────────────
# G. Repo error → graceful payload
# ─────────────────────────────────────────────────────────────────────


class TestRepoError:
    def test_returns_empty_with_error_marker(self):
        ctx = _ctx(client_id=str(uuid4()))
        with patch.object(
            stats_transaction_counts.compliance_repo,
            "fetch_transaction_counts",
            side_effect=RuntimeError("boom"),
        ):
            out = stats_transaction_counts.execute(ctx)
        assert out["total"] == 0
        assert out["items"] == []
        assert out["error"] == "repo_unavailable"
        assert "Aucune transaction" in out["markdown_table"]

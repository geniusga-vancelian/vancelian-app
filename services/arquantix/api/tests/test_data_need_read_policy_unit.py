"""PR3 — agrégation ``data_need`` vs tools appelés."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from services.assistance.data_need_read_policy import (
    data_need_reads_satisfied,
    maybe_audit_data_need_read_gap,
)


@pytest.mark.parametrize(
    "need,tools,ok",
    [
        ("transaction_data", ("list_transactions",), True),
        ("transaction_data", ("read_wiki_page",), False),
        ("account_data", ("read_compliance_state",), True),
        ("kyc_data", ("read_registration_progress",), True),
        ("none", (), True),
    ],
)
def test_data_need_reads_satisfied(need, tools, ok):
    assert data_need_reads_satisfied(need, tools) is ok


def test_maybe_audit_triggers_on_gap(monkeypatch):
    calls: list = []

    def _fake_persist(db, **kw):
        calls.append(kw)
        return str(uuid.uuid4())

    monkeypatch.setattr(
        "services.assistance.agents.tools.shared.audit.persist_decision",
        _fake_persist,
    )
    db = MagicMock()
    maybe_audit_data_need_read_gap(
        db,
        conversation_id=uuid.uuid4(),
        agent_id="compliance",
        orchestration={"data_need": "transaction_data"},
        tools_called_sequence=("read_wiki_page",),
        correlation_id="corr-1",
        iteration=2,
        early_break_reason="final_answer",
    )
    assert len(calls) == 1
    assert calls[0]["tool_name"] == "policy_data_need_reads"
    assert calls[0]["error_code"] == "policy_soft_warn"
    assert calls[0]["arguments"]["data_need"] == "transaction_data"


def test_maybe_audit_skips_when_satisfied(monkeypatch):
    calls: list = []

    def _fake_persist(db, **kw):
        calls.append(kw)

    monkeypatch.setattr(
        "services.assistance.agents.tools.shared.audit.persist_decision",
        _fake_persist,
    )
    maybe_audit_data_need_read_gap(
        MagicMock(),
        conversation_id=uuid.uuid4(),
        agent_id="compliance",
        orchestration={"data_need": "transaction_data"},
        tools_called_sequence=("list_transactions",),
        correlation_id=None,
        iteration=0,
        early_break_reason="final_answer",
    )
    assert calls == []

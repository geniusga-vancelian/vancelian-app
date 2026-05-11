"""Tests — payload admin pour l’agent ``action``."""

from __future__ import annotations

from services.assistance.agent_action_options_catalog import (
    build_agent_action_options_payload,
)
from services.assistance.agents.tools.registry import all_tool_names
from services.assistance.agents.tools.shared.action_cta_catalog import (
    catalog_entries_for_admin,
)


def test_catalog_entries_for_admin_matches_known_kinds():
    rows = catalog_entries_for_admin()
    kinds = [r["kind"] for r in rows]
    assert "deposit_funds" in kinds
    assert "markets_crypto" in kinds
    assert rows == sorted(rows, key=lambda r: r["kind"])


def test_build_agent_action_options_payload_shape():
    p = build_agent_action_options_payload()
    assert isinstance(p["doc_revision"], str)
    assert isinstance(p["source_files_note"], list)
    tool_names_backend = [
        row["tool_name"] for row in p["action_agent_tools"]
    ]
    for registered in all_tool_names("action"):
        assert registered in tool_names_backend

    kinds = [r["kind"] for r in p["cta_whitelist"]]
    assert kinds == sorted(kinds)


def test_action_tools_have_flow_steps_where_documented():
    p = build_agent_action_options_payload()
    by_name = {t["tool_name"]: t for t in p["action_agent_tools"]}

    deposit = by_name["deposit_present_channels"]
    assert len(deposit["client_flow_steps"]) >= 2
    assert "deposit_virement" in deposit["related_cta_kinds"]

    buy = by_name["crypto_buy_start"]
    assert buy["related_cta_kinds"]

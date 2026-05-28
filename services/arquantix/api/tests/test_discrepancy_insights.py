"""Tests insights ops — provenance et risque auto-fix."""
from __future__ import annotations

from services.onchain_reconciliation.discrepancy_insights import (
    build_explorer_links,
    infer_auto_fix_risk,
    infer_likely_sources,
)


def test_balance_eth_dust_sources():
    sources = infer_likely_sources(
        discrepancy_type="balance_ledger_vs_onchain",
        layer="privy",
        asset="ETH",
        db_amount="0",
        onchain_amount="0.018",
    )
    assert any("Dust" in s or "gas" in s for s in sources)


def test_admin_sim_risk():
    risk = infer_auto_fix_risk(
        discrepancy_type="admin_sim_deposit",
        severity="P0",
    )
    assert risk["level"] == "potential_double_credit_risk"


def test_basescan_link():
    links = build_explorer_links(chain_id=8453, tx_hash="0xabc123")
    assert links["explorer_tx_url"] == "https://basescan.org/tx/0xabc123"
    assert links["explorer_label"] == "Basescan"

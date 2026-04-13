"""Phase 1.5 — Family A: Compatibility tests for future lending introduction.

These tests verify that existing spot flows remain IDENTICAL after lending
atoms are introduced in Phase 2. They are skipped until Phase 2 implementation.

Each test captures the "before" state (spot-only), introduces a lending atom,
then verifies the "after" state for spot flows is unchanged.
"""
import pytest

PHASE2_REASON = "Phase 2 not yet implemented — lending not enabled"


@pytest.mark.skip(reason=PHASE2_REASON)
class TestBuyStillSpotOnly:
    def test_buy_produces_spot_atom_with_lending_present(self, db):
        """BUY BTC must create position_type=spot even when lending atoms exist."""

    def test_buy_does_not_affect_lending_atoms(self, db):
        """BUY BTC must not modify any existing lending atom."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestSellStillSpotOnly:
    def test_sell_produces_spot_atom_with_lending_present(self, db):
        """SELL BTC must only decrement spot atoms, not lending."""

    def test_sell_does_not_affect_lending_atoms(self, db):
        """SELL BTC must not modify any existing lending atom."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestSwapStillSpotOnly:
    def test_swap_produces_spot_atoms_with_lending_present(self, db):
        """SWAP BTC→ETH must create/update spot atoms only."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestBundleInvestStillSpotCash:
    def test_bundle_invest_produces_spot_and_cash_only(self, db):
        """Bundle invest must only create spot+cash atoms, ignoring lending."""

    def test_bundle_invest_does_not_affect_lending_atoms(self, db):
        """Bundle invest must not modify any existing lending atom."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestBundleRebalanceStillSpotCash:
    def test_rebalance_preserves_spot_cash_only(self, db):
        """Bundle rebalance must only modify spot+cash atoms."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestCryptoPositionsUnchanged:
    def test_crypto_positions_unchanged_by_lending_atom(self, db):
        """Creating a lending atom must NOT change crypto_positions.balance."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestValuationUnchanged:
    def test_valuation_unchanged_for_spot_only_client(self, db):
        """get_portfolio_breakdown must return identical values for a
        client that has only spot positions, regardless of other clients
        having lending atoms."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestStatisticsUnchanged:
    def test_wallet_statistics_unchanged_for_spot_only_client(self, db):
        """build_wallet_statistics for a spot-only client must be identical
        before and after lending atoms exist in the system."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestHistoryUnchanged:
    def test_wallet_history_unchanged_for_spot_only_client(self, db):
        """build_wallet_history for a spot-only client must be identical."""

    def test_global_history_unchanged_for_spot_only_client(self, db):
        """build_global_history for a spot-only client must be identical."""

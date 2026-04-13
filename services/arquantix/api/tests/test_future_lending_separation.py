"""Phase 1.5 — Family B: Separation tests for future lending introduction.

These tests verify that lending atoms NEVER leak into spot views.
They are skipped until Phase 2 implementation.

Each test creates a lending atom and verifies it does NOT appear in
spot-specific queries, views, or calculations.
"""
import pytest

PHASE2_REASON = "Phase 2 not yet implemented — lending not enabled"


@pytest.mark.skip(reason=PHASE2_REASON)
class TestLendingNotInCryptoPositions:
    def test_lending_atom_not_in_crypto_positions(self, db):
        """A lending atom must NOT cause crypto_positions.balance to change.
        crypto_positions is strictly for spot holdings."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestLendingNotInWalletHistory:
    def test_lending_atom_not_in_wallet_history(self, db):
        """wallet_history (NAV curve) must not include lending atoms.
        It reconstructs from ExchangeOrder which is spot-only."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestLendingNotInSpotValuation:
    def test_lending_atom_excluded_from_compute_atoms_value(self, db):
        """_compute_atoms_value must filter position_type and exclude lending.
        CRITICAL: currently no filter exists — this test will FAIL until
        valuation.py is updated in Phase 2."""

    def test_portfolio_breakdown_excludes_lending_from_spot_value(self, db):
        """get_portfolio_breakdown must report lending separately or exclude it
        from the spot crypto_value line."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestLendingNotInDirectWalletView:
    def test_lending_atom_not_in_direct_crypto_positions(self, db):
        """get_direct_crypto_positions already filters position_type=spot.
        Verify lending atoms are excluded."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestLendingNotCountedAsSpot:
    def test_lending_atom_not_counted_in_spot_sum(self, db):
        """Any query summing spot atoms must exclude lending."""

    def test_lending_atom_not_in_scoped_position_size(self, db):
        """_get_scoped_position_size already filters position_type=spot.
        Verify lending atoms are excluded for direct/bundle scopes."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestBundleViewsCoherent:
    def test_bundle_views_coherent_with_lending_present(self, db):
        """mobile_bundle_statistics and mobile_my_bundles must not include
        lending atoms in asset counts or allocation values."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestInvariantFWithLending:
    def test_invariant_f_holds_with_lending_atoms_present(self, db):
        """check_invariant_f compares Σ spot atoms to crypto_positions.
        Lending atoms must not affect this comparison.
        This holds as long as crypto_positions stays spot-only."""


@pytest.mark.skip(reason=PHASE2_REASON)
class TestSumPortfolioValueSeparation:
    def test_sum_portfolio_value_excludes_lending(self, db):
        """_sum_portfolio_value treats non-cash atoms as spot.
        CRITICAL: lending atoms would be valued as spot without a fix.
        This test will FAIL until _sum_portfolio_value adds a lending branch."""

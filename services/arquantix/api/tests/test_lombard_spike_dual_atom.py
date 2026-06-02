"""Mini-spike Phase 3B — contrainte unique open atoms (portfolio_id, instrument_id)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from tests.conftest import make_linked_client
from tests.test_bundle_lifi_funding import _instrument_usdc


def test_spike_spot_and_collateral_same_instrument_blocked(db: Session):
    """Confirms ix_pe_position_atoms_unique_open blocks dual open atoms."""
    pe = make_linked_client(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    instrument = _instrument_usdc(db)

    sync_direct_atom(db, direct_pf.id, instrument.id, Decimal("0.001"), Decimal("1"))
    db.flush()

    collateral = PositionAtom(
        portfolio_id=direct_pf.id,
        instrument_id=instrument.id,
        position_type=PositionType.COLLATERAL.value,
        status="open",
        quantity=Decimal("0.000125"),
        available_quantity=Decimal("0.000125"),
        metadata_={"scope": "trading_locked_collateral", "lock_reason": "lombard"},
    )
    db.add(collateral)
    with pytest.raises(IntegrityError):
        db.flush()

#!/usr/bin/env python3
"""Backfill pe_wallet_containers + PositionAtom.wallet_id for bundle/direct portfolios."""
from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill virtual wallet IDs")
    parser.add_argument("--portfolio-id", required=True, help="PE portfolio UUID")
    parser.add_argument("--client-id", required=True, help="PE client UUID")
    parser.add_argument(
        "--entry-instrument-id",
        default=None,
        help="Cash leg instrument UUID (bundle portfolios)",
    )
    parser.add_argument(
        "--spot-instrument-ids",
        nargs="*",
        default=[],
        help="Spot instrument UUIDs to provision",
    )
    args = parser.parse_args()

    from uuid import UUID

    from database import SessionLocal
    from services.portfolio_engine.wallets.resolver import (
        backfill_position_atom_wallet_ids,
        ensure_portfolio_wallets,
    )

    portfolio_id = UUID(args.portfolio_id)
    client_id = UUID(args.client_id)
    entry_id = UUID(args.entry_instrument_id) if args.entry_instrument_id else None
    spot_ids = [UUID(x) for x in args.spot_instrument_ids]

    db = SessionLocal()
    try:
        wallets = ensure_portfolio_wallets(
            db,
            portfolio_id=portfolio_id,
            client_id=client_id,
            spot_instrument_ids=spot_ids,
            entry_instrument_id=entry_id,
        )
        linked = backfill_position_atom_wallet_ids(
            db,
            portfolio_id=portfolio_id,
            client_id=client_id,
        )
        db.commit()
        logger.info("wallets=%s atoms_linked=%s", wallets, linked)
        return 0
    except Exception:
        db.rollback()
        logger.exception("backfill_failed")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

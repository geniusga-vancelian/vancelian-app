#!/usr/bin/env python3
"""Audit prod — swaps LINK confirmés + atoms PE (lecture seule)."""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))
os.chdir(api_dir)

import main  # noqa: F401

from sqlalchemy import or_

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    bundle_context_for_swap,
    is_bundle_internal_swap,
)
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit

INFLATION = Decimal("1000")


def main() -> None:
    db = SessionLocal()
    try:
        swaps = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
                or_(
                    PersonWalletSwap.to_asset == "LINK",
                    PersonWalletSwap.from_asset == "LINK",
                ),
            )
            .order_by(PersonWalletSwap.updated_at.desc())
            .limit(30)
            .all()
        )
        print(f"CONFIRMED swaps involving LINK: {len(swaps)}")
        for s in swaps:
            est = Decimal(str(s.estimated_receive or 0))
            ctx = bundle_context_for_swap(s) or {}
            internal = is_bundle_internal_swap(s)
            note = ""
            if est > 0:
                audit = s.audit_json if isinstance(s.audit_json, list) else []
                for entry in audit:
                    if not isinstance(entry, dict):
                        continue
                    raw = entry.get("actual_receive_amount")
                    if raw is None:
                        continue
                    act = Decimal(str(raw))
                    if act / est >= INFLATION:
                        note = f" audit_inflated act={act}"
            batch = ctx.get("batch_id")
            portfolio = ctx.get("portfolio_id")
            print(
                f" swap={s.id} person={s.person_id} internal={internal} "
                f"from={s.from_asset} to={s.to_asset} est={est} "
                f"batch={batch} portfolio={portfolio}{note}"
            )

        deposits = (
            db.query(PersonWalletDeposit)
            .filter(
                PersonWalletDeposit.asset == "LINK",
                PersonWalletDeposit.direction == PersonWalletDirection.CREDIT.value,
                PersonWalletDeposit.status == PersonWalletDepositStatus.CONFIRMED.value,
            )
            .order_by(PersonWalletDeposit.confirmed_at.desc())
            .limit(20)
            .all()
        )
        print(f"LINK credit deposits: {len(deposits)}")
        for d in deposits:
            amt = Decimal(str(d.amount or 0))
            meta = d.metadata_json if isinstance(d.metadata_json, dict) else {}
            est = meta.get("swap_amount_to_estimated")
            flag = ""
            if est:
                e = Decimal(str(est))
                if e > 0 and amt / e >= INFLATION:
                    flag = " INFLATED"
            elif amt >= INFLATION:
                flag = " LARGE"
            print(
                f" deposit={d.id} person={d.person_id} kind={d.transaction_kind} "
                f"amt={amt}{flag} swap={meta.get('swap_id')}"
            )

        rows = (
            db.query(PositionAtom, Asset)
            .join(Instrument, Instrument.id == PositionAtom.instrument_id)
            .join(Asset, Asset.id == Instrument.asset_id)
            .filter(Asset.symbol == "LINK", PositionAtom.status == "open")
            .all()
        )
        print(f"OPEN LINK atoms: {len(rows)}")
        for atom, _asset in rows:
            qty = Decimal(str(atom.quantity or 0))
            flag = " HUGE" if qty >= Decimal("1000") else ""
            print(f" atom={atom.id} portfolio={atom.portfolio_id} qty={qty}{flag}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

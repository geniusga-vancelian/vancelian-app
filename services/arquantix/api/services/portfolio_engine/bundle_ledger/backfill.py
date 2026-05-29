"""Backfill idempotent ``bundle_ledger_entries`` depuis sources legacy (Phase 4B)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_pe_transactions import (
    AUDIT_ACTION_FUND,
    AUDIT_ACTION_RELEASE,
)
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundle_ledger.enums import (
    BundleLedgerDirection,
    BundleLedgerEventType,
    BundleLedgerSourceSystem,
)
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundle_ledger.service import (
    build_idempotency_key,
    record_allocation_buy,
    record_allocation_sell,
    record_bundle_deposit,
    record_bundle_withdrawal,
    record_rebalance,
)
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from services.transaction_intents.enums import IntentProductType

logger = logging.getLogger(__name__)


@dataclass
class BackfillPlanItem:
    action: str
    idempotency_key: str
    source: str
    source_id: str
    batch_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackfillResult:
    dry_run: bool
    portfolio_id: str
    person_id: str | None
    planned: list[BackfillPlanItem] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "portfolio_id": self.portfolio_id,
            "person_id": self.person_id,
            "planned_count": len(self.planned),
            "skipped_existing_count": len(self.skipped_existing),
            "applied_count": len(self.applied),
            "planned": [
                {
                    "action": p.action,
                    "idempotency_key": p.idempotency_key,
                    "source": p.source,
                    "source_id": p.source_id,
                    "batch_id": p.batch_id,
                    "metadata": p.metadata,
                }
                for p in self.planned
            ],
            "skipped_existing": self.skipped_existing,
            "applied": self.applied,
            "warnings": self.warnings,
        }


def _instrument_for_asset(db: Session, symbol: str) -> Instrument | None:
    asset = db.query(Asset).filter(Asset.symbol == symbol.upper()).first()
    if asset is None:
        return None
    return (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )


def _existing_keys(db: Session, *, portfolio_id: UUID) -> set[str]:
    rows = (
        db.query(BundleLedgerEntry.idempotency_key)
        .filter(BundleLedgerEntry.bundle_portfolio_id == portfolio_id)
        .all()
    )
    return {r[0] for r in rows}


def _swap_atoms_applied(swap: PersonWalletSwap) -> bool:
    audit = swap.audit_log if isinstance(swap.audit_log, list) else []
    return any(isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied" for e in audit)


def _leg_id_from_swap(swap: PersonWalletSwap) -> str | None:
    audit = swap.audit_log if isinstance(swap.audit_log, list) else []
    for entry in audit:
        if isinstance(entry, dict) and entry.get("leg_id"):
            return str(entry["leg_id"])
    return None


def _plan_deposit_from_audit(
    row: AuditEvent,
    *,
    person_id: UUID,
    client_id: UUID,
    portfolio_id: UUID,
    existing: set[str],
    result: BackfillResult,
) -> None:
    meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
    batch_id = str(meta.get("batch_id") or "").strip()
    if not batch_id:
        result.warnings.append(f"audit_fund_missing_batch_id audit_id={row.id}")
        return
    entry_asset = str(meta.get("entry_asset") or "USDC").upper()
    amount_raw = meta.get("amount")
    if amount_raw is None:
        result.warnings.append(f"audit_fund_missing_amount audit_id={row.id}")
        return
    amount = Decimal(str(amount_raw))
    if amount <= 0:
        return
    source_id = f"{batch_id}:fund"
    key = build_idempotency_key(
        source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
        source_id=source_id,
        event_type=BundleLedgerEventType.BUNDLE_DEPOSIT.value,
        direction=BundleLedgerDirection.CREDIT.value,
    )
    if key in existing:
        result.skipped_existing.append(key)
        return
    result.planned.append(
        BackfillPlanItem(
            action="record_bundle_deposit",
            idempotency_key=key,
            source="pe_audit_events",
            source_id=str(row.id),
            batch_id=batch_id,
            metadata={
                "entry_asset": entry_asset,
                "amount": float(amount),
                "person_id": str(person_id),
                "client_id": str(client_id),
                "portfolio_id": str(portfolio_id),
            },
        )
    )


def _plan_withdrawal_from_audit(
    row: AuditEvent,
    *,
    person_id: UUID,
    client_id: UUID,
    portfolio_id: UUID,
    existing: set[str],
    result: BackfillResult,
) -> None:
    meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
    batch_id = str(meta.get("batch_id") or "").strip()
    if not batch_id:
        result.warnings.append(f"audit_release_missing_batch_id audit_id={row.id}")
        return
    entry_asset = str(meta.get("entry_asset") or "USDC").upper()
    amount_raw = meta.get("amount")
    if amount_raw is None:
        result.warnings.append(f"audit_release_missing_amount audit_id={row.id}")
        return
    amount = Decimal(str(amount_raw))
    if amount <= 0:
        return
    source_id = f"{batch_id}:release"
    key = build_idempotency_key(
        source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
        source_id=source_id,
        event_type=BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
        direction=BundleLedgerDirection.DEBIT.value,
    )
    if key in existing:
        result.skipped_existing.append(key)
        return
    result.planned.append(
        BackfillPlanItem(
            action="record_bundle_withdrawal",
            idempotency_key=key,
            source="pe_audit_events",
            source_id=str(row.id),
            batch_id=batch_id,
            metadata={
                "entry_asset": entry_asset,
                "amount": float(amount),
                "person_id": str(person_id),
                "client_id": str(client_id),
                "portfolio_id": str(portfolio_id),
            },
        )
    )


def _plan_from_confirmed_swap(
    db: Session,
    swap: PersonWalletSwap,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    existing: set[str],
    result: BackfillResult,
) -> None:
    if not _swap_atoms_applied(swap):
        return
    ctx = bundle_context_from_swap_audit(swap)
    if not ctx:
        result.warnings.append(f"swap_missing_bundle_context swap_id={swap.id}")
        return
    if str(ctx.get("portfolio_id") or "") != str(portfolio_id):
        return
    batch_id = str(ctx.get("batch_id") or "")
    action = str(ctx.get("bundle_action") or ctx.get("leg_action") or "").strip().lower()
    if not action:
        result.warnings.append(f"swap_ambiguous_action swap_id={swap.id}")
        return

    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    amount_in = Decimal(str(swap.amount_in or 0))
    amount_out = Decimal(str(swap.estimated_receive or 0))
    if amount_in <= 0 or amount_out <= 0:
        result.warnings.append(f"swap_invalid_amounts swap_id={swap.id}")
        return

    leg_id = _leg_id_from_swap(swap)
    swap_id = swap.id

    if action == "allocation":
        keys = [
            build_idempotency_key(
                source_system=BundleLedgerSourceSystem.LIFI.value,
                source_id=str(swap_id),
                event_type=BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value,
                direction=BundleLedgerDirection.CREDIT.value,
            ),
            build_idempotency_key(
                source_system=BundleLedgerSourceSystem.LIFI.value,
                source_id=f"{swap_id}:cash",
                event_type=BundleLedgerEventType.BUNDLE_CASH_RELEASED.value,
                direction=BundleLedgerDirection.DEBIT.value,
            ),
        ]
        if all(k in existing for k in keys):
            result.skipped_existing.extend(keys)
            return
        entry_instr = _instrument_for_asset(db, from_asset)
        target_instr = _instrument_for_asset(db, to_asset)
        if entry_instr is None or target_instr is None:
            result.warnings.append(f"swap_missing_instruments swap_id={swap.id}")
            return
        result.planned.append(
            BackfillPlanItem(
                action="record_allocation_buy",
                idempotency_key=keys[0],
                source="person_wallet_swaps",
                source_id=str(swap_id),
                batch_id=batch_id or None,
                metadata={
                    "from_asset": from_asset,
                    "to_asset": to_asset,
                    "amount_in": float(amount_in),
                    "amount_out": float(amount_out),
                    "leg_id": leg_id,
                    "entry_instrument_id": str(entry_instr.id),
                    "target_instrument_id": str(target_instr.id),
                },
            )
        )
    elif action in ("rebalance_buy", "rebalance_sell", "withdraw_sell"):
        side = "buy" if action == "rebalance_buy" else "sell"
        if action == "withdraw_sell":
            sell_instr = _instrument_for_asset(db, from_asset)
            entry_instr = _instrument_for_asset(db, to_asset)
            if sell_instr is None or entry_instr is None:
                result.warnings.append(f"swap_missing_instruments swap_id={swap.id}")
                return
            keys = [
                build_idempotency_key(
                    source_system=BundleLedgerSourceSystem.LIFI.value,
                    source_id=str(swap_id),
                    event_type=BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
                    direction=BundleLedgerDirection.DEBIT.value,
                ),
                build_idempotency_key(
                    source_system=BundleLedgerSourceSystem.LIFI.value,
                    source_id=f"{swap_id}:cash_credit",
                    event_type=BundleLedgerEventType.BUNDLE_DEPOSIT.value,
                    direction=BundleLedgerDirection.CREDIT.value,
                ),
            ]
            if all(k in existing for k in keys):
                result.skipped_existing.extend(keys)
                return
            result.planned.append(
                BackfillPlanItem(
                    action="record_allocation_sell",
                    idempotency_key=keys[0],
                    source="person_wallet_swaps",
                    source_id=str(swap_id),
                    batch_id=batch_id or None,
                    metadata={
                        "from_asset": from_asset,
                        "to_asset": to_asset,
                        "sell_qty": float(amount_in),
                        "entry_received": float(amount_out),
                        "withdraw_sell": True,
                        "leg_id": leg_id,
                    },
                )
            )
            return

        spot_asset = to_asset if side == "buy" else from_asset
        entry_asset = from_asset if side == "buy" else to_asset
        spot_instr = _instrument_for_asset(db, spot_asset)
        entry_instr = _instrument_for_asset(db, entry_asset)
        if spot_instr is None or entry_instr is None:
            result.warnings.append(f"swap_missing_instruments swap_id={swap.id}")
            return
        event_type = (
            BundleLedgerEventType.BUNDLE_REBALANCE_BUY.value
            if side == "buy"
            else BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value
        )
        direction = (
            BundleLedgerDirection.CREDIT.value
            if side == "buy"
            else BundleLedgerDirection.DEBIT.value
        )
        key = build_idempotency_key(
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=str(swap_id),
            event_type=event_type,
            direction=direction,
        )
        if key in existing:
            result.skipped_existing.append(key)
            return
        result.planned.append(
            BackfillPlanItem(
                action="record_rebalance",
                idempotency_key=key,
                source="person_wallet_swaps",
                source_id=str(swap_id),
                batch_id=batch_id or None,
                metadata={
                    "side": side,
                    "spot_asset": spot_asset,
                    "entry_asset": entry_asset,
                    "quantity": float(amount_out if side == "buy" else amount_in),
                    "entry_amount": float(amount_in if side == "buy" else amount_out),
                    "leg_id": leg_id,
                },
            )
        )
    else:
        result.warnings.append(f"swap_unsupported_action action={action} swap_id={swap.id}")


def _scan_intents_for_warnings(
    intents: list[TransactionIntent],
    *,
    audit_batch_ids: set[str],
    result: BackfillResult,
) -> None:
    for intent in intents:
        meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
        batch = str(meta.get("batch_id") or intent.linked_reference_id or "").strip()
        if not batch:
            continue
        if batch not in audit_batch_ids and str(intent.status or "").lower() in {
            "confirmed", "partial", "released",
        }:
            result.warnings.append(
                f"intent_without_audit batch_id={batch} intent_id={intent.id} "
                f"product_type={intent.product_type}"
            )


def plan_backfill(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None = None,
) -> BackfillResult:
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        raise ValueError(f"bundle_portfolio_not_found: {portfolio_id}")

    client = db.query(Client).filter(Client.id == portfolio.client_id).first()
    if client is None or client.person_id != person_id:
        raise ValueError(f"person_portfolio_mismatch person={person_id} portfolio={portfolio_id}")

    existing = _existing_keys(db, portfolio_id=portfolio_id)
    result = BackfillResult(
        dry_run=True,
        portfolio_id=str(portfolio_id),
        person_id=str(person_id),
    )

    portfolio_id_str = str(portfolio_id)
    audit_q = db.query(AuditEvent).filter(
        AuditEvent.entity_type == "portfolio",
        AuditEvent.entity_id == portfolio_id_str,
        AuditEvent.action.in_([AUDIT_ACTION_FUND, AUDIT_ACTION_RELEASE]),
    )
    audit_rows = audit_q.order_by(AuditEvent.created_at.asc()).all()
    audit_batch_ids: set[str] = set()

    for row in audit_rows:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        row_batch = str(meta.get("batch_id") or "").strip()
        if batch_id and row_batch != batch_id:
            continue
        if row_batch:
            audit_batch_ids.add(row_batch)
        if row.action == AUDIT_ACTION_FUND:
            before = len(result.planned)
            _plan_deposit_from_audit(
                row,
                person_id=person_id,
                client_id=client.id,
                portfolio_id=portfolio_id,
                existing=existing,
                result=result,
            )
        elif row.action == AUDIT_ACTION_RELEASE:
            before = len(result.planned)
            _plan_withdrawal_from_audit(
                row,
                person_id=person_id,
                client_id=client.id,
                portfolio_id=portfolio_id,
                existing=existing,
                result=result,
            )
        else:
            before = len(result.planned)
        for item in result.planned[before:]:
            existing.add(item.idempotency_key)

    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
        )
        .order_by(PersonWalletSwap.created_at.asc())
        .all()
    )
    for swap in swaps:
        if not is_bundle_internal_swap(swap):
            continue
        ctx = bundle_context_from_swap_audit(swap) or {}
        if str(ctx.get("portfolio_id") or "") != portfolio_id_str:
            continue
        if batch_id and str(ctx.get("batch_id") or "") != batch_id:
            continue
        before = len(result.planned)
        _plan_from_confirmed_swap(
            db,
            swap,
            person_id=person_id,
            portfolio_id=portfolio_id,
            existing=existing,
            result=result,
        )
        for item in result.planned[before:]:
            existing.add(item.idempotency_key)

    intents = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == person_id,
            TransactionIntent.product_type.in_([
                IntentProductType.BUNDLE_INVEST.value,
                IntentProductType.BUNDLE_WITHDRAW.value,
            ]),
        )
        .all()
    )
    filtered_intents = []
    for row in intents:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if str(meta.get("bundle_id") or "") not in ("", portfolio_id_str):
            if str(meta.get("bundle_id") or "") != portfolio_id_str:
                continue
        row_batch = str(meta.get("batch_id") or row.linked_reference_id or "")
        if batch_id and row_batch != batch_id:
            continue
        filtered_intents.append(row)
    _scan_intents_for_warnings(filtered_intents, audit_batch_ids=audit_batch_ids, result=result)

    return result


def _apply_plan_item(
    db: Session,
    item: BackfillPlanItem,
    *,
    person_id: UUID,
    client_id: UUID,
    portfolio_id: UUID,
) -> None:
    meta = item.metadata
    batch_id = item.batch_id or ""

    if item.action == "record_bundle_deposit":
        entry_asset = str(meta["entry_asset"])
        instr = _instrument_for_asset(db, entry_asset)
        if instr is None:
            raise ValueError(f"missing_instrument_for_{entry_asset}")
        record_bundle_deposit(
            db,
            person_id=person_id,
            client_id=client_id,
            bundle_portfolio_id=portfolio_id,
            entry_asset=entry_asset,
            entry_instrument_id=instr.id,
            amount=Decimal(str(meta["amount"])),
            batch_id=batch_id,
        )
    elif item.action == "record_bundle_withdrawal":
        entry_asset = str(meta["entry_asset"])
        instr = _instrument_for_asset(db, entry_asset)
        if instr is None:
            raise ValueError(f"missing_instrument_for_{entry_asset}")
        record_bundle_withdrawal(
            db,
            person_id=person_id,
            client_id=client_id,
            bundle_portfolio_id=portfolio_id,
            entry_asset=entry_asset,
            entry_instrument_id=instr.id,
            amount=Decimal(str(meta["amount"])),
            batch_id=batch_id,
        )
    elif item.action == "record_allocation_buy":
        record_allocation_buy(
            db,
            person_id=person_id,
            bundle_portfolio_id=portfolio_id,
            target_instrument_id=UUID(str(meta["target_instrument_id"])),
            target_asset_symbol=str(meta["to_asset"]),
            crypto_received=Decimal(str(meta["amount_out"])),
            entry_asset_consumed=Decimal(str(meta["amount_in"])),
            entry_instrument_id=UUID(str(meta["entry_instrument_id"])),
            entry_asset_symbol=str(meta["from_asset"]),
            batch_id=batch_id or None,
            leg_id=meta.get("leg_id"),
            swap_id=UUID(str(item.source_id)),
        )
    elif item.action == "record_allocation_sell":
        sell_instr = _instrument_for_asset(db, str(meta["from_asset"]))
        entry_instr = _instrument_for_asset(db, str(meta["to_asset"]))
        if sell_instr is None or entry_instr is None:
            raise ValueError("missing_instruments_for_sell")
        record_allocation_sell(
            db,
            person_id=person_id,
            bundle_portfolio_id=portfolio_id,
            instrument_id=sell_instr.id,
            asset_symbol=str(meta["from_asset"]),
            sell_qty=Decimal(str(meta["sell_qty"])),
            entry_received=Decimal(str(meta["entry_received"])),
            entry_instrument_id=entry_instr.id,
            entry_asset_symbol=str(meta["to_asset"]),
            batch_id=batch_id or None,
            leg_id=meta.get("leg_id"),
            swap_id=UUID(str(item.source_id)),
            withdraw_sell=bool(meta.get("withdraw_sell")),
        )
    elif item.action == "record_rebalance":
        side = str(meta["side"])
        spot_instr = _instrument_for_asset(db, str(meta["spot_asset"]))
        entry_instr = _instrument_for_asset(db, str(meta["entry_asset"]))
        if spot_instr is None or entry_instr is None:
            raise ValueError("missing_instruments_for_rebalance")
        record_rebalance(
            db,
            person_id=person_id,
            bundle_portfolio_id=portfolio_id,
            side=side,
            instrument_id=spot_instr.id,
            asset_symbol=str(meta["spot_asset"]),
            quantity=Decimal(str(meta["quantity"])),
            entry_instrument_id=entry_instr.id,
            entry_asset_symbol=str(meta["entry_asset"]),
            entry_amount=Decimal(str(meta["entry_amount"])),
            batch_id=batch_id or None,
            leg_id=meta.get("leg_id"),
            swap_id=UUID(str(item.source_id)),
        )
    else:
        raise ValueError(f"unknown_backfill_action: {item.action}")


def run_backfill(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None = None,
    dry_run: bool = True,
) -> BackfillResult:
    plan = plan_backfill(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
    plan.dry_run = dry_run
    if dry_run:
        return plan

    client = (
        db.query(Client)
        .filter(Client.id == (
            db.query(Portfolio.client_id)
            .filter(Portfolio.id == portfolio_id)
            .scalar()
        ))
        .first()
    )
    if client is None:
        raise ValueError("client_not_found")

    for item in plan.planned:
        _apply_plan_item(
            db,
            item,
            person_id=person_id,
            client_id=client.id,
            portfolio_id=portfolio_id,
        )
        plan.applied.append(item.idempotency_key)
    plan.planned = []
    return plan

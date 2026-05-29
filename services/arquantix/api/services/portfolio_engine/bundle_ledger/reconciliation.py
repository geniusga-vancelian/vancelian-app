"""Phase 4A.5 — réconciliation shadow ledger vs PE + Li.FI (read-only)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_funding import (
    resolve_bundle_cash_leg_available,
)
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
    BundleLedgerStatus,
)
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundle_ledger.service import build_idempotency_key
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.products.models import ProductDefinition
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from services.transaction_intents.enums import IntentProductType

TOLERANCE = Decimal("0.000001")

BALANCE_EVENT_TYPES = frozenset({
    BundleLedgerEventType.BUNDLE_DEPOSIT.value,
    BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
    BundleLedgerEventType.BUNDLE_CASH_RELEASED.value,
    BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value,
    BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
    BundleLedgerEventType.BUNDLE_REBALANCE_BUY.value,
    BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value,
    BundleLedgerEventType.BUNDLE_FEE.value,
})


def _resolve_entry_instrument(db: Session, portfolio: Portfolio) -> tuple[Instrument | None, str]:
    product = None
    if portfolio.origin_product_id:
        product = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.id == portfolio.origin_product_id)
            .first()
        )
    meta = product.metadata_ if product and isinstance(product.metadata_, dict) else {}
    entry_asset = str(meta.get("entry_asset_default") or "USDC").upper()
    asset = db.query(Asset).filter(Asset.symbol == entry_asset).first()
    if asset is None:
        return None, entry_asset
    instr = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )
    return instr, entry_asset


def _actual_cash_from_pe(
    db: Session,
    *,
    portfolio_id: UUID,
    entry_instrument_id: UUID | None,
) -> Decimal:
    if entry_instrument_id is None:
        return Decimal("0")
    return resolve_bundle_cash_leg_available(
        db,
        portfolio_id=portfolio_id,
        entry_instrument_id=entry_instrument_id,
    )


def _actual_spots_from_pe(db: Session, *, portfolio_id: UUID) -> dict[str, Decimal]:
    rows = (
        db.query(PositionAtom, Asset.symbol)
        .join(Instrument, Instrument.id == PositionAtom.instrument_id)
        .join(Asset, Asset.id == Instrument.asset_id)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.position_type == PositionType.SPOT,
            PositionAtom.status == "open",
        )
        .all()
    )
    out: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for atom, symbol in rows:
        qty = Decimal(str(atom.quantity or 0))
        if qty > 0:
            out[str(symbol).upper()] += qty
    return dict(out)


def _signed_quantity(entry: BundleLedgerEntry) -> Decimal:
    if entry.direction == BundleLedgerDirection.INFO.value:
        return Decimal("0")
    if entry.event_type == BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value:
        if entry.direction == BundleLedgerDirection.INFO.value:
            return Decimal("0")
    if entry.status == BundleLedgerStatus.FAILED.value:
        return Decimal("0")
    qty = Decimal(str(entry.quantity or 0))
    if entry.direction == BundleLedgerDirection.CREDIT.value:
        return qty
    if entry.direction == BundleLedgerDirection.DEBIT.value:
        return -qty
    return Decimal("0")


def _balances_from_ledger(
    entries: list[BundleLedgerEntry],
    *,
    entry_asset_symbol: str,
) -> tuple[Decimal, dict[str, Decimal]]:
    """Reconstruit cash leg + spots depuis le ledger (ignore recovery INFO)."""
    entry_asset = entry_asset_symbol.upper()
    cash = Decimal("0")
    spots: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for row in entries:
        if row.event_type not in BALANCE_EVENT_TYPES:
            continue
        delta = _signed_quantity(row)
        if delta == 0:
            continue
        asset = str(row.asset_symbol or "").upper()
        if asset == entry_asset:
            cash += delta
        else:
            spots[asset] += delta

    return cash, dict(spots)


def _list_ledger_entries(
    db: Session,
    *,
    portfolio_id: UUID,
    person_id: UUID | None,
    batch_id: str | None,
) -> list[BundleLedgerEntry]:
    q = db.query(BundleLedgerEntry).filter(
        BundleLedgerEntry.bundle_portfolio_id == portfolio_id,
    )
    if person_id is not None:
        q = q.filter(BundleLedgerEntry.person_id == person_id)
    if batch_id:
        q = q.filter(BundleLedgerEntry.batch_id == batch_id)
    return q.order_by(BundleLedgerEntry.created_at.asc()).all()


def _audit_fund_release_events(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str | None,
) -> list[AuditEvent]:
    portfolio_id_str = str(portfolio_id)
    q = db.query(AuditEvent).filter(
        AuditEvent.entity_type == "portfolio",
        AuditEvent.entity_id == portfolio_id_str,
        AuditEvent.action.in_([AUDIT_ACTION_FUND, AUDIT_ACTION_RELEASE]),
    )
    rows = q.order_by(AuditEvent.created_at.asc()).all()
    if not batch_id:
        return rows
    filtered: list[AuditEvent] = []
    for row in rows:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        if str(meta.get("batch_id") or "") == batch_id:
            filtered.append(row)
    return filtered


def _bundle_confirmed_swaps(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None,
) -> list[PersonWalletSwap]:
    portfolio_id_str = str(portfolio_id)
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
        )
        .order_by(PersonWalletSwap.created_at.asc())
        .all()
    )
    out: list[PersonWalletSwap] = []
    for swap in swaps:
        if not is_bundle_internal_swap(swap):
            continue
        ctx = bundle_context_from_swap_audit(swap) or {}
        if str(ctx.get("portfolio_id") or "") != portfolio_id_str:
            continue
        if batch_id and str(ctx.get("batch_id") or "") != batch_id:
            continue
        out.append(swap)
    return out


def _bundle_intents(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None,
) -> list[TransactionIntent]:
    rows = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == person_id,
            TransactionIntent.product_type.in_([
                IntentProductType.BUNDLE_INVEST.value,
                IntentProductType.BUNDLE_WITHDRAW.value,
            ]),
        )
        .order_by(TransactionIntent.created_at.asc())
        .all()
    )
    out: list[TransactionIntent] = []
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row_bundle = str(meta.get("bundle_id") or "")
        row_batch = str(meta.get("batch_id") or row.linked_reference_id or "")
        if row_bundle and row_bundle != str(portfolio_id):
            continue
        if batch_id and row_batch != batch_id:
            continue
        out.append(row)
    return out


def _ledger_keys_present(entries: list[BundleLedgerEntry]) -> set[str]:
    return {e.idempotency_key for e in entries}


def _swap_has_ledger_entry(swap_id: UUID, entries: list[BundleLedgerEntry]) -> bool:
    sid = str(swap_id)
    for entry in entries:
        if entry.source_id and sid in entry.source_id:
            return True
        meta = entry.metadata_ if isinstance(entry.metadata_, dict) else {}
        if str(meta.get("swap_id") or "") == sid:
            return True
    return False


def _intent_has_ledger_activity(intent: TransactionIntent, entries: list[BundleLedgerEntry]) -> bool:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    batch = str(meta.get("batch_id") or intent.linked_reference_id or "")
    if not batch:
        return False
    return any(str(e.batch_id or "") == batch for e in entries)


def _find_missing_ledger_entries_v2(
    *,
    audit_rows: list[AuditEvent],
    swaps: list[PersonWalletSwap],
    entries: list[BundleLedgerEntry],
) -> list[dict[str, Any]]:
    ledger_keys = _ledger_keys_present(entries)
    missing: list[dict[str, Any]] = []

    for row in audit_rows:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        batch_id = str(meta.get("batch_id") or "")
        if row.action == AUDIT_ACTION_FUND:
            event_type = BundleLedgerEventType.BUNDLE_DEPOSIT.value
            source_id = f"{batch_id}:fund"
            direction = BundleLedgerDirection.CREDIT.value
        elif row.action == AUDIT_ACTION_RELEASE:
            event_type = BundleLedgerEventType.BUNDLE_WITHDRAWAL.value
            source_id = f"{batch_id}:release"
            direction = BundleLedgerDirection.DEBIT.value
        else:
            continue
        key = build_idempotency_key(
            source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
            source_id=source_id,
            event_type=event_type,
            direction=direction,
        )
        if key not in ledger_keys:
            missing.append({
                "kind": "audit_event",
                "audit_id": str(row.id),
                "action": row.action,
                "batch_id": batch_id,
                "expected_idempotency_key": key,
            })

    for swap in swaps:
        audit = swap.audit_log if isinstance(swap.audit_log, list) else []
        atoms_applied = any(
            isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied"
            for e in audit
        )
        if not atoms_applied:
            continue
        if not _swap_has_ledger_entry(swap.id, entries):
            ctx = bundle_context_from_swap_audit(swap) or {}
            missing.append({
                "kind": "lifi_swap",
                "swap_id": str(swap.id),
                "batch_id": ctx.get("batch_id"),
                "bundle_action": ctx.get("bundle_action"),
                "from_asset": swap.from_asset,
                "to_asset": swap.to_asset,
            })
    return missing


def _find_extra_ledger_entries(
    entries: list[BundleLedgerEntry],
    *,
    audit_rows: list[AuditEvent],
    swaps: list[PersonWalletSwap],
) -> list[dict[str, Any]]:
    audit_keys: set[str] = set()
    for row in audit_rows:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        batch_id = str(meta.get("batch_id") or "")
        if row.action == AUDIT_ACTION_FUND:
            audit_keys.add(
                build_idempotency_key(
                    source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
                    source_id=f"{batch_id}:fund",
                    event_type=BundleLedgerEventType.BUNDLE_DEPOSIT.value,
                    direction=BundleLedgerDirection.CREDIT.value,
                )
            )
        elif row.action == AUDIT_ACTION_RELEASE:
            audit_keys.add(
                build_idempotency_key(
                    source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
                    source_id=f"{batch_id}:release",
                    event_type=BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
                    direction=BundleLedgerDirection.DEBIT.value,
                )
            )

    swap_ids = {str(s.id) for s in swaps}
    extras: list[dict[str, Any]] = []
    for entry in entries:
        if entry.event_type == BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value:
            continue
        if entry.source_system == BundleLedgerSourceSystem.PE_TRANSFER.value:
            if entry.idempotency_key not in audit_keys and ":fund" in (entry.source_id or ""):
                extras.append({
                    "kind": "ledger_without_audit",
                    "entry_id": str(entry.id),
                    "event_type": entry.event_type,
                    "idempotency_key": entry.idempotency_key,
                })
            elif entry.idempotency_key not in audit_keys and ":release" in (entry.source_id or ""):
                extras.append({
                    "kind": "ledger_without_audit",
                    "entry_id": str(entry.id),
                    "event_type": entry.event_type,
                    "idempotency_key": entry.idempotency_key,
                })
        elif entry.source_system == BundleLedgerSourceSystem.LIFI.value:
            meta = entry.metadata_ if isinstance(entry.metadata_, dict) else {}
            swap_id = str(meta.get("swap_id") or (entry.source_id or "").split(":")[0])
            if swap_id and swap_id not in swap_ids:
                extras.append({
                    "kind": "ledger_without_swap",
                    "entry_id": str(entry.id),
                    "event_type": entry.event_type,
                    "source_id": entry.source_id,
                    "swap_id": swap_id,
                })
    return extras


def _duplicated_idempotency_keys(entries: list[BundleLedgerEntry]) -> list[str]:
    counts = Counter(e.idempotency_key for e in entries)
    return [k for k, c in counts.items() if c > 1]


def _orphan_lifi_swaps(
    swaps: list[PersonWalletSwap],
    entries: list[BundleLedgerEntry],
) -> list[dict[str, Any]]:
    orphans: list[dict[str, Any]] = []
    for swap in swaps:
        audit = swap.audit_log if isinstance(swap.audit_log, list) else []
        atoms_applied = any(
            isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied"
            for e in audit
        )
        if not atoms_applied:
            continue
        if not _swap_has_ledger_entry(swap.id, entries):
            ctx = bundle_context_from_swap_audit(swap) or {}
            orphans.append({
                "swap_id": str(swap.id),
                "batch_id": ctx.get("batch_id"),
                "bundle_action": ctx.get("bundle_action"),
                "status": swap.status,
            })
    return orphans


def _orphan_transaction_intents(
    intents: list[TransactionIntent],
    entries: list[BundleLedgerEntry],
) -> list[dict[str, Any]]:
    orphans: list[dict[str, Any]] = []
    terminal = {"completed", "failed", "partial", "released", "cancelled"}
    for intent in intents:
        status = str(intent.status or "").lower()
        if status not in terminal:
            continue
        if not _intent_has_ledger_activity(intent, entries):
            meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
            orphans.append({
                "intent_id": str(intent.id),
                "product_type": intent.product_type,
                "status": intent.status,
                "batch_id": meta.get("batch_id") or intent.linked_reference_id,
            })
    return orphans


def _compare_balances(
    expected_cash: Decimal,
    actual_cash: Decimal,
    expected_spots: dict[str, Decimal],
    actual_spots: dict[str, Decimal],
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    if abs(expected_cash - actual_cash) > TOLERANCE:
        diffs.append({
            "field": "cash_leg",
            "expected_from_ledger": float(expected_cash),
            "actual_from_pe": float(actual_cash),
            "delta": float(expected_cash - actual_cash),
        })
    all_assets = set(expected_spots) | set(actual_spots)
    for asset in sorted(all_assets):
        exp = expected_spots.get(asset, Decimal("0"))
        act = actual_spots.get(asset, Decimal("0"))
        if abs(exp - act) > TOLERANCE:
            diffs.append({
                "field": f"spot_{asset}",
                "expected_from_ledger": float(exp),
                "actual_from_pe": float(act),
                "delta": float(exp - act),
            })
    return diffs


def _recommendations(payload: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    verdict = payload.get("verdict")
    missing = payload.get("missing_ledger_entries") or []
    orphans = payload.get("orphan_lifi_swaps") or []

    if verdict == "MATCH":
        recs.append("Shadow ledger aligné avec PE — prêt pour validation ops avant Phase 4B.")
    elif verdict == "INCOMPLETE":
        recs.append(
            "Données legacy ou batch filtré — ne pas basculer l'historique UI tant que INCOMPLETE."
        )
        if missing:
            recs.append(
                f"{len(missing)} entrée(s) ledger manquante(s) — backfill Phase 4B ou rejeu idempotent requis."
            )
    elif verdict == "DIFF":
        recs.append("Écart détecté — investiguer avec inspect_bundle_state et ne pas basculer Phase 4B.")
        if payload.get("differences"):
            recs.append("Comparer expected_cash_from_ledger vs actual_cash_from_pe en priorité.")

    if orphans:
        recs.append(f"{len(orphans)} swap(s) Li.FI confirmé(s) sans entrée ledger — vérifier écriture miroir.")
    if payload.get("duplicated_idempotency_keys"):
        recs.append("Clés idempotence dupliquées — anomalie DB critique.")
    if not recs:
        recs.append("Aucune recommandation additionnelle (read-only).")
    return recs


def reconcile_bundle_ledger_shadow(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Compare ledger shadow vs PE + sources Li.FI/audit — strictement read-only."""
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
        raise ValueError(
            f"person_id {person_id} ne correspond pas au client du portfolio {portfolio_id}"
        )

    entry_instrument, entry_asset = _resolve_entry_instrument(db, portfolio)
    all_entries = _list_ledger_entries(
        db, portfolio_id=portfolio_id, person_id=person_id, batch_id=None,
    )
    scoped_entries = (
        _list_ledger_entries(
            db, portfolio_id=portfolio_id, person_id=person_id, batch_id=batch_id,
        )
        if batch_id
        else all_entries
    )

    audit_rows = _audit_fund_release_events(db, portfolio_id=portfolio_id, batch_id=batch_id)
    swaps = _bundle_confirmed_swaps(
        db, person_id=person_id, portfolio_id=portfolio_id, batch_id=batch_id,
    )
    intents = _bundle_intents(
        db, person_id=person_id, portfolio_id=portfolio_id, batch_id=batch_id,
    )

    expected_cash, expected_spots = _balances_from_ledger(
        all_entries, entry_asset_symbol=entry_asset,
    )
    actual_cash = _actual_cash_from_pe(
        db, portfolio_id=portfolio_id, entry_instrument_id=entry_instrument.id if entry_instrument else None,
    )
    actual_spots = _actual_spots_from_pe(db, portfolio_id=portfolio_id)

    balance_diffs = [] if batch_id else _compare_balances(
        expected_cash, actual_cash, expected_spots, actual_spots,
    )

    missing = _find_missing_ledger_entries_v2(
        audit_rows=audit_rows, swaps=swaps, entries=scoped_entries if batch_id else all_entries,
    )
    extra = _find_extra_ledger_entries(
        scoped_entries if batch_id else all_entries,
        audit_rows=audit_rows,
        swaps=swaps,
    )
    dup_keys = _duplicated_idempotency_keys(all_entries)
    orphan_swaps = _orphan_lifi_swaps(swaps, scoped_entries if batch_id else all_entries)
    orphan_intents = _orphan_transaction_intents(intents, scoped_entries if batch_id else all_entries)

    legacy_audit_without_ledger = [
        m for m in missing if m.get("kind") == "audit_event"
    ]

    if batch_id:
        if missing or extra or dup_keys:
            verdict = "DIFF"
        else:
            verdict = "MATCH"
    elif balance_diffs or dup_keys:
        verdict = "DIFF"
    elif missing or orphan_swaps:
        if legacy_audit_without_ledger and not balance_diffs:
            verdict = "INCOMPLETE"
        else:
            verdict = "DIFF"
    elif orphan_intents and not all_entries:
        verdict = "INCOMPLETE"
    else:
        verdict = "MATCH"

    if verdict == "DIFF":
        from services.portfolio_engine.bundle_ledger.observability import log_bundle_ledger_event

        log_bundle_ledger_event(
            "ledger_reconciliation_diff",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            verdict=verdict,
            fallback_reason="ledger_diff",
            entries_count=len(all_entries),
            differences=balance_diffs,
        )

    payload = {
        "reconciled_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "shadow_mode": True,
        "person_id": str(person_id),
        "portfolio_id": str(portfolio_id),
        "batch_id_filter": batch_id,
        "entry_asset": entry_asset,
        "expected_cash_from_ledger": float(expected_cash),
        "actual_cash_from_pe": float(actual_cash),
        "expected_spots_from_ledger": {k: float(v) for k, v in expected_spots.items()},
        "actual_spots_from_pe": {k: float(v) for k, v in actual_spots.items()},
        "differences": balance_diffs,
        "missing_ledger_entries": missing,
        "extra_ledger_entries": extra,
        "duplicated_idempotency_keys": dup_keys,
        "orphan_lifi_swaps": orphan_swaps,
        "orphan_transaction_intents": orphan_intents,
        "ledger_entry_count": len(all_entries),
        "audit_event_count": len(audit_rows),
        "confirmed_swap_count": len(swaps),
        "verdict": verdict,
        "recommendations": [],
    }
    payload["recommendations"] = _recommendations(payload)
    from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled

    payload["history_switch"] = {
        "flag_enabled": bundle_ledger_history_enabled(),
        "would_read_ledger": (
            bundle_ledger_history_enabled()
            and payload.get("verdict") == "MATCH"
            and int(payload.get("ledger_entry_count") or 0) > 0
        ),
        "fallback_reason": (
            None
            if payload.get("verdict") == "MATCH" and int(payload.get("ledger_entry_count") or 0) > 0
            else payload.get("verdict")
        ),
    }
    return payload

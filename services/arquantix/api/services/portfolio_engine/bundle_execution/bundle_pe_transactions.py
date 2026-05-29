"""Historique portail — transferts comptables bundle (fund / release) sans mouvement Privy."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import or_
from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import BUNDLE_INVEST_LOCK_KEY
from services.portfolio_engine.bundles.bundle_withdraw_lock import BUNDLE_WITHDRAW_LOCK_KEY
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.portfolios.models import Portfolio
from services.privy_wallet.service import _format_decimal
from services.transaction_intents.enums import IntentProductType

AUDIT_ACTION_FUND = "bundle.fund_cash_leg"
AUDIT_ACTION_RELEASE = "bundle.release_cash_leg"


def _parse_iso_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _stable_id(prefix: str, batch_id: str, action: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"{prefix}:{batch_id}:{action}")


def _portfolio_name_map(db: Session, *, client_id: UUID) -> dict[str, str]:
    rows = (
        db.query(Portfolio.id, Portfolio.name)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .all()
    )
    return {str(row[0]): (row[1] or "Bundle") for row in rows}


def _tx_from_audit(
    row: AuditEvent,
    *,
    asset_u: str,
    portfolio_names: dict[str, str],
) -> dict[str, Any] | None:
    meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
    entry_asset = str(meta.get("entry_asset") or meta.get("asset") or "").upper()
    if entry_asset != asset_u:
        return None

    amount_raw = meta.get("amount")
    if amount_raw is None:
        return None
    amount = _format_decimal(amount_raw)
    if not amount or amount == "0":
        return None

    portfolio_id = str(meta.get("portfolio_id") or row.entity_id or "")
    batch_id = str(meta.get("batch_id") or "")
    portfolio_name = str(meta.get("portfolio_name") or portfolio_names.get(portfolio_id) or "Bundle")

    if row.action == AUDIT_ACTION_FUND:
        direction = "debit"
        title = f"Transfert vers {portfolio_name}"
        subtitle = f"-{amount} {asset_u} · Mon Trading → Bundle"
        tx_id = row.id
    elif row.action == AUDIT_ACTION_RELEASE:
        direction = "credit"
        title = f"Retrait {portfolio_name}"
        subtitle = f"+{amount} {asset_u} · Bundle → Mon Trading"
        tx_id = row.id
    else:
        return None

    return {
        "id": tx_id,
        "side": "transfer",
        "asset": asset_u,
        "amount_crypto": amount,
        "amount_fiat": "0",
        "price": "0",
        "currency": "EUR",
        "status": "confirmed",
        "fee_amount": None,
        "fee_asset": None,
        "external_reference": batch_id or None,
        "created_at": row.created_at,
        "title": title,
        "subtitle": subtitle,
        "direction": direction,
        "from_asset": asset_u if direction == "debit" else None,
        "to_asset": asset_u if direction == "credit" else None,
        "transaction_kind": "bundle_pe_transfer",
        "source_system": "bundle_pe",
        "tx_hash": None,
        "custody_provider": "privy",
    }


def _tx_from_intent(
    row: TransactionIntent,
    *,
    asset_u: str,
    portfolio_names: dict[str, str],
) -> dict[str, Any] | None:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    batch_id = str(meta.get("batch_id") or row.linked_reference_id or "").strip()
    if not batch_id:
        return None

    portfolio_id = str(meta.get("bundle_id") or "")
    portfolio_name = str(meta.get("portfolio_name") or portfolio_names.get(portfolio_id) or "Bundle")

    if row.product_type == IntentProductType.BUNDLE_INVEST.value:
        funding_asset = str(meta.get("funding_asset") or meta.get("entry_asset") or "").upper()
        funding_amount = meta.get("funding_amount")
        if funding_asset != asset_u or funding_amount is None:
            return None
        amount = _format_decimal(funding_amount)
        if not amount or amount == "0":
            return None
        return {
            "id": _stable_id("bundle-intent-fund", batch_id, funding_asset),
            "side": "transfer",
            "asset": asset_u,
            "amount_crypto": amount,
            "amount_fiat": "0",
            "price": "0",
            "currency": "EUR",
            "status": "confirmed",
            "fee_amount": None,
            "fee_asset": None,
            "external_reference": batch_id,
            "created_at": row.created_at,
            "title": f"Transfert vers {portfolio_name}",
            "subtitle": f"-{amount} {asset_u} · Mon Trading → Bundle",
            "direction": "debit",
            "from_asset": asset_u,
            "to_asset": None,
            "transaction_kind": "bundle_pe_transfer",
            "source_system": "bundle_pe",
            "tx_hash": None,
            "custody_provider": "privy",
        }

    if row.product_type == IntentProductType.BUNDLE_WITHDRAW.value:
        entry_asset = str(meta.get("entry_asset") or "USDC").upper()
        released = meta.get("released_amount") or meta.get("requested_release_amount")
        if entry_asset != asset_u or released is None:
            return None
        amount = _format_decimal(released)
        if not amount or amount == "0":
            return None
        if str(row.status or "").lower() not in {"confirmed", "partial"}:
            return None
        return {
            "id": _stable_id("bundle-intent-release", batch_id, entry_asset),
            "side": "transfer",
            "asset": asset_u,
            "amount_crypto": amount,
            "amount_fiat": "0",
            "price": "0",
            "currency": "EUR",
            "status": "confirmed",
            "fee_amount": None,
            "fee_asset": None,
            "external_reference": batch_id,
            "created_at": row.updated_at or row.created_at,
            "title": f"Retrait {portfolio_name}",
            "subtitle": f"+{amount} {asset_u} · Bundle → Mon Trading",
            "direction": "credit",
            "from_asset": None,
            "to_asset": asset_u,
            "transaction_kind": "bundle_pe_transfer",
            "source_system": "bundle_pe",
            "tx_hash": None,
            "custody_provider": "privy",
        }

    return None


def _tx_from_portfolio_lock(
    portfolio: Portfolio,
    lock_key: str,
    *,
    asset_u: str,
) -> dict[str, Any] | None:
    meta = portfolio.metadata_ if isinstance(portfolio.metadata_, dict) else {}
    lock = meta.get(lock_key)
    if not isinstance(lock, dict):
        return None

    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        return None

    portfolio_name = portfolio.name or "Bundle"

    if lock_key == BUNDLE_INVEST_LOCK_KEY:
        funding_asset = str(lock.get("funding_asset") or "").upper()
        funding_amount = lock.get("funding_amount")
        if funding_asset != asset_u or funding_amount is None:
            return None
        amount = _format_decimal(funding_amount)
        if not amount or amount == "0":
            return None
        created = _parse_iso_dt(lock.get("created_at")) or portfolio.updated_at
        return {
            "id": _stable_id("bundle-lock-fund", batch_id, funding_asset),
            "side": "transfer",
            "asset": asset_u,
            "amount_crypto": amount,
            "amount_fiat": "0",
            "price": "0",
            "currency": "EUR",
            "status": "confirmed",
            "fee_amount": None,
            "fee_asset": None,
            "external_reference": batch_id,
            "created_at": created,
            "title": f"Transfert vers {portfolio_name}",
            "subtitle": f"-{amount} {asset_u} · Mon Trading → Bundle",
            "direction": "debit",
            "from_asset": asset_u,
            "to_asset": None,
            "transaction_kind": "bundle_pe_transfer",
            "source_system": "bundle_pe",
            "tx_hash": None,
            "custody_provider": "privy",
        }

    if lock_key == BUNDLE_WITHDRAW_LOCK_KEY:
        entry_asset = str(lock.get("entry_asset") or "USDC").upper()
        released = lock.get("released_amount")
        phase = str(lock.get("withdraw_phase") or lock.get("status") or "").upper()
        if entry_asset != asset_u:
            return None
        if phase != "RELEASED" or released is None:
            return None
        amount = _format_decimal(released)
        if not amount or amount == "0":
            return None
        created = _parse_iso_dt(lock.get("updated_at") or lock.get("created_at")) or portfolio.updated_at
        return {
            "id": _stable_id("bundle-lock-release", batch_id, entry_asset),
            "side": "transfer",
            "asset": asset_u,
            "amount_crypto": amount,
            "amount_fiat": "0",
            "price": "0",
            "currency": "EUR",
            "status": "confirmed",
            "fee_amount": None,
            "fee_asset": None,
            "external_reference": batch_id,
            "created_at": created,
            "title": f"Retrait {portfolio_name}",
            "subtitle": f"+{amount} {asset_u} · Bundle → Mon Trading",
            "direction": "credit",
            "from_asset": None,
            "to_asset": asset_u,
            "transaction_kind": "bundle_pe_transfer",
            "source_system": "bundle_pe",
            "tx_hash": None,
            "custody_provider": "privy",
        }

    return None


def _pe_transfer_canonical_key(mapped: dict[str, Any]) -> str | None:
    batch = str(mapped.get("external_reference") or "").strip()
    direction = str(mapped.get("direction") or "").strip()
    if not batch or not direction:
        return None
    return f"{batch}:{direction}"


def _store_pe_transfer(
    store: dict[str, tuple[int, dict[str, Any]]],
    mapped: dict[str, Any],
    *,
    priority: int,
) -> None:
    """Une seule ligne par batch+direction — audit > intent > lock."""
    key = _pe_transfer_canonical_key(mapped)
    if key is None:
        store[f"orphan:{mapped.get('id')}"] = (priority, mapped)
        return
    existing = store.get(key)
    if existing is None or priority > existing[0]:
        store[key] = (priority, mapped)


def list_bundle_pe_asset_transactions(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    asset: str,
    limit: int = 100,
    portfolio_id: str | None = None,
) -> list[dict[str, Any]]:
    """Liste les transferts PE bundle ↔ self-trading pour un actif (ex. USDC)."""
    asset_u = asset.strip().upper()
    portfolio_names = _portfolio_name_map(db, client_id=client_id)
    portfolio_ids = list(portfolio_names.keys())
    portfolio_filter = str(portfolio_id or "").strip()
    by_key: dict[str, tuple[int, dict[str, Any]]] = {}

    def _portfolio_allowed(pid: str) -> bool:
        if not portfolio_filter:
            return True
        return pid == portfolio_filter

    audit_filters = [AuditEvent.action.in_([AUDIT_ACTION_FUND, AUDIT_ACTION_RELEASE])]
    client_match = AuditEvent.metadata_["client_id"].astext == str(client_id)
    if portfolio_ids:
        audit_filters.append(
            or_(client_match, AuditEvent.entity_id.in_(portfolio_ids)),
        )
    else:
        audit_filters.append(client_match)

    audit_rows = (
        db.query(AuditEvent)
        .filter(*audit_filters)
        .order_by(AuditEvent.created_at.desc())
        .limit(max(limit * 4, 50))
        .all()
    )
    for row in audit_rows:
        mapped = _tx_from_audit(row, asset_u=asset_u, portfolio_names=portfolio_names)
        if mapped is None:
            continue
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        pid = str(meta.get("portfolio_id") or row.entity_id or "")
        if not _portfolio_allowed(pid):
            continue
        _store_pe_transfer(by_key, mapped, priority=3)

    if person_id is not None:
        intents = (
            db.query(TransactionIntent)
            .filter(
                TransactionIntent.person_id == person_id,
                TransactionIntent.product_type.in_(
                    [
                        IntentProductType.BUNDLE_INVEST.value,
                        IntentProductType.BUNDLE_WITHDRAW.value,
                    ]
                ),
            )
            .order_by(TransactionIntent.created_at.desc())
            .limit(max(limit * 4, 50))
            .all()
        )
        for row in intents:
            mapped = _tx_from_intent(row, asset_u=asset_u, portfolio_names=portfolio_names)
            if mapped is None:
                continue
            meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            pid = str(meta.get("bundle_id") or "")
            if not _portfolio_allowed(pid):
                continue
            _store_pe_transfer(by_key, mapped, priority=2)

    portfolios = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .all()
    )
    for portfolio in portfolios:
        if not _portfolio_allowed(str(portfolio.id)):
            continue
        for lock_key in (BUNDLE_INVEST_LOCK_KEY, BUNDLE_WITHDRAW_LOCK_KEY):
            mapped = _tx_from_portfolio_lock(portfolio, lock_key, asset_u=asset_u)
            if mapped is None:
                continue
            _store_pe_transfer(by_key, mapped, priority=1)

    txs = [item[1] for item in by_key.values()]
    txs.sort(
        key=lambda tx: _parse_iso_dt(tx.get("created_at")) or datetime.min.replace(tzinfo=None),
        reverse=True,
    )
    return txs[:limit]

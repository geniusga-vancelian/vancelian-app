"""B3a — Bundle funding handler (trading_available USDC → bundle_cash_leg).

Handler event-driven / settlement layer — module isolé, flag OFF par défaut.
Ne remplace pas ``fund_bundle_cash_leg_from_self_trading`` en runtime legacy.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.event_driven.bundle_funding_handler_config import (
    bundle_funding_handler_enabled,
)
from services.portfolio_engine.bundle_execution.bundle_funding import (
    BundleFundingError,
    resolve_self_trading_available,
)
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.enums import IntentProductType, IntentRole

BUNDLE_FUNDING_ASSET_V1 = "USDC"
BUNDLE_FUNDING_RECEIPT_METADATA_KEY = "bundle_funding_receipt_hash"
BUNDLE_FUNDING_BLOCK_METADATA_KEY = "bundle_funding"
TOLERANCE = Decimal("0.000001")


class BundleFundingHandlerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class BundleFundingSettleResult:
    skipped: bool
    idempotent: bool
    settled: bool
    receipt_hash: str | None
    amount_usdc: Decimal | None
    portfolio_id: UUID | None
    parent_intent_id: UUID | None
    reason: str | None = None
    trading_debit_usdc: Decimal | None = None
    bundle_cash_credit_usdc: Decimal | None = None


def compute_bundle_funding_receipt_hash(
    *,
    parent_intent_id: UUID,
    portfolio_id: UUID,
    person_id: UUID,
    amount_usdc: Decimal | str,
    bundle_execution_id: UUID | None,
) -> str:
    payload = {
        "parent_intent_id": str(parent_intent_id),
        "portfolio_id": str(portfolio_id),
        "person_id": str(person_id),
        "amount_usdc": str(amount_usdc),
        "asset": BUNDLE_FUNDING_ASSET_V1,
        "bundle_execution_id": str(bundle_execution_id) if bundle_execution_id else None,
        "handler": "bundle_funding_v1",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_usdc_instrument_id(db: Session) -> UUID:
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.models import Instrument

    asset = db.query(Asset).filter(Asset.symbol == BUNDLE_FUNDING_ASSET_V1).first()
    if asset is None:
        raise BundleFundingHandlerError(
            "bundle.funding.usdc_instrument_missing",
            "Instrument USDC introuvable",
        )
    instr = (
        db.query(Instrument)
        .filter(
            Instrument.asset_id == asset.id,
            Instrument.instrument_type == "spot",
        )
        .first()
    )
    if instr is None:
        raise BundleFundingHandlerError(
            "bundle.funding.usdc_instrument_missing",
            "Instrument USDC spot introuvable",
        )
    return instr.id


def _validate_parent_intent(
    intent: TransactionIntent,
    *,
    portfolio_id: UUID,
    person_id: UUID,
    amount_usdc: Decimal,
    bundle_execution_id: UUID | None,
) -> None:
    if intent.product_type != IntentProductType.BUNDLE_INVEST.value:
        raise BundleFundingHandlerError(
            "bundle.funding.invalid_product_type",
            f"product_type={intent.product_type}",
        )
    if intent.intent_role != IntentRole.PARENT.value:
        raise BundleFundingHandlerError(
            "bundle.funding.invalid_intent_role",
            f"intent_role={intent.intent_role}",
        )
    if intent.person_id != person_id:
        raise BundleFundingHandlerError(
            "bundle.funding.person_mismatch",
            "person_id incohérent",
        )
    if amount_usdc <= 0:
        raise BundleFundingHandlerError(
            "bundle.funding.invalid_amount",
            "amount_usdc doit être > 0",
        )

    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    meta_portfolio = str(meta.get("bundle_id") or meta.get("portfolio_id") or "").strip()
    if meta_portfolio and meta_portfolio != str(portfolio_id):
        raise BundleFundingHandlerError(
            "bundle.funding.portfolio_mismatch",
            "portfolio_id incohérent avec metadata parent",
        )

    if bundle_execution_id is not None and intent.bundle_execution_id is not None:
        if intent.bundle_execution_id != bundle_execution_id:
            raise BundleFundingHandlerError(
                "bundle.funding.bundle_execution_id_mismatch",
                "bundle_execution_id incohérent",
            )


def _existing_funding_metadata(intent: TransactionIntent) -> dict[str, Any] | None:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    block = meta.get(BUNDLE_FUNDING_BLOCK_METADATA_KEY)
    if isinstance(block, dict) and block.get("settled") is True:
        return block
    return None


def _persist_funding_metadata(
    db: Session,
    intent: TransactionIntent,
    *,
    receipt_hash: str,
    amount_usdc: Decimal,
    portfolio_id: UUID,
    wallet_id: UUID,
    cash_leg_atom_id: str | None,
) -> None:
    meta = dict(intent.metadata_json) if isinstance(intent.metadata_json, dict) else {}
    meta[BUNDLE_FUNDING_RECEIPT_METADATA_KEY] = receipt_hash
    meta[BUNDLE_FUNDING_BLOCK_METADATA_KEY] = {
        "settled": True,
        "funding_settled": True,
        "receipt_hash": receipt_hash,
        "asset": BUNDLE_FUNDING_ASSET_V1,
        "amount_usdc": str(amount_usdc),
        "portfolio_id": str(portfolio_id),
        "wallet_id": str(wallet_id),
        "cash_leg_atom_id": cash_leg_atom_id,
        "settled_at": _utc_now_iso(),
        "phase": "FUNDED",
    }
    intent.metadata_json = meta
    db.add(intent)
    db.flush()


def _apply_pe_funding_transfer(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID,
    portfolio_id: UUID,
    entry_instrument_id: UUID,
    amount: Decimal,
    batch_id: str,
) -> tuple[Decimal, Decimal, str | None]:
    """Débit trading_available (direct overlay) · crédit bundle_cash_leg — sans Privy."""
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    available = resolve_self_trading_available(
        db,
        client_id=client_id,
        person_id=person_id,
        entry_asset=BUNDLE_FUNDING_ASSET_V1,
        entry_instrument_id=entry_instrument_id,
    )
    if available + TOLERANCE < amount:
        raise BundleFundingHandlerError(
            "bundle.funding.insufficient_trading_available",
            f"Solde trading_available USDC insuffisant ({available} < {amount})",
        )

    cost_basis = Decimal("0")
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(
        db,
        direct_pf.id,
        entry_instrument_id,
        -amount,
        -cost_basis,
    )
    cash_atom = BundleOrchestrator._credit_cash_leg(
        db,
        portfolio_id,
        entry_instrument_id,
        amount,
        cost_basis,
    )
    return amount, amount, str(cash_atom.id) if cash_atom is not None else None


def settle_bundle_funding_idempotently(
    db: Session,
    *,
    parent_intent_id: UUID,
    amount_usdc: Decimal | str,
    portfolio_id: UUID,
    wallet_id: UUID,
    person_id: UUID,
    bundle_execution_id: UUID | None = None,
) -> BundleFundingSettleResult:
    """Settle funding interne Bundle — flag OFF → no-op strict."""
    amount = Decimal(str(amount_usdc))

    if not bundle_funding_handler_enabled():
        return BundleFundingSettleResult(
            skipped=True,
            idempotent=False,
            settled=False,
            receipt_hash=None,
            amount_usdc=amount,
            portfolio_id=portfolio_id,
            parent_intent_id=parent_intent_id,
            reason="bundle_funding_handler_disabled",
        )

    intent = db.query(TransactionIntent).filter(TransactionIntent.id == parent_intent_id).first()
    if intent is None:
        raise BundleFundingHandlerError(
            "bundle.funding.parent_intent_not_found",
            f"parent_intent_id={parent_intent_id}",
        )

    _validate_parent_intent(
        intent,
        portfolio_id=portfolio_id,
        person_id=person_id,
        amount_usdc=amount,
        bundle_execution_id=bundle_execution_id,
    )

    receipt_hash = compute_bundle_funding_receipt_hash(
        parent_intent_id=parent_intent_id,
        portfolio_id=portfolio_id,
        person_id=person_id,
        amount_usdc=amount,
        bundle_execution_id=bundle_execution_id or intent.bundle_execution_id,
    )

    existing = _existing_funding_metadata(intent)
    if existing is not None:
        existing_hash = str(
            existing.get("receipt_hash")
            or (intent.metadata_json or {}).get(BUNDLE_FUNDING_RECEIPT_METADATA_KEY)
            or ""
        )
        return BundleFundingSettleResult(
            skipped=False,
            idempotent=True,
            settled=True,
            receipt_hash=existing_hash or receipt_hash,
            amount_usdc=Decimal(str(existing.get("amount_usdc") or amount)),
            portfolio_id=portfolio_id,
            parent_intent_id=parent_intent_id,
            trading_debit_usdc=Decimal(str(existing.get("amount_usdc") or amount)),
            bundle_cash_credit_usdc=Decimal(str(existing.get("amount_usdc") or amount)),
            reason="already_settled",
        )

    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.status == "active",
        )
        .first()
    )
    if portfolio is None:
        raise BundleFundingHandlerError(
            "bundle.funding.portfolio_not_found",
            f"portfolio_id={portfolio_id}",
        )
    if portfolio.client_id is None:
        raise BundleFundingHandlerError(
            "bundle.funding.portfolio_client_missing",
            "portfolio sans client_id",
        )

    usdc_instrument_id = _resolve_usdc_instrument_id(db)
    batch_id = str(bundle_execution_id or intent.bundle_execution_id or parent_intent_id)

    try:
        debit, credit, cash_atom_id = _apply_pe_funding_transfer(
            db,
            client_id=portfolio.client_id,
            person_id=person_id,
            portfolio_id=portfolio_id,
            entry_instrument_id=usdc_instrument_id,
            amount=amount,
            batch_id=batch_id,
        )
    except BundleFundingError as exc:
        raise BundleFundingHandlerError(exc.code, str(exc)) from exc

    _persist_funding_metadata(
        db,
        intent,
        receipt_hash=receipt_hash,
        amount_usdc=amount,
        portfolio_id=portfolio_id,
        wallet_id=wallet_id,
        cash_leg_atom_id=cash_atom_id,
    )

    return BundleFundingSettleResult(
        skipped=False,
        idempotent=False,
        settled=True,
        receipt_hash=receipt_hash,
        amount_usdc=amount,
        portfolio_id=portfolio_id,
        parent_intent_id=parent_intent_id,
        trading_debit_usdc=debit,
        bundle_cash_credit_usdc=credit,
    )

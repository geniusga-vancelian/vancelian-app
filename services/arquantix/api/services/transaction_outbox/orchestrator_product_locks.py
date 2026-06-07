"""Branchement runtime S4 L4b — product locks sur intent orchestrateur LI.FI (flag OFF par défaut)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.orchestrator_allowlist import lifi_intent_orchestrator_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.privy_wallet.repository import PersonCryptoWalletRepository
from services.product_locks.balance_snapshot import build_balance_snapshot
from services.product_locks.config import transaction_product_locks_enabled
from services.product_locks.enums import ProductLockScope
from services.product_locks.exceptions import (
    ProductLockConflict,
    ProductLockConflict409,
)
from services.product_locks.middleware import (
    validate_balance_snapshot_or_raise,
    validate_product_lock_or_raise,
)
from services.product_locks.service import acquire_product_lock
from services.transaction_intents.enums import IntentProductType

logger = logging.getLogger(__name__)

BALANCE_SNAPSHOT_VERSION = 1


@dataclass(frozen=True)
class OrchestratorProductLockApplyResult:
    skipped: bool
    applied: bool = False
    reason: str | None = None


def _is_orchestrator_lifi_intent(intent: TransactionIntent) -> bool:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    return (
        intent.product_type == IntentProductType.LIFI_SWAP.value
        and meta.get("phase2_orchestrator") is True
    )


def _source_asset(intent: TransactionIntent) -> str:
    assets = intent.assets_json if isinstance(intent.assets_json, dict) else {}
    from_block = assets.get("from") if isinstance(assets.get("from"), dict) else {}
    asset = from_block.get("asset") if isinstance(from_block, dict) else None
    if not asset:
        raise ValueError("orchestrator_intent_missing_source_asset")
    return str(asset)


def _resolve_orchestrator_wallet_id(db: Session, person_id: UUID) -> UUID:
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    if not wallets:
        raise ValueError(f"orchestrator_wallet_missing:{person_id}")

    for wallet in wallets:
        if (wallet.provider or "").strip().lower() == "privy":
            return wallet.id
    return wallets[0].id


def _persist_balance_snapshot(intent: TransactionIntent, snapshot_dict: dict) -> None:
    meta = dict(intent.metadata_json) if isinstance(intent.metadata_json, dict) else {}
    meta["balance_snapshot"] = snapshot_dict
    intent.metadata_json = meta


def apply_orchestrator_product_locks_before_queued(
    db: Session,
    intent: TransactionIntent,
) -> OrchestratorProductLockApplyResult:
    """Capture snapshot + acquire lock avant transition VALIDATED → QUEUED.

    Flag OFF → no-op strict (comportement prod inchangé).
    Scope L4b : intent orchestrateur LI.FI allowlisté uniquement.
    Release lock : hors scope (L4c).
    """
    if not transaction_product_locks_enabled():
        return OrchestratorProductLockApplyResult(skipped=True, reason="product_locks_disabled")

    if not _is_orchestrator_lifi_intent(intent):
        return OrchestratorProductLockApplyResult(skipped=True, reason="not_orchestrator_lifi")

    if not lifi_intent_orchestrator_enabled_for_person(db, intent.person_id):
        return OrchestratorProductLockApplyResult(skipped=True, reason="not_allowlisted")

    wallet_id = _resolve_orchestrator_wallet_id(db, intent.person_id)
    asset = _source_asset(intent)
    scope = ProductLockScope.TRADING_AVAILABLE

    validate_product_lock_or_raise(
        db,
        person_id=intent.person_id,
        wallet_id=wallet_id,
        asset=asset,
        scope=scope,
        intent_id=intent.id,
    )

    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    existing_snapshot = meta.get("balance_snapshot")
    pe_snapshot = read_current_pe_scope_snapshot(db, intent.person_id)

    if isinstance(existing_snapshot, dict):
        current = build_balance_snapshot(
            person_id=intent.person_id,
            wallet_id=wallet_id,
            asset=asset,
            scope=scope,
            version=BALANCE_SNAPSHOT_VERSION,
            pe_snapshot=pe_snapshot,
        )
        if current.snapshot is None:
            raise RuntimeError("unexpected_balance_snapshot_skip_when_enabled")
        validate_balance_snapshot_or_raise(
            person_id=intent.person_id,
            wallet_id=wallet_id,
            asset=asset,
            scope=scope,
            stored_snapshot=existing_snapshot,
            current_available=current.snapshot.available,
            current_version=BALANCE_SNAPSHOT_VERSION,
        )
        snapshot_dict = existing_snapshot
    else:
        built = build_balance_snapshot(
            person_id=intent.person_id,
            wallet_id=wallet_id,
            asset=asset,
            scope=scope,
            version=BALANCE_SNAPSHOT_VERSION,
            pe_snapshot=pe_snapshot,
        )
        if built.skipped or built.snapshot is None:
            raise RuntimeError("unexpected_balance_snapshot_skip_when_enabled")
        validate_balance_snapshot_or_raise(
            person_id=intent.person_id,
            wallet_id=wallet_id,
            asset=asset,
            scope=scope,
            stored_snapshot=built.snapshot,
            current_available=built.snapshot.available,
            current_version=BALANCE_SNAPSHOT_VERSION,
        )
        snapshot_dict = built.snapshot.to_dict()
        _persist_balance_snapshot(intent, snapshot_dict)

    try:
        acquired = acquire_product_lock(
            db,
            person_id=intent.person_id,
            wallet_id=wallet_id,
            asset=asset,
            scope=scope,
            product_type=intent.product_type,
            intent_id=intent.id,
        )
    except ProductLockConflict as exc:
        raise ProductLockConflict409(
            lock_key=exc.lock_key,
            existing_intent_id=exc.existing_intent_id,
            requested_intent_id=exc.requested_intent_id,
        ) from None

    if acquired.skipped:
        raise RuntimeError("unexpected_acquire_skip_when_enabled")

    logger.info(
        "orchestrator_product_lock_applied",
        extra={
            "intent_id": str(intent.id),
            "asset": asset,
            "scope": scope.value,
            "idempotent": acquired.idempotent,
        },
    )
    return OrchestratorProductLockApplyResult(skipped=False, applied=True)

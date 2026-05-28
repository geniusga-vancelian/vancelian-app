"""Rapport reconcile:wallet --dry-run (aucune modification de balance)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.base_transfer_indexer import index_deposit_tx_hashes_for_wallet
from services.onchain_indexer.chain_config import chain_label
from services.onchain_indexer.models import RawOnChainEvent
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.chain_balance import aggregate_confirmed_deposit_balances
from services.privy_wallet.deposit_backfill import fetch_aggregated_on_chain_balances
from services.privy_wallet.enums import PersonWalletDepositStatus
from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from services.privy_wallet.reconciliation_service import RECONCILIATION_ASSETS, dust_tolerance

_DEPOSIT_KEY = tuple[int, str, int]  # chain_id, tx_hash, log_index
_EVENT_KEY = _DEPOSIT_KEY


@dataclass
class WalletReconcileReport:
    wallet_address: str
    person_id: str
    chain_id: int
    chain: str
    dry_run: bool
    index_tx_hashes: bool
    balances_ledger_by_asset: dict[str, str] = field(default_factory=dict)
    balances_table_by_asset: dict[str, str] = field(default_factory=dict)
    balances_on_chain_by_asset: dict[str, str] = field(default_factory=dict)
    deltas_by_asset: dict[str, dict[str, str]] = field(default_factory=dict)
    db_without_onchain_proof: list[dict[str, Any]] = field(default_factory=list)
    onchain_without_db_ledger: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    index_summary: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wallet_address": self.wallet_address,
            "person_id": self.person_id,
            "chain_id": self.chain_id,
            "chain": self.chain,
            "dry_run": self.dry_run,
            "index_tx_hashes": self.index_tx_hashes,
            "balances_ledger_by_asset": self.balances_ledger_by_asset,
            "balances_table_by_asset": self.balances_table_by_asset,
            "balances_on_chain_by_asset": self.balances_on_chain_by_asset,
            "deltas_by_asset": self.deltas_by_asset,
            "db_without_onchain_proof": self.db_without_onchain_proof,
            "onchain_without_db_ledger": self.onchain_without_db_ledger,
            "recommendations": self.recommendations,
            "index_summary": self.index_summary,
            "warnings": self.warnings,
        }


def _fmt_decimal(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _ledger_balances_for_wallet_chain(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    chain_id: int,
) -> dict[str, Decimal]:
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    wallet_by_id = {w.id: w for w in wallets}
    buckets = aggregate_confirmed_deposit_balances(db, person_id=person_id, wallets=wallets)
    out: dict[str, Decimal] = {}
    for bucket in buckets:
        if bucket.wallet_id != wallet_id or bucket.chain_id != chain_id:
            continue
        out[bucket.asset] = bucket.balance
    return out


def _table_balances_for_wallet(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in PersonWalletBalanceRepository.list_for_person(db, person_id):
        if row.person_crypto_wallet_id != wallet_id:
            continue
        out[row.asset.upper()] = Decimal(str(row.balance or 0))
    return out


def _deposit_keys(
    deposits: list[PersonWalletDeposit],
    *,
    chain_id: int,
) -> set[_DEPOSIT_KEY]:
    keys: set[_DEPOSIT_KEY] = set()
    for row in deposits:
        if row.chain_id != chain_id:
            continue
        if row.status != PersonWalletDepositStatus.CONFIRMED.value:
            continue
        tx = str(row.tx_hash or "").strip().lower()
        if not tx:
            continue
        keys.add((chain_id, tx, int(row.log_index or 0)))
    return keys


def _event_keys(events: list[RawOnChainEvent]) -> set[_EVENT_KEY]:
    return {
        (int(e.chain_id), str(e.tx_hash).lower(), int(e.log_index or 0))
        for e in events
    }


def build_wallet_reconcile_report(
    db: Session,
    *,
    wallet_address: str,
    chain_id: int,
    dry_run: bool = True,
    index_tx_hashes: bool = False,
) -> WalletReconcileReport:
    """
    Compare ledger DB, soldes on-chain et événements indexés.

    Ne modifie jamais ``person_wallet_balances`` ni les dépôts.
    ``index_tx_hashes=True`` écrit uniquement dans ``raw_onchain_events``.
    """
    normalized = normalize_evm_address(wallet_address) or wallet_address.strip().lower()
    wallet = PersonCryptoWalletRepository.find_active_by_address(db, normalized)
    if wallet is None:
        raise ValueError(f"Wallet Privy introuvable : {normalized}")

    report = WalletReconcileReport(
        wallet_address=normalized,
        person_id=str(wallet.person_id),
        chain_id=chain_id,
        chain=chain_label(chain_id),
        dry_run=dry_run,
        index_tx_hashes=index_tx_hashes,
    )

    if index_tx_hashes and not dry_run:
        report.warnings.append(
            "index_tx_hashes sans dry_run : seule la table raw_onchain_events sera enrichie.",
        )

    if index_tx_hashes:
        report.index_summary = index_deposit_tx_hashes_for_wallet(
            db,
            person_id=wallet.person_id,
            wallet_address=normalized,
            chain_id=chain_id,
        )
        if not dry_run:
            db.commit()

    ledger = _ledger_balances_for_wallet_chain(
        db,
        person_id=wallet.person_id,
        wallet_id=wallet.id,
        chain_id=chain_id,
    )
    table = _table_balances_for_wallet(db, person_id=wallet.person_id, wallet_id=wallet.id)

    on_chain_map = fetch_aggregated_on_chain_balances(
        wallet_address=normalized,
        chain_ids=[chain_id],
        assets=list(RECONCILIATION_ASSETS),
    )
    on_chain = {
        asset: on_chain_map.get((chain_id, asset), Decimal("0"))
        for asset in RECONCILIATION_ASSETS
    }
    if not any(on_chain_map.values()) and not resolve_chain_rpc_url(chain_id):
        report.warnings.append(
            f"RPC non configuré pour chain_id={chain_id} — soldes on-chain indisponibles.",
        )

    all_assets = sorted(
        set(ledger) | set(table) | {a for a, v in on_chain.items() if v > 0},
    )

    for asset in all_assets:
        led = ledger.get(asset, Decimal("0"))
        tbl = table.get(asset, Decimal("0"))
        oc = on_chain.get(asset, Decimal("0"))
        report.balances_ledger_by_asset[asset] = _fmt_decimal(led)
        report.balances_table_by_asset[asset] = _fmt_decimal(tbl)
        report.balances_on_chain_by_asset[asset] = _fmt_decimal(oc)
        delta_oc_led = oc - led
        tol = dust_tolerance(asset)
        report.deltas_by_asset[asset] = {
            "ledger_vs_on_chain": _fmt_decimal(delta_oc_led),
            "table_vs_ledger": _fmt_decimal(tbl - led),
            "within_dust_tolerance": str(abs(delta_oc_led) <= tol),
        }

    deposits = PersonWalletDepositRepository.list_for_person(
        db,
        wallet.person_id,
        limit=5000,
    )
    wallet_deposits = [
        d
        for d in deposits
        if d.person_crypto_wallet_id == wallet.id and d.chain_id == chain_id
    ]

    raw_events = (
        db.query(RawOnChainEvent)
        .filter(
            RawOnChainEvent.wallet_address == normalized,
            RawOnChainEvent.chain_id == chain_id,
        )
        .order_by(RawOnChainEvent.parsed_at.desc())
        .limit(5000)
        .all()
    )

    deposit_keys = _deposit_keys(wallet_deposits, chain_id=chain_id)
    event_keys = _event_keys(raw_events)

    for dep in wallet_deposits:
        if dep.status != PersonWalletDepositStatus.CONFIRMED.value:
            continue
        key = (chain_id, str(dep.tx_hash).lower(), int(dep.log_index or 0))
        if key in event_keys:
            continue
        tx = str(dep.tx_hash or "").lower()
        if tx.startswith("0xsim") or (dep.idempotency_key or "").lower().startswith("admin_sim_"):
            report.db_without_onchain_proof.append(
                {
                    "deposit_id": str(dep.id),
                    "tx_hash": dep.tx_hash,
                    "log_index": dep.log_index,
                    "asset": dep.asset,
                    "amount": _fmt_decimal(Decimal(str(dep.amount))),
                    "direction": dep.direction,
                    "reason": "simulated_or_admin_credit",
                }
            )
            continue
        report.db_without_onchain_proof.append(
            {
                "deposit_id": str(dep.id),
                "tx_hash": dep.tx_hash,
                "log_index": dep.log_index,
                "asset": dep.asset,
                "amount": _fmt_decimal(Decimal(str(dep.amount))),
                "direction": dep.direction,
                "reason": "no_matching_raw_onchain_event",
            }
        )

    matched_deposit_keys = deposit_keys
    for event in raw_events:
        key = (int(event.chain_id), str(event.tx_hash).lower(), int(event.log_index or 0))
        if key in matched_deposit_keys:
            continue
        report.onchain_without_db_ledger.append(
            {
                "event_id": str(event.id),
                "tx_hash": event.tx_hash,
                "log_index": event.log_index,
                "asset": event.asset,
                "amount_raw": str(event.amount_raw),
                "event_type": event.event_type,
            }
        )

    if report.db_without_onchain_proof:
        report.recommendations.append(
            "Exécuter avec --index-tx-hashes (hors dry-run strict) pour ingérer les receipts "
            "des tx connues dans raw_onchain_events, puis relancer le dry-run.",
        )
    if report.onchain_without_db_ledger:
        report.recommendations.append(
            "Événements on-chain sans ledger : vérifier webhook Privy manquant ou "
            "backfill deposit (admin) — pas d'apply automatique en Phase 3.",
        )
    for asset, delta in report.deltas_by_asset.items():
        if delta.get("within_dust_tolerance") == "False":
            report.recommendations.append(
                f"Écart {asset} ledger/on-chain hors tolérance — investigation manuelle requise.",
            )
    if not report.recommendations:
        report.recommendations.append("Aucun écart critique détecté sur le périmètre analysé.")

    return report

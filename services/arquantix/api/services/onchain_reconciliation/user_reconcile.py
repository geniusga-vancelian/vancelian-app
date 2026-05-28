"""Réconciliation agrégée par person_id (Phase 4)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.chain_config import CHAIN_BASE
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from services.onchain_reconciliation.wallet_dry_run import build_wallet_reconcile_report
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.repository import (
    PersonCryptoWalletRepository,
    PersonWalletDepositRepository,
)

PENDING_STALE_HOURS = 24


@dataclass
class UserReconcileReport:
    person_id: str
    dry_run: bool
    persist_discrepancies: bool
    wallets: list[dict[str, Any]] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    discrepancies_written: int = 0
    discrepancies_skipped: int = 0
    summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": self.person_id,
            "dry_run": self.dry_run,
            "persist_discrepancies": self.persist_discrepancies,
            "wallets": self.wallets,
            "anomalies": self.anomalies,
            "discrepancies_written": self.discrepancies_written,
            "discrepancies_skipped": self.discrepancies_skipped,
            "summary": self.summary,
            "warnings": self.warnings,
        }


def _fmt(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(Decimal(str(value)).normalize(), "f")
    return text.rstrip("0").rstrip(".") or "0"


def _audit_has_event(audit_log: Any, event_name: str) -> bool:
    if not isinstance(audit_log, list):
        return False
    return any(isinstance(e, dict) and e.get("event") == event_name for e in audit_log)


def _swap_missing_actual_settlement(swap: PersonWalletSwap) -> bool:
    if swap.status != SwapSessionStatus.CONFIRMED.value:
        return False
    if swap_settlement_already_applied(swap):
        return False
    if _audit_has_event(swap.audit_log, "settlement_blocked"):
        return True
    if _audit_has_event(swap.audit_log, "swap_settled"):
        return False
    return True


def _collect_vault_pending(db: Session, person_id: UUID) -> list[dict[str, Any]]:
    try:
        rows = db.execute(
            sa.text(
                """
                SELECT id, status, operation, integration_mode, created_at, wallet_address
                FROM onchain_vault_transactions
                WHERE person_id = :person_id AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 200
                """
            ),
            {"person_id": str(person_id)},
        ).mappings().all()
    except Exception:
        return []
    return [dict(row) for row in rows]


def _collect_lombard_mock_credits(db: Session, person_id: UUID) -> list[dict[str, Any]]:
    try:
        rows = db.execute(
            sa.text(
                """
                SELECT id, idempotency_key, metadata_json, wallet_address, created_at
                FROM onchain_vault_transactions
                WHERE person_id = :person_id
                  AND integration_mode = 'lombard'
                  AND status = 'success'
                  AND metadata_json->>'mock_usdc_ledger_credited' = 'true'
                ORDER BY created_at DESC
                LIMIT 100
                """
            ),
            {"person_id": str(person_id)},
        ).mappings().all()
    except Exception:
        return []
    return [dict(row) for row in rows]


def _record_anomaly(
    report: UserReconcileReport,
    db: Session,
    *,
    person_id: UUID,
    layer: str,
    discrepancy_type: str,
    severity: str,
    wallet_address: str | None = None,
    asset: str | None = None,
    db_amount: Decimal | None = None,
    onchain_amount: Decimal | None = None,
    delta: Decimal | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    item = {
        "layer": layer,
        "discrepancy_type": discrepancy_type,
        "severity": severity,
        "wallet_address": wallet_address,
        "asset": asset,
        "db_amount": _fmt(db_amount),
        "onchain_amount": _fmt(onchain_amount),
        "delta": _fmt(delta),
        "reference_type": reference_type,
        "reference_id": reference_id,
        "metadata_json": metadata_json,
    }
    report.anomalies.append(item)

    if report.dry_run or not report.persist_discrepancies:
        return

    _, created = DiscrepancyRepository.upsert_open(
        db,
        person_id=person_id,
        layer=layer,
        discrepancy_type=discrepancy_type,
        severity=severity,
        wallet_address=wallet_address,
        asset=asset,
        db_amount=db_amount,
        onchain_amount=onchain_amount,
        delta=delta,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata_json=metadata_json,
    )
    if created:
        report.discrepancies_written += 1
    else:
        report.discrepancies_skipped += 1


def build_user_reconcile_report(
    db: Session,
    *,
    person_id: UUID,
    dry_run: bool = True,
    persist_discrepancies: bool = False,
    chain_id: int = CHAIN_BASE,
) -> UserReconcileReport:
    if persist_discrepancies and dry_run:
        raise ValueError("persist_discrepancies nécessite dry_run=False")

    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    report = UserReconcileReport(
        person_id=str(person_id),
        dry_run=dry_run,
        persist_discrepancies=persist_discrepancies and not dry_run,
    )

    if not wallets:
        report.warnings.append("Aucun wallet Privy actif pour cette personne.")
        return report

    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=PENDING_STALE_HOURS)

    for wallet in wallets:
        addr = normalize_evm_address(wallet.address) or wallet.address
        wallet_report = build_wallet_reconcile_report(
            db,
            wallet_address=addr,
            chain_id=chain_id,
            dry_run=True,
            index_tx_hashes=False,
        )
        report.wallets.append(wallet_report.to_dict())

        for item in wallet_report.db_without_onchain_proof:
            reason = item.get("reason", "no_matching_raw_onchain_event")
            dtype = "admin_sim_deposit" if reason == "simulated_or_admin_credit" else "db_ledger_without_onchain_proof"
            sev = "P0" if dtype == "admin_sim_deposit" else "P1"
            _record_anomaly(
                report,
                db,
                person_id=person_id,
                layer="privy",
                discrepancy_type=dtype,
                severity=sev,
                wallet_address=addr,
                asset=item.get("asset"),
                db_amount=Decimal(str(item.get("amount", "0"))) if item.get("amount") else None,
                reference_type="deposit",
                reference_id=item.get("deposit_id"),
                metadata_json=item,
            )

        for item in wallet_report.onchain_without_db_ledger:
            _record_anomaly(
                report,
                db,
                person_id=person_id,
                layer="privy",
                discrepancy_type="onchain_event_without_db_ledger",
                severity="P1",
                wallet_address=addr,
                asset=item.get("asset"),
                onchain_amount=Decimal(str(item.get("amount_raw", "0"))) if item.get("amount_raw") else None,
                reference_type="raw_onchain_event",
                reference_id=item.get("event_id"),
                metadata_json=item,
            )

        for asset, delta_info in wallet_report.deltas_by_asset.items():
            if delta_info.get("within_dust_tolerance") == "False":
                led = Decimal(wallet_report.balances_ledger_by_asset.get(asset, "0"))
                oc = Decimal(wallet_report.balances_on_chain_by_asset.get(asset, "0"))
                _record_anomaly(
                    report,
                    db,
                    person_id=person_id,
                    layer="privy",
                    discrepancy_type="balance_ledger_vs_onchain",
                    severity="P1",
                    wallet_address=addr,
                    asset=asset,
                    db_amount=led,
                    onchain_amount=oc,
                    delta=oc - led,
                    reference_type="asset",
                    reference_id=asset,
                )

    deposits = PersonWalletDepositRepository.list_for_person(db, person_id, limit=5000)
    for dep in deposits:
        key = (dep.idempotency_key or "").lower()
        tx = (dep.tx_hash or "").lower()
        if key.startswith("admin_sim_") or tx.startswith("0xsim"):
            _record_anomaly(
                report,
                db,
                person_id=person_id,
                layer="privy",
                discrepancy_type="admin_sim_deposit",
                severity="P0",
                wallet_address=dep.to_address,
                asset=dep.asset,
                db_amount=Decimal(str(dep.amount)),
                reference_type="deposit",
                reference_id=str(dep.id),
                metadata_json={"tx_hash": dep.tx_hash, "idempotency_key": dep.idempotency_key},
            )

        meta = dep.metadata_json if isinstance(dep.metadata_json, dict) else {}
        if meta.get("mock_usdc_ledger_credited") or meta.get("lombard_mock"):
            _record_anomaly(
                report,
                db,
                person_id=person_id,
                layer="lombard",
                discrepancy_type="lombard_mock_privy_ledger_credit",
                severity="P0",
                wallet_address=dep.to_address,
                asset=dep.asset,
                db_amount=Decimal(str(dep.amount)),
                reference_type="deposit",
                reference_id=str(dep.id),
                metadata_json=meta,
            )

    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.desc())
        .limit(500)
        .all()
    )
    for swap in swaps:
        if _swap_missing_actual_settlement(swap):
            _record_anomaly(
                report,
                db,
                person_id=person_id,
                layer="lifi",
                discrepancy_type="swap_confirmed_without_settlement",
                severity="P1",
                asset=str(swap.to_asset).upper(),
                db_amount=Decimal(str(swap.estimated_receive or 0)),
                reference_type="swap",
                reference_id=str(swap.id),
                metadata_json={
                    "tx_hash": swap.tx_hash,
                    "status": swap.status,
                    "audit_tail": (swap.audit_log or [])[-3:] if isinstance(swap.audit_log, list) else [],
                },
            )

        if swap.status == SwapSessionStatus.SUBMITTED.value:
            updated = swap.updated_at or swap.created_at
            if updated and updated.replace(tzinfo=timezone.utc) < stale_cutoff:
                _record_anomaly(
                    report,
                    db,
                    person_id=person_id,
                    layer="lifi",
                    discrepancy_type="swap_pending_stale",
                    severity="P2",
                    reference_type="swap",
                    reference_id=str(swap.id),
                    metadata_json={"tx_hash": swap.tx_hash, "updated_at": updated.isoformat()},
                )

    for vault_row in _collect_vault_pending(db, person_id):
        created = vault_row.get("created_at")
        if created and created.replace(tzinfo=timezone.utc) < stale_cutoff:
            layer = "morpho"
            mode = str(vault_row.get("integration_mode") or "").lower()
            if "lombard" in mode:
                layer = "lombard"
            elif "ledgity" in mode:
                layer = "ledgity"
            _record_anomaly(
                report,
                db,
                person_id=person_id,
                layer=layer,
                discrepancy_type="vault_tx_pending_stale",
                severity="P2",
                wallet_address=vault_row.get("wallet_address"),
                reference_type="vault_tx",
                reference_id=str(vault_row.get("id")),
                metadata_json=vault_row,
            )

    for mock_row in _collect_lombard_mock_credits(db, person_id):
        _record_anomaly(
            report,
            db,
            person_id=person_id,
            layer="lombard",
            discrepancy_type="lombard_mock_historical_credit",
            severity="P0",
            wallet_address=mock_row.get("wallet_address"),
            reference_type="vault_tx",
            reference_id=str(mock_row.get("id")),
            metadata_json=mock_row,
        )

    open_rows = []
    intent_discrepancies_written = 0
    if not dry_run and persist_discrepancies:
        open_rows = DiscrepancyRepository.list_open_for_person(db, person_id)
        from services.transaction_intents.transaction_intent_reconciliation import (
            persist_intent_discrepancies,
        )

        intent_discrepancies_written = persist_intent_discrepancies(db, person_id)

    report.summary = {
        "wallet_count": len(wallets),
        "anomaly_count": len(report.anomalies),
        "by_severity": {
            "P0": sum(1 for a in report.anomalies if a.get("severity") == "P0"),
            "P1": sum(1 for a in report.anomalies if a.get("severity") == "P1"),
            "P2": sum(1 for a in report.anomalies if a.get("severity") == "P2"),
        },
        "open_discrepancies_persisted": len(open_rows),
        "intent_discrepancies_persisted": intent_discrepancies_written,
    }

    return report

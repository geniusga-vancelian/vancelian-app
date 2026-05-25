"""Synchronisation ``person_crypto_wallets`` depuis payloads Privy (API / JWT)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.privy_wallet.asset_mapping import parse_caip2_chain_id
from services.privy_wallet.privy_api_client import (
    PrivyApiError,
    extract_wallet_linked_accounts,
    fetch_privy_user,
    privy_server_api_configured,
)

_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class NormalizedPrivyWalletInput:
    address: str
    chain_type: str
    chain_id: Optional[int]
    wallet_type: str
    privy_wallet_id: Optional[str] = None


@dataclass(frozen=True)
class PrivyWalletSyncResult:
    synced_count: int
    wallets: list[dict[str, Any]]
    source: str
    privy_user_id: Optional[str] = None
    api_error: Optional[str] = None


def normalize_privy_wallet_payload(raw: dict[str, Any]) -> Optional[NormalizedPrivyWalletInput]:
    address = str(raw.get("address") or "").strip()
    if not _EVM_ADDRESS.match(address):
        return None

    chain_raw = raw.get("chain_type") or raw.get("chainType") or "ethereum"
    chain_norm = str(chain_raw).strip().lower()
    chain_type = "evm" if chain_norm in ("evm", "ethereum") else chain_norm

    chain_id = parse_caip2_chain_id(raw.get("chain_id") or raw.get("chainId"))

    wallet_type = (
        raw.get("wallet_type")
        or raw.get("connector_type")
        or raw.get("wallet_client_type")
        or raw.get("walletClientType")
        or "embedded"
    )
    wallet_type = str(wallet_type).strip().lower() or "embedded"

    privy_wallet_id = str(raw.get("id") or raw.get("wallet_id") or raw.get("walletId") or "").strip() or None

    return NormalizedPrivyWalletInput(
        address=address.lower(),
        chain_type=chain_type,
        chain_id=chain_id,
        wallet_type=wallet_type,
        privy_wallet_id=privy_wallet_id,
    )


def upsert_normalized_wallets_for_person(
    db: Session,
    *,
    person_id: UUID,
    pe_client_id: Optional[UUID],
    wallets: list[NormalizedPrivyWalletInput],
    primary_index: int = 0,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, w in enumerate(wallets):
        metadata: dict[str, Any] = {"sync_source": "privy_reconcile"}
        if w.privy_wallet_id:
            metadata["privy_wallet_id"] = w.privy_wallet_id
        row = upsert_person_crypto_wallet(
            db,
            person_id=person_id,
            pe_client_id=pe_client_id,
            provider=PROVIDER_PRIVY,
            wallet_type=w.wallet_type,
            chain_type=w.chain_type,
            address=w.address,
            chain_id=w.chain_id,
            is_primary=(idx == primary_index),
            metadata_json=metadata,
        )
        out.append(
            {
                "id": str(row.id),
                "address": row.address,
                "chain_type": row.chain_type,
                "chain_id": row.chain_id,
                "wallet_type": row.wallet_type,
                "provider": row.provider,
                "is_primary": bool(row.is_primary),
            }
        )
    return out


def sync_wallets_from_privy_linked_accounts(
    db: Session,
    *,
    person_id: UUID,
    pe_client_id: Optional[UUID],
    linked_accounts: list[dict[str, Any]],
    source: str,
) -> PrivyWalletSyncResult:
    normalized: list[NormalizedPrivyWalletInput] = []
    for raw in linked_accounts:
        if str(raw.get("type") or "").strip().lower() == "wallet" or raw.get("address"):
            item = normalize_privy_wallet_payload(raw)
            if item is not None:
                normalized.append(item)

    synced = upsert_normalized_wallets_for_person(
        db, person_id=person_id, pe_client_id=pe_client_id, wallets=normalized
    )
    return PrivyWalletSyncResult(synced_count=len(synced), wallets=synced, source=source)


def reconcile_person_privy_wallets(
    db: Session,
    *,
    person_id: UUID,
    pe_client_id: Optional[UUID],
    privy_user_id: str,
    manual_address: Optional[str] = None,
    manual_chain_id: Optional[int] = None,
) -> PrivyWalletSyncResult:
    """Réconciliation admin : API Privy puis repli adresse manuelle."""
    api_error: Optional[str] = None
    if privy_server_api_configured():
        try:
            payload = fetch_privy_user(privy_user_id)
            accounts = extract_wallet_linked_accounts(payload)
            if accounts:
                result = sync_wallets_from_privy_linked_accounts(
                    db,
                    person_id=person_id,
                    pe_client_id=pe_client_id,
                    linked_accounts=accounts,
                    source="privy_api",
                )
                result = PrivyWalletSyncResult(
                    synced_count=result.synced_count,
                    wallets=result.wallets,
                    source=result.source,
                    privy_user_id=privy_user_id,
                )
                if result.synced_count > 0:
                    return result
        except PrivyApiError as exc:
            api_error = str(exc)

    manual = (manual_address or "").strip()
    if manual:
        item = normalize_privy_wallet_payload(
            {
                "address": manual,
                "chain_type": "ethereum",
                "chain_id": manual_chain_id or 1,
                "wallet_type": "embedded",
            }
        )
        if item is None:
            raise PrivyApiError("privy.reconcile.invalid_address", "Adresse EVM invalide.")
        synced = upsert_normalized_wallets_for_person(
            db, person_id=person_id, pe_client_id=pe_client_id, wallets=[item]
        )
        return PrivyWalletSyncResult(
            synced_count=len(synced),
            wallets=synced,
            source="manual_address",
            privy_user_id=privy_user_id,
            api_error=api_error,
        )

    if api_error:
        raise PrivyApiError(
            "privy.reconcile.api_failed",
            f"{api_error} — fournissez une adresse manuelle si besoin.",
        )
    raise PrivyApiError(
        "privy.reconcile.no_wallets",
        "Aucun wallet trouvé côté Privy pour cet utilisateur.",
    )

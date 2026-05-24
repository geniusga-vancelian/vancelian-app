"""Création / résolution wallets Privy user-owned (Solana) — serveur uniquement."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import PersonExternalIdentity
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    PersonIdentityBridgeError,
    get_pe_client_for_person,
    upsert_person_crypto_wallet,
)
from services.privy_wallet.privy_api_client import (
    PrivyApiError,
    create_privy_wallet,
    extract_solana_wallet_linked_accounts,
    fetch_privy_user,
    privy_server_api_configured,
)

CHAIN_TYPE_SOLANA = "solana"
_SOLANA_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class PrivySolanaWalletError(ValueError):
    def __init__(self, code: str, message: str, *, http_status: int = 400):
        self.code = code
        self.http_status = http_status
        super().__init__(message)


@dataclass(frozen=True)
class SolanaWalletResult:
    chain_type: str
    address: str
    wallet_id: str
    created: bool
    person_wallet_id: UUID


@dataclass(frozen=True)
class SolanaWalletStatus:
    """État wallet Solana : absent, présent côté Privy seulement, ou lié au compte Vancelian."""

    status: str
    chain_type: str = CHAIN_TYPE_SOLANA
    address: Optional[str] = None
    wallet_id: Optional[str] = None
    person_wallet_id: Optional[UUID] = None
    created: bool = False


def normalize_solana_address(address: str | None) -> str | None:
    if address is None:
        return None
    addr = str(address).strip()
    if not addr or not _SOLANA_ADDRESS.match(addr):
        return None
    return addr


def get_privy_user_id_for_person(db: Session, person_id: UUID) -> str:
    """Résout ``privy_user_id`` depuis ``person_external_identities`` (pas de création Privy ici)."""
    row = (
        db.query(PersonExternalIdentity)
        .filter(
            PersonExternalIdentity.person_id == person_id,
            PersonExternalIdentity.provider == PROVIDER_PRIVY,
        )
        .first()
    )
    if row is None or not (row.external_subject or "").strip():
        raise PrivySolanaWalletError(
            "privy.solana_wallet.privy_not_linked",
            "Compte Privy non lié. Connectez-vous via Privy avant de créer un wallet Solana.",
            http_status=400,
        )
    return str(row.external_subject).strip()


def find_solana_wallet_row(db: Session, person_id: UUID):
    from database import PersonCryptoWallet

    return (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == person_id,
            PersonCryptoWallet.provider == PROVIDER_PRIVY,
            PersonCryptoWallet.chain_type == CHAIN_TYPE_SOLANA,
            PersonCryptoWallet.revoked_at.is_(None),
        )
        .order_by(PersonCryptoWallet.created_at.asc())
        .first()
    )


def _persist_solana_wallet(
    db: Session,
    *,
    person_id: UUID,
    address: str,
    privy_wallet_id: str | None,
    wallet_type: str = "embedded",
) -> SolanaWalletResult:
    pe = get_pe_client_for_person(db, person_id=person_id)
    metadata: dict[str, Any] | None = None
    if privy_wallet_id:
        metadata = {"privy_wallet_id": privy_wallet_id}

    row = upsert_person_crypto_wallet(
        db,
        person_id=person_id,
        pe_client_id=pe.id if pe else None,
        provider=PROVIDER_PRIVY,
        wallet_type=wallet_type,
        chain_type=CHAIN_TYPE_SOLANA,
        chain_id=None,
        address=address,
        is_primary=False,
        metadata_json=metadata,
    )
    wallet_id = privy_wallet_id or str(row.id)
    return SolanaWalletResult(
        chain_type=CHAIN_TYPE_SOLANA,
        address=row.address,
        wallet_id=wallet_id,
        created=False,
        person_wallet_id=row.id,
    )


def _result_from_row(row) -> SolanaWalletResult:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    privy_wallet_id = meta.get("privy_wallet_id") if isinstance(meta, dict) else None
    return SolanaWalletResult(
        chain_type=CHAIN_TYPE_SOLANA,
        address=row.address,
        wallet_id=str(privy_wallet_id or row.id),
        created=False,
        person_wallet_id=row.id,
    )


def _peek_solana_from_privy_linked_accounts(
    privy_user_id: str,
) -> Optional[dict[str, str]]:
    """Lit un wallet Solana Privy sans persistance DB (mode « link to Vancelian »)."""
    if not privy_server_api_configured():
        return None
    try:
        user_payload = fetch_privy_user(privy_user_id)
    except PrivyApiError:
        return None

    linked = extract_solana_wallet_linked_accounts(user_payload)
    if not linked:
        return None

    first = linked[0]
    address = normalize_solana_address(first.get("address"))
    if not address:
        return None

    privy_wallet_id = str(first.get("id") or first.get("wallet_id") or "").strip()
    return {
        "address": address,
        "wallet_id": privy_wallet_id or address,
    }


def get_user_solana_wallet_status(db: Session, person_id: UUID) -> SolanaWalletStatus:
    """Résout missing / unlinked (Privy seul) / linked (person_crypto_wallets)."""
    existing = get_user_solana_wallet(db, person_id)
    if existing is not None:
        return SolanaWalletStatus(
            status="linked",
            address=existing.address,
            wallet_id=existing.wallet_id,
            person_wallet_id=existing.person_wallet_id,
            created=False,
        )

    try:
        privy_user_id = get_privy_user_id_for_person(db, person_id)
    except PrivySolanaWalletError:
        return SolanaWalletStatus(status="missing")

    peek = _peek_solana_from_privy_linked_accounts(privy_user_id)
    if peek is not None:
        return SolanaWalletStatus(
            status="unlinked",
            address=peek["address"],
            wallet_id=peek["wallet_id"],
        )

    return SolanaWalletStatus(status="missing")


def get_user_solana_wallet(db: Session, person_id: UUID) -> Optional[SolanaWalletResult]:
    row = find_solana_wallet_row(db, person_id)
    if row is None:
        return None
    return _result_from_row(row)


def _sync_solana_from_privy_linked_accounts(
    db: Session,
    *,
    person_id: UUID,
    privy_user_id: str,
) -> Optional[SolanaWalletResult]:
    if not privy_server_api_configured():
        return None
    try:
        user_payload = fetch_privy_user(privy_user_id)
    except PrivyApiError:
        return None

    linked = extract_solana_wallet_linked_accounts(user_payload)
    if not linked:
        return None

    first = linked[0]
    address = normalize_solana_address(first.get("address"))
    if not address:
        return None

    privy_wallet_id = str(first.get("id") or first.get("wallet_id") or "").strip() or None
    wallet_type = str(
        first.get("wallet_type")
        or first.get("wallet_client_type")
        or first.get("walletClientType")
        or "embedded"
    ).strip() or "embedded"

    return _persist_solana_wallet(
        db,
        person_id=person_id,
        address=address,
        privy_wallet_id=privy_wallet_id,
        wallet_type=wallet_type,
    )


def create_user_solana_wallet(db: Session, person_id: UUID) -> SolanaWalletResult:
    """Crée un wallet Solana via l’API Privy (sans get_or_create — préférer ``get_or_create_user_solana_wallet``)."""
    if not privy_server_api_configured():
        raise PrivySolanaWalletError(
            "privy.solana_wallet.api_not_configured",
            "Configuration Privy serveur manquante (PRIVY_APP_ID / PRIVY_APP_SECRET).",
            http_status=503,
        )

    privy_user_id = get_privy_user_id_for_person(db, person_id)
    existing = find_solana_wallet_row(db, person_id)
    if existing is not None:
        return _result_from_row(existing)

    synced = _sync_solana_from_privy_linked_accounts(
        db, person_id=person_id, privy_user_id=privy_user_id
    )
    if synced is not None:
        return synced

    try:
        created_payload = create_privy_wallet(
            privy_user_id=privy_user_id,
            chain_type=CHAIN_TYPE_SOLANA,
            idempotency_key=f"solana-wallet-{person_id}",
        )
    except PrivyApiError as exc:
        raise PrivySolanaWalletError(
            exc.code,
            str(exc),
            http_status=exc.http_status or 502,
        ) from exc

    address = normalize_solana_address(created_payload.get("address"))
    if not address:
        raise PrivySolanaWalletError(
            "privy.solana_wallet.invalid_response",
            "Réponse Privy sans adresse Solana valide.",
            http_status=502,
        )

    privy_wallet_id = str(created_payload.get("id") or "").strip() or None
    try:
        result = _persist_solana_wallet(
            db,
            person_id=person_id,
            address=address,
            privy_wallet_id=privy_wallet_id,
        )
    except PersonIdentityBridgeError as exc:
        raise PrivySolanaWalletError(
            "privy.solana_wallet.persist_failed",
            str(exc),
            http_status=409,
        ) from exc

    return SolanaWalletResult(
        chain_type=result.chain_type,
        address=result.address,
        wallet_id=result.wallet_id,
        created=True,
        person_wallet_id=result.person_wallet_id,
    )


def get_or_create_user_solana_wallet(db: Session, person_id: UUID) -> SolanaWalletResult:
    """Retourne le wallet Solana existant ou en crée un via Privy."""
    existing = get_user_solana_wallet(db, person_id)
    if existing is not None:
        return existing

    privy_user_id = get_privy_user_id_for_person(db, person_id)
    synced = _sync_solana_from_privy_linked_accounts(
        db, person_id=person_id, privy_user_id=privy_user_id
    )
    if synced is not None:
        return synced

    return create_user_solana_wallet(db, person_id)

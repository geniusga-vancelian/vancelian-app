"""Résolution du wallet signataire pour quotes / exécution swap LI.FI."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from database import PersonCryptoWallet
from services.lifi.lifi_validation_service import SwapValidationError, wallet_chain_type_for_chain
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.repository import PersonCryptoWalletRepository

PROVIDER_PRIVY = "privy"
PROVIDER_EXTERNAL = "external"

SIGNING_MODE_PRIVY = "privy_embedded"
SIGNING_MODE_EXTERNAL = "external_evm"


def _wallet_chain_type_matches(stored: str | None, expected: str) -> bool:
    s = (stored or "").strip().lower()
    e = (expected or "").strip().lower()
    if not s or not e:
        return False
    if s == e:
        return True
    evm_aliases = frozenset({"evm", "ethereum"})
    return s in evm_aliases and e in evm_aliases


def _is_verified_external_wallet(wallet: PersonCryptoWallet) -> bool:
    meta = wallet.metadata_json if isinstance(wallet.metadata_json, dict) else {}
    if meta.get("is_verified") is True:
        return True
    if meta.get("revoked_at"):
        return False
    return wallet.revoked_at is None


def _normalize_required_address(raw: str | None) -> str:
    normalized = normalize_evm_address((raw or "").strip())
    if not normalized:
        raise SwapValidationError("swap.invalid_signing_wallet", "Adresse wallet signataire invalide")
    return normalized


def resolve_swap_signing_wallet(
    db: Session,
    *,
    person_id: UUID,
    chain_key: str,
    signing_wallet_mode: str | None = None,
    signing_wallet_address: str | None = None,
) -> tuple[str, str]:
    """
    Retourne (mode, adresse checksum) pour LI.FI fromAddress / toAddress.

    ``privy_embedded`` : wallet Privy embedded actif pour la chaîne.
    ``external_evm`` : wallet externe vérifié (MetaMask / WalletConnect) — adresse requise.
    """
    mode = (signing_wallet_mode or SIGNING_MODE_PRIVY).strip().lower()
    if mode not in {SIGNING_MODE_PRIVY, SIGNING_MODE_EXTERNAL}:
        raise SwapValidationError(
            "swap.invalid_signing_mode",
            "Mode wallet signataire invalide (privy_embedded | external_evm)",
        )

    expected_type = wallet_chain_type_for_chain(chain_key)
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)

    if mode == SIGNING_MODE_EXTERNAL:
        address = _resolve_external_signing_wallet(
            wallets,
            expected_type=expected_type,
            signing_wallet_address=signing_wallet_address,
        )
        return mode, address

    address = _resolve_privy_signing_wallet(wallets, expected_type=expected_type)
    return mode, address


def _resolve_privy_signing_wallet(
    wallets: list[PersonCryptoWallet],
    *,
    expected_type: str,
) -> str:
    for wallet in wallets:
        if (wallet.provider or "").strip().lower() != PROVIDER_PRIVY:
            continue
        if not _wallet_chain_type_matches(wallet.chain_type, expected_type):
            continue
        normalized = normalize_evm_address(wallet.address)
        if normalized:
            return normalized

    raise SwapValidationError(
        "swap.wallet_missing",
        f"Aucun wallet Privy embedded lié pour cette opération ({expected_type})",
    )


def _resolve_external_signing_wallet(
    wallets: list[PersonCryptoWallet],
    *,
    expected_type: str,
    signing_wallet_address: str | None,
) -> str:
    if not signing_wallet_address:
        raise SwapValidationError(
            "swap.signing_wallet_required",
            "Adresse wallet externe requise pour le quote LI.FI",
        )

    target = _normalize_required_address(signing_wallet_address)

    for wallet in wallets:
        if (wallet.provider or "").strip().lower() != PROVIDER_EXTERNAL:
            continue
        normalized = normalize_evm_address(wallet.address)
        if not normalized or normalized.lower() != target.lower():
            continue
        if not _is_verified_external_wallet(wallet):
            raise SwapValidationError(
                "swap.external_wallet_unverified",
                "Wallet externe non vérifié — signez le message depuis Mon wallet",
            )
        if not _wallet_chain_type_matches(wallet.chain_type, expected_type):
            continue
        return normalized

    raise SwapValidationError(
        "swap.external_wallet_not_found",
        "Wallet externe introuvable ou non autorisé pour cette personne",
    )


def read_signing_wallet_from_audit(audit_log: Any) -> tuple[str | None, str | None]:
    """Wallet signataire — priorité ``wallet_locked`` (confirm_execute) puis ``quote_requested``."""
    if not isinstance(audit_log, list):
        return None, None
    locked: tuple[str | None, str | None] | None = None
    quoted: tuple[str | None, str | None] | None = None
    for entry in audit_log:
        if not isinstance(entry, dict):
            continue
        event = entry.get("event")
        mode = str(entry.get("signing_wallet_mode") or "") or None
        address = str(entry.get("signing_wallet_address") or "") or None
        if event == "wallet_locked" and address:
            locked = (mode, address)
        elif event == "quote_requested" and address and quoted is None:
            quoted = (mode, address)
    if locked is not None:
        return locked
    if quoted is not None:
        return quoted
    return None, None


def assert_locked_signing_wallet_match(
    swap,
    *,
    connected_wallet_address: str | None,
) -> None:
    """Refuse approval/submit si le wallet connecté diffère du wallet verrouillé au confirm."""
    if not connected_wallet_address or not str(connected_wallet_address).strip():
        return
    _, locked = read_signing_wallet_from_audit(swap.audit_log)
    if not locked:
        return
    connected = normalize_evm_address(connected_wallet_address)
    expected = normalize_evm_address(locked)
    if connected and expected and connected.lower() != expected.lower():
        raise SwapValidationError(
            "swap.wallet_mismatch",
            "Le wallet connecté ne correspond plus au devis — refaites une estimation.",
        )

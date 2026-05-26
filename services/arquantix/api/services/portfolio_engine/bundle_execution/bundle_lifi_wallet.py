"""Résolution wallet Privy EVM pour bundles LI.FI Base (réseau ≠ famille chain_type)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from database import PersonCryptoWallet
from services.privy_wallet.asset_mapping import normalize_evm_address
from services.privy_wallet.repository import PersonCryptoWalletRepository

from .bundle_lifi_validation import BundleLifiValidationError
from .lifi_base_config import BUNDLE_LIFI_CHAIN_KEY

BASE_LIFI_CHAIN_ID = 8453
PRIVY_PROVIDER = "privy"

# Famille technologique — un wallet EVM signe sur Base, Ethereum, Arbitrum, etc.
EVM_WALLET_CHAIN_TYPES = frozenset({"evm", "ethereum"})

SIGNING_MODE_PRIVY = "privy_embedded"


def wallet_supports_evm_network(
    wallet: PersonCryptoWallet,
    *,
    network_chain_key: str,
    network_chain_id: int | None = BASE_LIFI_CHAIN_ID,
) -> bool:
    """
    ``chain_type`` = famille (evm / ethereum), pas le réseau L2.
    ``network_chain_key`` = base | ethereum | … (réseau LI.FI).
    """
    stored = (wallet.chain_type or "").strip().lower()
    network = (network_chain_key or "").strip().lower()

    if stored in ("solana", "sol"):
        return False

    if stored in EVM_WALLET_CHAIN_TYPES:
        return True

    if stored == network:
        return True

    if network_chain_id is not None and wallet.chain_id is not None:
        try:
            if int(wallet.chain_id) == int(network_chain_id):
                return True
        except (TypeError, ValueError):
            pass

    return False


def _pick_privy_evm_wallet(
    wallets: list[PersonCryptoWallet],
    *,
    network_chain_key: str,
    network_chain_id: int | None,
) -> PersonCryptoWallet | None:
    privy = [
        w
        for w in wallets
        if (w.provider or "").strip().lower() == PRIVY_PROVIDER and w.revoked_at is None
    ]
    candidates = [
        w for w in privy if wallet_supports_evm_network(
            w, network_chain_key=network_chain_key, network_chain_id=network_chain_id,
        )
    ]
    if not candidates:
        return None

    def _sort_key(w: PersonCryptoWallet) -> tuple:
        chain_id_match = (
            network_chain_id is not None
            and w.chain_id is not None
            and int(w.chain_id) == int(network_chain_id)
        )
        stored = (w.chain_type or "").strip().lower()
        network = network_chain_key.strip().lower()
        return (
            0 if w.is_primary else 1,
            0 if chain_id_match else 1,
            0 if stored == network else 1,
            0 if stored in EVM_WALLET_CHAIN_TYPES else 1,
        )

    return sorted(candidates, key=_sort_key)[0]


def resolve_evm_wallet_for_person(
    db: Session,
    *,
    person_id: UUID,
    chain: str = BUNDLE_LIFI_CHAIN_KEY,
    chain_id: int | None = BASE_LIFI_CHAIN_ID,
) -> str:
    """Adresse checksum du wallet Privy embedded EVM compatible réseau Base."""
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    picked = _pick_privy_evm_wallet(
        wallets, network_chain_key=chain, network_chain_id=chain_id,
    )
    if picked is None:
        raise BundleLifiValidationError(
            "bundle.lifi.wallet_missing",
            f"Aucun wallet Privy embedded EVM pour {chain} (chain_id={chain_id})",
        )
    normalized = normalize_evm_address(picked.address)
    if not normalized:
        raise BundleLifiValidationError(
            "bundle.lifi.wallet_invalid",
            "Adresse wallet Privy invalide",
        )
    return normalized


def resolve_evm_wallet_for_client(
    db: Session,
    *,
    client_id: UUID,
    chain: str = BUNDLE_LIFI_CHAIN_KEY,
    chain_id: int | None = BASE_LIFI_CHAIN_ID,
) -> str:
    from services.portfolio_engine.clients.models import Client

    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None or client.person_id is None:
        raise BundleLifiValidationError(
            "bundle.lifi.no_person_id",
            "Client sans person_id — wallet Privy requis",
        )
    return resolve_evm_wallet_for_person(
        db, person_id=client.person_id, chain=chain, chain_id=chain_id,
    )


def resolve_bundle_lifi_signing_wallet(
    db: Session,
    *,
    person_id: UUID,
    chain_key: str = BUNDLE_LIFI_CHAIN_KEY,
    chain_id: int | None = BASE_LIFI_CHAIN_ID,
) -> tuple[str, str]:
    """(mode, address) pour quotes / legs bundle — toujours privy_embedded EVM."""
    address = resolve_evm_wallet_for_person(
        db, person_id=person_id, chain=chain_key, chain_id=chain_id,
    )
    return SIGNING_MODE_PRIVY, address

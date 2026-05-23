"""Admin-only simulation for Privy wallet deposits (dev / staging)."""
from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.orm import Session

from database import Person, PersonExternalIdentity
from services.auth.person_identity_bridge import PROVIDER_PRIVY, get_pe_client_for_person
from services.exchange.assets import ASSET_PRECISION

from .asset_mapping import ERC20_CONTRACT_TO_ASSET
from .enums import PrivyWebhookEventStatus
from .repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from .schemas import (
    PrivyReconcileWalletItem,
    PrivyReconcileWalletsRequest,
    PrivyReconcileWalletsResponse,
    PrivySimulateDepositRequest,
    PrivySimulateDepositResponse,
)
from .service import _format_decimal
from .wallet_sync import reconcile_person_privy_wallets
from .webhook_service import FUNDS_DEPOSITED_EVENT, PrivyWebhookProcessor


class PrivyWalletNotFoundError(ValueError):
    pass


class PrivySimulateDepositError(ValueError):
    pass


class PrivyWalletAdminService:

    def __init__(self) -> None:
        self._processor = PrivyWebhookProcessor()
        self._wallet_repo = PersonCryptoWalletRepository()
        self._deposit_repo = PersonWalletDepositRepository()
        self._balance_repo = PersonWalletBalanceRepository()

    def simulate_deposit(
        self,
        db: Session,
        payload: PrivySimulateDepositRequest,
    ) -> PrivySimulateDepositResponse:
        person = db.query(Person).filter(Person.id == payload.person_id).first()
        if person is None:
            raise PrivyWalletNotFoundError("Person not found")

        wallet = self._resolve_wallet(db, person_id=payload.person_id, wallet_address=payload.wallet_address)
        asset = payload.asset.strip().upper()
        amount = self._parse_human_amount(payload.amount)
        chain_id = payload.chain_id if payload.chain_id is not None else (wallet.chain_id or 1)

        tx_hash = f"0xsim{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
        idempotency_key = f"admin_sim_{uuid.uuid4().hex}"
        log_index = int(uuid.uuid4().int % 1_000_000)

        data: dict = {
            "to_address": wallet.address,
            "from_address": f"0x{uuid.uuid4().hex[:40]}",
            "transaction_hash": tx_hash,
            "chain_id": f"eip155:{chain_id}",
            "asset": {"type": "native", "symbol": asset},
            "amount": _human_to_atomic(amount, asset),
            "log_index": log_index,
            "block_number": 99_999_999,
            "confirmations": 12,
        }

        contract = _contract_for_asset(chain_id, asset)
        if contract:
            data["contract_address"] = contract
            data["asset"] = {"type": "erc20", "symbol": asset}

        webhook_payload = {
            "type": FUNDS_DEPOSITED_EVENT,
            "id": f"sim_{uuid.uuid4().hex[:16]}",
            "idempotency_key": idempotency_key,
            "data": data,
        }

        event = self._processor.store_raw_event(
            db,
            event_type=FUNDS_DEPOSITED_EVENT,
            payload=webhook_payload,
            svix_id=f"admin_sim_{uuid.uuid4().hex[:12]}",
            idempotency_key=idempotency_key,
            external_reference=tx_hash,
        )
        status = self._processor.process_event(db, event)

        if status == PrivyWebhookEventStatus.FAILED.value:
            raise PrivySimulateDepositError(event.error_message or "Deposit simulation failed")

        deposit = self._deposit_repo.find_by_chain_tx(
            db, chain_id=chain_id, tx_hash=tx_hash, log_index=log_index
        )
        new_balance: str | None = None
        if deposit is not None:
            for row in self._balance_repo.list_for_person(db, payload.person_id):
                if row.person_crypto_wallet_id == wallet.id and row.asset == asset:
                    new_balance = _format_decimal(row.balance)
                    break

        return PrivySimulateDepositResponse(
            event_id=event.id,
            deposit_id=deposit.id if deposit else event.linked_deposit_id,
            processing_status=status,
            asset=asset,
            amount=_format_decimal(amount),
            new_balance=new_balance,
            tx_hash=tx_hash,
            message=f"Dépôt simulé : {_format_decimal(amount)} {asset} crédité sur le wallet Privy.",
        )

    @staticmethod
    def _resolve_wallet(db: Session, *, person_id: UUID, wallet_address: str | None):
        wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
        if not wallets:
            raise PrivyWalletNotFoundError("Aucun wallet Privy actif pour cette personne")

        if wallet_address:
            wallet = PersonCryptoWalletRepository.find_active_by_address(db, wallet_address)
            if wallet is None or wallet.person_id != person_id:
                raise PrivyWalletNotFoundError("Wallet Privy introuvable pour cette personne")
            return wallet

        return wallets[0]

    @staticmethod
    def _parse_human_amount(raw: str) -> Decimal:
        text = (raw or "").strip().replace(",", ".")
        if not text:
            raise PrivySimulateDepositError("Montant requis")
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise PrivySimulateDepositError(f"Montant invalide : {raw}") from exc
        if amount <= 0:
            raise PrivySimulateDepositError("Le montant doit être strictement positif")
        return amount

    def reconcile_wallets(
        self,
        db: Session,
        payload: PrivyReconcileWalletsRequest,
    ) -> PrivyReconcileWalletsResponse:
        identity = (
            db.query(PersonExternalIdentity)
            .filter(
                PersonExternalIdentity.person_id == payload.person_id,
                PersonExternalIdentity.provider == PROVIDER_PRIVY,
            )
            .order_by(PersonExternalIdentity.created_at.asc())
            .first()
        )
        if identity is None:
            raise PrivyWalletNotFoundError(
                "Aucune identité Privy liée à cette personne — lier Privy côté app d’abord."
            )

        pe = get_pe_client_for_person(db, person_id=payload.person_id)
        result = reconcile_person_privy_wallets(
            db,
            person_id=payload.person_id,
            pe_client_id=pe.id if pe else None,
            privy_user_id=identity.external_subject,
            manual_address=payload.manual_address,
            manual_chain_id=payload.chain_id,
        )
        msg = f"{result.synced_count} wallet(s) synchronisé(s) ({result.source})."
        if result.api_error and result.source == "manual_address":
            msg += f" API Privy : {result.api_error}"

        return PrivyReconcileWalletsResponse(
            synced_count=result.synced_count,
            wallets=[PrivyReconcileWalletItem(**w) for w in result.wallets],
            source=result.source,
            privy_user_id=result.privy_user_id,
            api_error=result.api_error,
            message=msg,
        )


def _human_to_atomic(amount: Decimal, asset: str) -> str:
    precision = ASSET_PRECISION.get(asset.upper(), 18)
    atomic = amount * (Decimal(10) ** precision)
    return str(int(atomic))


def _contract_for_asset(chain_id: int, asset: str) -> str | None:
    contracts = ERC20_CONTRACT_TO_ASSET.get(chain_id, {})
    for address, symbol in contracts.items():
        if symbol.upper() == asset.upper():
            return address
    return None

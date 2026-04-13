"""Service layer for Custody module — fiat accounts, simulations, ledger integration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.ledger_accounts.models import LedgerAccount
from services.portfolio_engine.ledger_accounts.repository import LedgerAccountRepository
from services.portfolio_engine.ledger_entries.service import LedgerEntryService

from .enums import (
    CustodyAccountStatus,
    CustodyAccountType,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
)
from .models import CustodyAccount, CustodyAccountBalance, CustodyTransaction
from .repository import (
    CustodyAccountRepository,
    CustodyBalanceRepository,
    CustodyProviderRepository,
    CustodyTransactionRepository,
    CustodyWebhookEventRepository,
)
from .schemas import (
    AccountCreate,
    InternalTransferRequest,
    ProviderCreate,
    SimulateDepositRequest,
    SimulateWithdrawalRequest,
)
from .identity_resolution import enrichment_fields_for_pe_client
from .state_machine import validate_transition

logger = logging.getLogger(__name__)


class InsufficientFundsError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class SettlementAccountNotFoundError(Exception):
    pass


class DuplicateAccountError(Exception):
    pass


class CurrencyMismatchError(Exception):
    pass


class DuplicateReferenceError(Exception):
    pass


class InvalidTransferError(Exception):
    pass


class CustodyService:

    def __init__(self) -> None:
        self._provider_repo = CustodyProviderRepository()
        self._account_repo = CustodyAccountRepository()
        self._balance_repo = CustodyBalanceRepository()
        self._tx_repo = CustodyTransactionRepository()
        self._webhook_repo = CustodyWebhookEventRepository()
        self._ledger_account_repo = LedgerAccountRepository()
        self._ledger_entry_svc = LedgerEntryService()

    # ------------------------------------------------------------------
    # Currency validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_currency_chain(
        payload_currency: str,
        account: CustodyAccount,
        balance: CustodyAccountBalance,
        ledger_account: LedgerAccount | None = None,
    ) -> None:
        """Ensure currency is consistent across the entire chain."""
        if account.currency != payload_currency:
            raise CurrencyMismatchError(
                f"Currency mismatch: payload={payload_currency}, account={account.currency}"
            )
        if balance.currency != payload_currency:
            raise CurrencyMismatchError(
                f"Currency mismatch: payload={payload_currency}, balance={balance.currency}"
            )
        if ledger_account and ledger_account.currency != payload_currency:
            raise CurrencyMismatchError(
                f"Currency mismatch: payload={payload_currency}, ledger={ledger_account.currency}"
            )

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def create_provider(self, db: Session, payload: ProviderCreate, actor: ActorContext):
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata") or {}
        provider = self._provider_repo.create(db, data=data)
        AuditService.log_success(
            db,
            entity_type="custody_provider",
            entity_id=str(provider.id),
            action="custody_provider_created",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={"provider_id": str(provider.id), "name": payload.name},
        )
        return provider

    def list_providers(self, db: Session, *, skip: int = 0, limit: int = 50):
        return self._provider_repo.list(db, skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def _create_ledger_account(
        self,
        db: Session,
        *,
        client_id: UUID | None,
        account_type: str,
        account_code: str,
        label: str,
        currency: str,
    ) -> LedgerAccount:
        existing = self._ledger_account_repo.get_by_code(db, account_code)
        if existing:
            return existing
        return self._ledger_account_repo.create(
            db,
            data={
                "client_id": client_id,
                "account_type": account_type,
                "account_code": account_code,
                "label": label,
                "currency": currency,
                "metadata_": {},
            },
        )

    def create_client_account(
        self, db: Session, payload: AccountCreate, actor: ActorContext
    ) -> CustodyAccount:
        if payload.client_id is None:
            raise ValueError("client_id is required for client deposit accounts")

        existing = self._account_repo.find_client_account(db, payload.client_id, payload.currency)
        if existing:
            raise DuplicateAccountError(
                f"Client {payload.client_id} already has a {payload.currency} deposit account"
            )

        client = db.query(Client).filter(Client.id == payload.client_id).first()
        if client is None:
            raise ValueError(f"Client {payload.client_id} not found")

        ledger_account = self._create_ledger_account(
            db,
            client_id=payload.client_id,
            account_type="client",
            account_code=f"custody_fiat_{payload.client_id}_{payload.currency}",
            label=f"Custody Fiat {payload.currency} — {client.email}",
            currency=payload.currency,
        )

        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata") or {}
        data["account_type"] = CustodyAccountType.CLIENT_DEPOSIT.value
        data["is_master_account"] = False
        data["ledger_account_id"] = ledger_account.id
        account = self._account_repo.create(db, data=data)

        self._balance_repo.create(
            db,
            data={
                "account_id": account.id,
                "available_balance": Decimal("0"),
                "pending_balance": Decimal("0"),
                "currency": payload.currency,
            },
        )

        AuditService.log_success(
            db,
            entity_type="custody_account",
            entity_id=str(account.id),
            action="custody_client_account_created",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "account_id": str(account.id),
                "client_id": str(payload.client_id),
                "currency": payload.currency,
                "ledger_account_id": str(ledger_account.id),
            },
        )
        return account

    def create_settlement_account(
        self, db: Session, payload: AccountCreate, actor: ActorContext
    ) -> CustodyAccount:
        existing = self._account_repo.find_settlement_account(db, payload.currency)
        if existing:
            raise DuplicateAccountError(
                f"Settlement account for {payload.currency} already exists"
            )

        ledger_account = self._create_ledger_account(
            db,
            client_id=None,
            account_type="treasury",
            account_code=f"custody_treasury_{payload.currency}",
            label=f"Custody Treasury {payload.currency}",
            currency=payload.currency,
        )

        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata") or {}
        data["account_type"] = CustodyAccountType.COMPANY_SETTLEMENT.value
        data["is_master_account"] = True
        data["client_id"] = None
        data["ledger_account_id"] = ledger_account.id
        account = self._account_repo.create(db, data=data)

        self._balance_repo.create(
            db,
            data={
                "account_id": account.id,
                "available_balance": Decimal("0"),
                "pending_balance": Decimal("0"),
                "currency": payload.currency,
            },
        )

        AuditService.log_success(
            db,
            entity_type="custody_account",
            entity_id=str(account.id),
            action="custody_settlement_account_created",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "account_id": str(account.id),
                "currency": payload.currency,
                "ledger_account_id": str(ledger_account.id),
            },
        )
        return account

    def list_accounts(
        self,
        db: Session,
        *,
        account_type: str | None = None,
        client_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ):
        return self._account_repo.list(
            db, account_type=account_type, client_id=client_id, skip=skip, limit=limit
        )

    def list_clients_for_deposit_simulation(
        self,
        db: Session,
        *,
        currency: str,
        provider_id: Optional[UUID] = None,
    ) -> list[dict]:
        """Customers (PE Client) avec compte dépôt dans la devise.

        Filtre optionnel par fournisseur BAS pour aligner la simulation avec le provider choisi en UI.
        (Sans filtre : tous les comptes dépôt dans la devise.)
        """
        cur = (currency or "EUR").strip().upper()
        q = (
            db.query(CustodyAccount, Client)
            .join(Client, CustodyAccount.client_id == Client.id)
            .filter(
                CustodyAccount.account_type == CustodyAccountType.CLIENT_DEPOSIT.value,
                CustodyAccount.currency == cur,
                CustodyAccount.client_id.isnot(None),
            )
        )
        if provider_id is not None:
            q = q.filter(CustodyAccount.provider_id == provider_id)
        rows = q.order_by(Client.email.asc().nulls_last(), Client.id).all()
        seen: set[UUID] = set()
        out: list[dict] = []
        for acc, client in rows:
            if client.id in seen:
                continue
            seen.add(client.id)
            bal = CustodyBalanceRepository.get_by_account_id(db, acc.id)
            extra = enrichment_fields_for_pe_client(db, client)
            from_pe = (client.email or "").strip()
            from_person = (extra.get("person_email_collected") or "").strip()
            phone_hint = (extra.get("phone_e164") or "").strip()
            # Même logique que AccountRead : l’e-mail métier est souvent sur Person (collecté), pas sur pe_clients.
            email_for_api = from_pe or from_person
            holder_db = (acc.account_holder_name or "").strip() or "—"
            display_holder = holder_db if holder_db != "—" else "Client"
            if email_for_api:
                contact = email_for_api
            elif phone_hint:
                contact = phone_hint
            else:
                contact = ""
            if contact:
                label = f"{display_holder} — {contact}"
            else:
                label = f"{display_holder} — (no contact)"
            out.append(
                {
                    "client_id": client.id,
                    "email": email_for_api,
                    "iban": acc.iban,
                    "account_holder_name": holder_db,
                    "available_balance": bal.available_balance if bal else None,
                    "label": label,
                }
            )
        out.sort(key=lambda d: d["label"].lower())
        return out

    def list_balances(self, db: Session, *, skip: int = 0, limit: int = 50):
        return self._balance_repo.list(db, skip=skip, limit=limit)

    def list_transactions(
        self,
        db: Session,
        *,
        account_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        provider_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        return self._tx_repo.list(
            db,
            account_id=account_id,
            client_id=client_id,
            transaction_type=transaction_type,
            status=status,
            provider_id=provider_id,
            skip=skip,
            limit=limit,
        )

    def list_webhook_events(
        self,
        db: Session,
        *,
        provider_id: UUID | None = None,
        processing_status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ):
        return self._webhook_repo.list(
            db,
            provider_id=provider_id,
            processing_status=processing_status,
            skip=skip,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Simulations (hardened)
    # ------------------------------------------------------------------

    def simulate_deposit(
        self, db: Session, payload: SimulateDepositRequest, actor: ActorContext
    ) -> tuple[CustodyTransaction, CustodyAccountBalance]:
        client_account = self._account_repo.find_client_account(db, payload.client_id, payload.currency)
        if client_account is None:
            raise AccountNotFoundError(
                f"No active {payload.currency} deposit account for client {payload.client_id}"
            )

        settlement = self._account_repo.find_settlement_account(db, payload.currency)
        if settlement is None:
            raise SettlementAccountNotFoundError(
                f"No active {payload.currency} settlement account"
            )

        balance = self._balance_repo.get_for_update(db, client_account.id)

        client_ledger = None
        if client_account.ledger_account_id:
            client_ledger = db.query(LedgerAccount).filter(
                LedgerAccount.id == client_account.ledger_account_id
            ).first()

        self._validate_currency_chain(payload.currency, client_account, balance, client_ledger)

        tx = self._tx_repo.create(
            db,
            data={
                "account_id": client_account.id,
                "provider_id": client_account.provider_id,
                "transaction_type": TransactionType.DEPOSIT.value,
                "direction": TransactionDirection.CREDIT.value,
                "amount": payload.amount,
                "currency": payload.currency,
                "status": TransactionStatus.PENDING.value,
                "external_reference": payload.reference,
                "metadata_": {},
            },
        )

        validate_transition(tx.status, TransactionStatus.PROCESSING.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.PROCESSING.value)

        try:
            if client_account.ledger_account_id and settlement.ledger_account_id:
                self._ledger_entry_svc.post_double_entry(
                    db,
                    debit_account_id=client_account.ledger_account_id,
                    credit_account_id=settlement.ledger_account_id,
                    amount=payload.amount,
                    currency=payload.currency,
                    reference_type="custody_transaction",
                    reference_id=tx.id,
                    effective_at=datetime.now(timezone.utc),
                    description=f"Simulated deposit {payload.currency} {payload.amount}",
                    metadata={"simulation": True, "external_reference": payload.reference},
                )

            self._balance_repo.update_balance(db, balance, delta=payload.amount)

            validate_transition(tx.status, TransactionStatus.COMPLETED.value)
            self._tx_repo.update_status(db, tx, new_status=TransactionStatus.COMPLETED.value)
        except Exception as exc:
            validate_transition(tx.status, TransactionStatus.FAILED.value)
            self._tx_repo.update_status(
                db, tx,
                new_status=TransactionStatus.FAILED.value,
                failure_reason=str(exc),
            )
            raise

        AuditService.log_success(
            db,
            entity_type="custody_transaction",
            entity_id=str(tx.id),
            action="custody_deposit_simulated",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "transaction_id": str(tx.id),
                "client_id": str(payload.client_id),
                "amount": str(payload.amount),
                "currency": payload.currency,
                "new_balance": str(balance.available_balance),
            },
        )
        return tx, balance

    def simulate_withdrawal(
        self, db: Session, payload: SimulateWithdrawalRequest, actor: ActorContext
    ) -> tuple[CustodyTransaction, CustodyAccountBalance]:
        client_account = self._account_repo.find_client_account(db, payload.client_id, payload.currency)
        if client_account is None:
            raise AccountNotFoundError(
                f"No active {payload.currency} deposit account for client {payload.client_id}"
            )

        settlement = self._account_repo.find_settlement_account(db, payload.currency)
        if settlement is None:
            raise SettlementAccountNotFoundError(
                f"No active {payload.currency} settlement account"
            )

        balance = self._balance_repo.get_for_update(db, client_account.id)
        current_balance = Decimal(str(balance.available_balance))
        if current_balance < payload.amount:
            raise InsufficientFundsError(
                f"Insufficient funds: available={current_balance}, requested={payload.amount}"
            )

        client_ledger = None
        if client_account.ledger_account_id:
            client_ledger = db.query(LedgerAccount).filter(
                LedgerAccount.id == client_account.ledger_account_id
            ).first()

        self._validate_currency_chain(payload.currency, client_account, balance, client_ledger)

        tx = self._tx_repo.create(
            db,
            data={
                "account_id": client_account.id,
                "provider_id": client_account.provider_id,
                "transaction_type": TransactionType.WITHDRAWAL.value,
                "direction": TransactionDirection.DEBIT.value,
                "amount": payload.amount,
                "currency": payload.currency,
                "status": TransactionStatus.PENDING.value,
                "external_reference": payload.reference,
                "metadata_": {},
            },
        )

        validate_transition(tx.status, TransactionStatus.PROCESSING.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.PROCESSING.value)

        try:
            if client_account.ledger_account_id and settlement.ledger_account_id:
                self._ledger_entry_svc.post_double_entry(
                    db,
                    debit_account_id=settlement.ledger_account_id,
                    credit_account_id=client_account.ledger_account_id,
                    amount=payload.amount,
                    currency=payload.currency,
                    reference_type="custody_transaction",
                    reference_id=tx.id,
                    effective_at=datetime.now(timezone.utc),
                    description=f"Simulated withdrawal {payload.currency} {payload.amount}",
                    metadata={"simulation": True, "external_reference": payload.reference},
                )

            self._balance_repo.update_balance(db, balance, delta=-payload.amount)

            validate_transition(tx.status, TransactionStatus.COMPLETED.value)
            self._tx_repo.update_status(db, tx, new_status=TransactionStatus.COMPLETED.value)
        except Exception as exc:
            validate_transition(tx.status, TransactionStatus.FAILED.value)
            self._tx_repo.update_status(
                db, tx,
                new_status=TransactionStatus.FAILED.value,
                failure_reason=str(exc),
            )
            raise

        AuditService.log_success(
            db,
            entity_type="custody_transaction",
            entity_id=str(tx.id),
            action="custody_withdrawal_simulated",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "transaction_id": str(tx.id),
                "client_id": str(payload.client_id),
                "amount": str(payload.amount),
                "currency": payload.currency,
                "new_balance": str(balance.available_balance),
            },
        )
        return tx, balance

    # ------------------------------------------------------------------
    # Internal Transfer (client → settlement)
    # ------------------------------------------------------------------

    def execute_internal_transfer(
        self,
        db: Session,
        payload: InternalTransferRequest,
        actor: ActorContext,
    ) -> dict:
        """Transfer funds from a client EUR account to the company settlement account.

        Returns a dict matching InternalTransferResponse fields.
        Raises on validation errors; returns status=ignored for duplicates.
        """
        # --- Step 0: idempotency check ---
        existing = self._tx_repo.find_by_external_reference(db, payload.external_reference)
        if existing:
            return {
                "status": "ignored",
                "reason": "duplicate_external_reference",
                "transaction_id": existing.id,
            }

        # --- Step 1: validate accounts ---
        client_account = self._account_repo.get_by_id(db, payload.client_account_id)
        if client_account is None or client_account.status != "active":
            raise AccountNotFoundError("client_account_not_found")

        settlement = self._account_repo.get_by_id(db, payload.settlement_account_id)
        if settlement is None or settlement.status != "active":
            raise SettlementAccountNotFoundError("settlement_account_not_found")

        if client_account.account_type != CustodyAccountType.CLIENT_DEPOSIT.value:
            raise InvalidTransferError("transfer_route_not_allowed: source must be a client_deposit_account")
        if client_account.client_id is None:
            raise InvalidTransferError("transfer_route_not_allowed: source account has no client_id")

        if settlement.account_type != CustodyAccountType.COMPANY_SETTLEMENT.value:
            raise InvalidTransferError("invalid_settlement_account: destination must be a company_settlement_account")
        if not settlement.is_master_account:
            raise InvalidTransferError("invalid_settlement_account: destination must be a master settlement account")
        if settlement.client_id is not None:
            raise InvalidTransferError("invalid_settlement_account: settlement account must not be linked to a client")

        if client_account.id == settlement.id:
            raise InvalidTransferError("transfer_route_not_allowed: source and destination must be different accounts")

        # --- Step 2: currency validation ---
        if client_account.currency != payload.currency:
            raise CurrencyMismatchError(
                f"currency_not_supported: client account is {client_account.currency}, requested {payload.currency}"
            )
        if settlement.currency != payload.currency:
            raise CurrencyMismatchError(
                f"currency_not_supported: settlement account is {settlement.currency}, requested {payload.currency}"
            )

        # --- Step 3: balance check with row-level lock ---
        client_balance = self._balance_repo.get_for_update(db, client_account.id)
        if client_balance is None:
            raise AccountNotFoundError("client balance not found")

        settlement_balance = self._balance_repo.get_for_update(db, settlement.id)
        if settlement_balance is None:
            raise SettlementAccountNotFoundError("settlement balance not found")

        self._validate_currency_chain(payload.currency, client_account, client_balance)
        self._validate_currency_chain(payload.currency, settlement, settlement_balance)

        current_client = Decimal(str(client_balance.available_balance))
        if current_client < payload.amount:
            raise InsufficientFundsError(
                f"insufficient_funds: available={current_client}, requested={payload.amount}"
            )

        # --- Step 4: create transaction (pending → processing) ---
        tx = self._tx_repo.create(
            db,
            data={
                "account_id": client_account.id,
                "provider_id": None,
                "transaction_type": TransactionType.TRANSFER_INTERNAL.value,
                "transaction_kind": "internal_transfer",
                "direction": TransactionDirection.DEBIT.value,
                "amount": payload.amount,
                "currency": payload.currency,
                "status": TransactionStatus.PENDING.value,
                "external_reference": payload.external_reference,
                "metadata_": {
                    "settlement_account_id": str(settlement.id),
                    "client_id": str(client_account.client_id),
                    "operation": "crypto_buy_pre_funding",
                },
            },
        )

        validate_transition(tx.status, TransactionStatus.PROCESSING.value)
        self._tx_repo.update_status(db, tx, new_status=TransactionStatus.PROCESSING.value)

        # --- Step 5: ledger double entry + balance updates ---
        try:
            if client_account.ledger_account_id and settlement.ledger_account_id:
                self._ledger_entry_svc.post_double_entry(
                    db,
                    debit_account_id=client_account.ledger_account_id,
                    credit_account_id=settlement.ledger_account_id,
                    amount=payload.amount,
                    currency=payload.currency,
                    reference_type="custody_transaction",
                    reference_id=tx.id,
                    effective_at=datetime.now(timezone.utc),
                    description=f"Internal transfer {payload.currency} {payload.amount} — client→settlement",
                    metadata={
                        "external_reference": payload.external_reference,
                        "client_id": str(client_account.client_id),
                    },
                )

            self._balance_repo.update_balance(db, client_balance, delta=-payload.amount)
            self._balance_repo.update_balance(db, settlement_balance, delta=payload.amount)

            # --- Step 6: finalize ---
            validate_transition(tx.status, TransactionStatus.COMPLETED.value)
            self._tx_repo.update_status(db, tx, new_status=TransactionStatus.COMPLETED.value)

        except Exception as exc:
            logger.error("Internal transfer failed: %s", exc, exc_info=True)
            validate_transition(tx.status, TransactionStatus.FAILED.value)
            self._tx_repo.update_status(
                db, tx,
                new_status=TransactionStatus.FAILED.value,
                failure_reason=str(exc),
            )
            raise

        AuditService.log_success(
            db,
            entity_type="custody_transaction",
            entity_id=str(tx.id),
            action="internal_transfer_completed",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "transaction_id": str(tx.id),
                "client_account_id": str(client_account.id),
                "settlement_account_id": str(settlement.id),
                "amount": str(payload.amount),
                "currency": payload.currency,
                "client_balance_after": str(client_balance.available_balance),
                "settlement_balance_after": str(settlement_balance.available_balance),
            },
        )

        return {
            "status": "completed",
            "transaction_id": tx.id,
            "amount": payload.amount,
            "currency": payload.currency,
            "client_balance_after": client_balance.available_balance,
            "settlement_balance_after": settlement_balance.available_balance,
        }

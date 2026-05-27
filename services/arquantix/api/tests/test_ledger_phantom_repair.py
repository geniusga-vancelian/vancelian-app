"""Tests repair crédits phantom ledger Privy."""
from decimal import Decimal
from uuid import uuid4

from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.privy_wallet.enums import PersonWalletDepositStatus
from services.privy_wallet.ledger_phantom_repair import (
    list_phantom_confirmed_deposits,
    void_phantom_confirmed_deposits,
)
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletBalanceRepository
from tests.conftest import make_linked_client


def test_list_phantom_sim_deposit(db_session):
    pe = make_linked_client(db_session)
    wallet = upsert_person_crypto_wallet(
        db_session,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid4().hex[:40]}",
    )
    db_session.flush()

    deposit = PersonWalletDeposit(
        id=uuid4(),
        person_crypto_wallet_id=wallet.id,
        person_id=pe.person_id,
        transaction_kind="privy_deposit_in",
        direction="credit",
        asset="USDC",
        amount=Decimal("15"),
        chain_type="evm",
        chain_id=8453,
        tx_hash="0xsimdeadbeef",
        log_index=0,
        to_address=wallet.address,
        status=PersonWalletDepositStatus.CONFIRMED.value,
        title="Simulated",
    )
    db_session.add(deposit)
    balance_repo = PersonWalletBalanceRepository()
    row = balance_repo.get_or_create_for_update(
        db_session,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    balance_repo.increment_balance(db_session, row, delta=Decimal("15"))
    db_session.commit()

    phantoms = list_phantom_confirmed_deposits(db_session, person_id=pe.person_id)
    assert len(phantoms) == 1
    assert phantoms[0].reason == "simulated_tx_hash"

    actions = void_phantom_confirmed_deposits(db_session, person_id=pe.person_id, dry_run=True)
    assert actions[0]["action"] == "would_void"

    void_phantom_confirmed_deposits(db_session, person_id=pe.person_id, dry_run=False)
    db_session.commit()

    phantoms_after = list_phantom_confirmed_deposits(db_session, person_id=pe.person_id)
    assert phantoms_after == []

    refreshed = balance_repo.get_or_create_for_update(
        db_session,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    assert Decimal(str(refreshed.balance)) == Decimal("0")

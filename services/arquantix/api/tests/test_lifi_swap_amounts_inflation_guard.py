"""Garde-fou cost basis — ledger LINK gonflé vs devis LI.FI."""
from decimal import Decimal
from uuid import uuid4

from services.cost_basis.lifi_swap_amounts import amount_out_from_ledger


class _FakeSwap:
    def __init__(self) -> None:
        self.id = uuid4()
        self.person_id = uuid4()
        self.to_asset = "LINK"


class _FakeDeposit:
    def __init__(self, *, swap, amount: str, estimated: str) -> None:
        self.person_id = swap.person_id
        self.asset = "LINK"
        self.direction = "credit"
        self.transaction_kind = "crypto_swap"
        self.amount = amount
        self.metadata_json = {
            "swap_id": str(swap.id),
            "swap_amount_to": amount,
            "swap_amount_to_estimated": estimated,
        }
        self.confirmed_at = None
        self.created_at = None


class _FakeQuery:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def query(self, model):
        return _FakeQuery(self._rows)


def test_amount_out_from_ledger_prefers_estimated_when_inflated():
    swap = _FakeSwap()
    deposit = _FakeDeposit(
        swap=swap,
        amount="1488558716",
        estimated="0.1488558716",
    )

    db = _FakeDb([deposit])
    amount, src = amount_out_from_ledger(db, swap)
    assert amount == Decimal("0.1488558716")
    assert "inflation_guard" in src

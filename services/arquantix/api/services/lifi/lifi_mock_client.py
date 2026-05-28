"""Client LI.FI mock — environnement local / test sans appel réseau ni signature Privy."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Union

from config.supported_swap_assets import (
    SUPPORTED_SWAP_CHAINS,
    atomic_amount_to_human,
    human_amount_to_atomic,
    resolve_swap_token,
)
from services.lifi.lifi_mock_pricing import estimate_mock_swap_output


def _chain_key_from_lifi_id(chain_id: Union[int, str]) -> str:
    for key, meta in SUPPORTED_SWAP_CHAINS.items():
        if meta.get("lifi_chain_id") == chain_id:
            return key
    return "ethereum"


class LifiMockClient:
    """Quote + status simulés — aligné sur le contrat ``LifiClient``."""

    def get_quote(
        self,
        *,
        from_chain: Union[int, str],
        to_chain: Union[int, str],
        from_token: str,
        to_token: str,
        from_amount: str,
        from_address: str,
        to_address: str | None = None,
        slippage: float | None = None,
        fee_bps: int | None = None,
    ) -> dict[str, Any]:
        del from_address, to_address, slippage, fee_bps
        from_key = _chain_key_from_lifi_id(from_chain)
        to_key = _chain_key_from_lifi_id(to_chain)
        from_meta = resolve_swap_token(_token_symbol_from_address(from_token, from_key), from_key)
        to_meta = resolve_swap_token(_token_symbol_from_address(to_token, to_key), to_key)

        amount_in = atomic_amount_to_human(from_amount, from_meta.decimals)
        estimated_out = estimate_mock_swap_output(
            from_asset=from_meta.asset,
            to_asset=to_meta.asset,
            amount_in=amount_in,
        )
        if estimated_out <= 0:
            estimated_out = Decimal("0.00000001")

        min_out = (estimated_out * Decimal("0.995")).quantize(Decimal("0.00000001"))
        to_amount_atomic = human_amount_to_atomic(estimated_out, to_meta.decimals)
        to_min_atomic = human_amount_to_atomic(min_out, to_meta.decimals)

        from_chain_id = int(SUPPORTED_SWAP_CHAINS[from_key]["lifi_chain_id"])
        to_chain_id = int(SUPPORTED_SWAP_CHAINS[to_key]["lifi_chain_id"])

        return {
            "id": f"mock-quote-{uuid.uuid4().hex[:12]}",
            "tool": "mock-swap-v1",
            "action": {"fromChainId": from_chain_id, "toChainId": to_chain_id},
            "estimate": {
                "toAmount": to_amount_atomic,
                "toAmountMin": to_min_atomic,
                "executionDuration": 3,
                "feeCosts": [
                    {
                        "name": "Mock network",
                        "included": False,
                        "amount": "10000",
                        "amountUSD": "0.01",
                        "token": {"symbol": from_meta.asset, "decimals": from_meta.decimals},
                    }
                ],
                "gasCosts": [
                    {
                        "type": "SEND",
                        "amount": "5000000000000000",
                        "amountUSD": "0.02",
                        "token": {"symbol": "ETH", "decimals": 18},
                    }
                ],
            },
            "transactionRequest": {
                "to": "0x0000000000000000000000000000000000000001",
                "data": "0x",
                "value": "0",
                "chainId": from_chain_id,
                "gasLimit": "21000",
            },
        }

    def get_status(self, *, tx_hash: str, bridge: str | None = None) -> dict[str, Any]:
        del bridge
        if (tx_hash or "").startswith("0xmock"):
            return {"status": "DONE", "substatus": "COMPLETED", "substatusMessage": "Mock swap settled"}
        return {"status": "PENDING", "substatus": "WAIT_SOURCE_CONFIRMATIONS"}


def _token_symbol_from_address(token_address: str, chain_key: str) -> str:
    addr = (token_address or "").strip().lower()
    if addr in {"", "0x0000000000000000000000000000000000000000", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"}:
        return "ETH"
    from config.supported_swap_assets import SUPPORTED_SWAP_ASSETS

    for symbol, meta in SUPPORTED_SWAP_ASSETS.items():
        addresses = meta.get("addresses") or {}
        mapped = addresses.get(chain_key)
        if mapped and str(mapped).lower() == addr:
            return symbol
    return "USDC"

"""Client HTTP LI.FI — backend uniquement."""
from __future__ import annotations

import logging
from typing import Any, Union

import httpx

from services.lifi.config import lifi_base_url, lifi_quote_base_params, lifi_request_headers

logger = logging.getLogger(__name__)


class LifiClientError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int | None = None):
        self.code = code
        self.http_status = http_status
        super().__init__(message)


class LifiClient:
    def __init__(self, *, timeout_seconds: float = 20.0):
        self._timeout = timeout_seconds

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
        params = lifi_quote_base_params(
            fromChain=from_chain,
            toChain=to_chain,
            fromToken=from_token,
            toToken=to_token,
            fromAmount=from_amount,
            fromAddress=from_address,
        )
        if to_address:
            params["toAddress"] = to_address
        if slippage is not None:
            params["slippage"] = slippage
        if fee_bps is not None and fee_bps > 0:
            params["fee"] = fee_bps / 10_000

        url = f"{lifi_base_url()}/quote"
        headers = lifi_request_headers()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=params, headers=headers)
        except httpx.RequestError as exc:
            logger.warning("lifi.quote.network_error", extra={"error": str(exc)})
            raise LifiClientError("lifi.network_error", "LI.FI indisponible") from exc

        if response.status_code >= 400:
            detail = _safe_error_body(response)
            logger.warning(
                "lifi.quote.http_error",
                extra={"status": response.status_code, "detail": detail[:500]},
            )
            raise LifiClientError(
                "lifi.quote_failed",
                detail or "Quote LI.FI refusée",
                http_status=response.status_code,
            )

        payload = response.json()
        logger.info(
            "lifi.quote.success",
            extra={
                "tool": payload.get("tool"),
                "from_chain": from_chain,
                "to_chain": to_chain,
            },
        )
        return payload

    def get_status(self, *, tx_hash: str, bridge: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"txHash": tx_hash}
        if bridge:
            params["bridge"] = bridge
        url = f"{lifi_base_url()}/status"
        headers = lifi_request_headers()
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(url, params=params, headers=headers)
        if response.status_code >= 400:
            raise LifiClientError(
                "lifi.status_failed",
                _safe_error_body(response) or "Status LI.FI indisponible",
                http_status=response.status_code,
            )
        return response.json()


def _safe_error_body(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("message") or body.get("error") or body)
        return str(body)
    except Exception:
        return (response.text or "").strip()

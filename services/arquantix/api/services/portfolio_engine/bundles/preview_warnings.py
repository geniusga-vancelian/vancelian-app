"""Structured bundle invest preview warnings (machine-parseable + UI-friendly)."""
from __future__ import annotations

from urllib.parse import quote, unquote


def _encode_field(value: str) -> str:
    return quote((value or "").strip(), safe="")


def _decode_field(value: str) -> str:
    return unquote((value or "").strip())


def build_lifi_preview_warning(
    *,
    asset: str,
    display: str,
    code: str,
    detail: str,
) -> str:
    return (
        "lifi_preview_failed"
        f"|asset={_encode_field(asset)}"
        f"|display={_encode_field(display)}"
        f"|code={_encode_field(code)}"
        f"|detail={_encode_field(detail)}"
    )


def build_lifi_preview_warning_from_exc(
    *,
    asset: str,
    display: str,
    exc: Exception,
) -> str:
    code = getattr(exc, "code", None) or "bundle.lifi.unknown"
    detail = str(exc).strip() or "Erreur inconnue"
    return build_lifi_preview_warning(
        asset=asset,
        display=display,
        code=str(code),
        detail=detail,
    )


def build_exchange_preview_warning(
    *,
    asset: str,
    display: str,
    detail: str,
) -> str:
    return (
        "exchange_preview_failed"
        f"|asset={_encode_field(asset)}"
        f"|display={_encode_field(display)}"
        f"|code={_encode_field('exchange.preview_failed')}"
        f"|detail={_encode_field(detail)}"
    )


def parse_preview_warning(raw: str) -> dict[str, str]:
    """Parse ``kind|key=value|…`` warnings; returns at least ``kind`` and ``detail``."""
    text = (raw or "").strip()
    if not text:
        return {"kind": "unknown", "detail": ""}
    parts = text.split("|")
    out: dict[str, str] = {"kind": parts[0]}
    for segment in parts[1:]:
        if "=" not in segment:
            continue
        key, _, value = segment.partition("=")
        out[key.strip()] = _decode_field(value)
    return out

"""Configuration LI.FI (swaps cross-chain / DEX aggregator) — backend uniquement."""
from __future__ import annotations

import os
from typing import Any

DEFAULT_LIFI_BASE_URL = "https://li.quest/v1"

# Valeurs par défaut alignées sur le portail LI.FI (intégration vancelian.finance).
DEFAULT_LIFI_INTEGRATOR_ID = "vancelian.finance"
DEFAULT_LIFI_INTEGRATION_URL = "https://app.vancelian.finance/"
DEFAULT_LIFI_FEE_BPS = 25
DEFAULT_LIFI_RPM_LIMIT = 100

# Fees Vancelian (affichés au client, distincts des fees LI.FI integrator).
DEFAULT_SWAP_FEE_BPS = 0
DEFAULT_SLIPPAGE_BPS = 50
MAX_SLIPPAGE_BPS = 100
QUOTE_TTL_SECONDS = 120

# Pilote V1 — swaps same-chain (pas de bridge cross-chain entre réseaux navbar).
DEFAULT_SWAP_V1_SAME_CHAIN_ONLY = True
DEFAULT_SWAP_V1_PILOT_CHAINS = "base"

# Mock local — pas d'appel LI.FI ni signature Privy (règlement ledger interne).
DEFAULT_LIFI_SWAPS_MOCK = False

# Phase 2 S2a — intent orchestrateur (défaut OFF : legacy Phase 7 inchangé).
DEFAULT_LIFI_INTENT_ORCHESTRATOR_ENABLED = False
DEFAULT_LIFI_OUTBOX_WORKER_ENABLED = False

# Alias rétrocompat.
LIFI_API_BASE_URL = DEFAULT_LIFI_BASE_URL


def swap_v1_same_chain_only() -> bool:
    raw = (os.getenv("SWAP_V1_SAME_CHAIN_ONLY") or str(DEFAULT_SWAP_V1_SAME_CHAIN_ONLY)).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def swap_v1_pilot_chains() -> frozenset[str]:
    raw = (os.getenv("SWAP_V1_PILOT_CHAINS") or DEFAULT_SWAP_V1_PILOT_CHAINS).strip()
    keys = frozenset(part.strip().lower() for part in raw.split(",") if part.strip())
    return keys or frozenset({"base"})


def swaps_mock_mode() -> bool:
    raw = (os.getenv("LIFI_SWAPS_MOCK") or str(DEFAULT_LIFI_SWAPS_MOCK)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def build_lifi_client():
    """Client LI.FI réel ou mock selon ``LIFI_SWAPS_MOCK``."""
    if swaps_mock_mode():
        from services.lifi.lifi_mock_client import LifiMockClient

        return LifiMockClient()
    from services.lifi.lifi_client import LifiClient

    return LifiClient()


def lifi_base_url() -> str:
    return (os.getenv("LIFI_BASE_URL") or DEFAULT_LIFI_BASE_URL).strip().rstrip("/")


def lifi_api_key() -> str:
    return (os.getenv("LIFI_API_KEY") or "").strip()


def swap_fee_bps() -> int:
    raw = (os.getenv("SWAP_FEE_BPS") or str(DEFAULT_SWAP_FEE_BPS)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_SWAP_FEE_BPS


def default_slippage_bps() -> int:
    raw = (os.getenv("DEFAULT_SLIPPAGE_BPS") or str(DEFAULT_SLIPPAGE_BPS)).strip()
    try:
        return max(1, min(MAX_SLIPPAGE_BPS, int(raw)))
    except ValueError:
        return DEFAULT_SLIPPAGE_BPS


def swaps_enabled() -> bool:
    flag = (os.getenv("LIFI_SWAPS_ENABLED") or "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def lifi_intent_orchestrator_enabled() -> bool:
    """Phase 2 S2a — quote crée intent orchestrateur + outbox (défaut false)."""
    raw = (
        os.getenv("LIFI_INTENT_ORCHESTRATOR_ENABLED")
        or str(DEFAULT_LIFI_INTENT_ORCHESTRATOR_ENABLED)
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def lifi_outbox_worker_enabled() -> bool:
    """Phase 2 S2a+ — poll outbox intent.created (défaut false, hors scope runtime S2a)."""
    raw = (
        os.getenv("LIFI_OUTBOX_WORKER_ENABLED") or str(DEFAULT_LIFI_OUTBOX_WORKER_ENABLED)
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def lifi_integrator_id() -> str:
    return (os.getenv("LIFI_INTEGRATOR_ID") or DEFAULT_LIFI_INTEGRATOR_ID).strip()


def lifi_integration_url() -> str:
    return (os.getenv("LIFI_INTEGRATION_URL") or DEFAULT_LIFI_INTEGRATION_URL).strip()


def lifi_fee_bps() -> int:
    raw = (os.getenv("LIFI_FEE_BPS") or str(DEFAULT_LIFI_FEE_BPS)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_LIFI_FEE_BPS


def lifi_rpm_limit() -> int:
    raw = (os.getenv("LIFI_RPM_LIMIT") or str(DEFAULT_LIFI_RPM_LIMIT)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LIFI_RPM_LIMIT


def lifi_api_configured() -> bool:
    return bool(lifi_api_key())


def lifi_request_headers() -> dict[str, str]:
    """En-têtes serveur → LI.FI (clé API jamais côté front)."""
    headers = {"Accept": "application/json"}
    key = lifi_api_key()
    if key:
        headers["x-lifi-api-key"] = key
    return headers


def lifi_quote_base_params(**overrides: Any) -> dict[str, Any]:
    """Paramètres communs quote LI.FI (integrator requis pour analytics / fees)."""
    params: dict[str, Any] = {"integrator": lifi_integrator_id()}
    params.update(overrides)
    return params

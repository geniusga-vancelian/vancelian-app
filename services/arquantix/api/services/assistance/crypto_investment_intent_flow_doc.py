"""Chargement du document de flow versionné — ``crypto_investment_intent`` V1.

Le JSON vit sous ``services/assistance/flow_json/`` pour éviter tout conflit avec
``services/assistance/config.py`` (module plat existant)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

_JSON_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "flow_json" / "crypto_investment_intent.v1.json"
)


class ExecutionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_can_execute_order: bool = False
    supports_native_deep_links_in_v1: bool = False


class CryptoInvestmentIntentFlowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: str
    version: str
    action_type: str = "crypto_investment_intent"
    enabled: bool = True
    required_slots: list[str] = Field(default_factory=list)
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    runtime_sources: list[str] = Field(default_factory=list)
    anti_hallucination_rules: list[str] = Field(default_factory=list)
    slot_provenance: dict[str, Any] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def load_crypto_investment_intent_flow_v1() -> CryptoInvestmentIntentFlowV1:
    raw = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    return CryptoInvestmentIntentFlowV1.model_validate(raw)


__all__ = [
    "CryptoInvestmentIntentFlowV1",
    "ExecutionPolicy",
    "load_crypto_investment_intent_flow_v1",
]

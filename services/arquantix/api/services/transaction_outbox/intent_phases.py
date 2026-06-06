"""Phases orchestrateur intent (ADR 001) — champs ``current_phase`` uniquement en S2b."""
from __future__ import annotations

from enum import Enum


class IntentOrchestratorPhase(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"

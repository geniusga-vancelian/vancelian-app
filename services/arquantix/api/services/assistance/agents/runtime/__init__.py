"""Runtime du loop agentique (Phase 2a).

Cf. `docs/arquantix/MULTI_AGENTS_RUNTIME.md` pour la spec complète.

Symboles publics :

  - `run_agent_loop`      : async generator central, point d'entrée du
                            runtime. Yield des `AgentEvent`.
  - `RuntimeError` (alias): exception métier remontée si un cas
                            inattendu impose un abort (rare — la plupart
                            des erreurs deviennent un `AgentEvent.error`).
"""

from __future__ import annotations

from services.assistance.agents.runtime import tour_shared_context
from services.assistance.agents.runtime.agent_loop import (
    MAX_ITER_FALLBACK_MESSAGE,
    run_agent_loop,
)

__all__ = [
    "run_agent_loop",
    "MAX_ITER_FALLBACK_MESSAGE",
    "tour_shared_context",
]

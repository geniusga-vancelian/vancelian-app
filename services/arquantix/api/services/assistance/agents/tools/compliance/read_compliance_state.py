"""Tool ``read_compliance_state`` — agent **compliance**, autonomy **L0**.

Snapshot **introspectif** et **safe** de l'état compliance d'un client.
À appeler en **premier** par l'agent compliance avant tout raisonnement.

Cf. `MULTI_AGENTS_RUNTIME.md` § 2.2.

──────────────────────────────────────────────────────────────────────
Garanties anti-tipping-off
──────────────────────────────────────────────────────────────────────

  - Le payload de retour ne contient **aucun** signal interne brut
    (`risk_score`, `level`, `deny_reason`, watchlist match, etc.).
  - Tous les signaux sensibles sont filtrés en amont par
    `compliance_repo.fetch_safe_signals` (cf. § 5.2).
  - L'`actor_kind` est exposé pour permettre à l'agent de s'adapter
    (CUSTOMER vs ONBOARDING) sans deviner.

──────────────────────────────────────────────────────────────────────
Conventions de retour
──────────────────────────────────────────────────────────────────────

```
{
  "actor_kind": "customer" | "onboarding" | "admin_bo" | "suspended",
  "client": {
      "client_status":  str | null,
      "kyc_status":     str | null,
      "account_state":  str | null,
      "login_frozen":   bool | null,
  },
  "safe_signals": {
      "requires_doc_upload":   bool,
      "requires_step_up":      bool,
      "client_facing_message": str | null,
  },
}
```

Si le client est introuvable (cas onboarding pur), tous les champs
`client.*` sont `None` et `safe_signals` reste neutre. L'agent doit
alors se rabattre sur les autres tools (`read_registration_progress`).
"""

from __future__ import annotations

import logging
from typing import Any

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "read_compliance_state",
        "description": (
            "Retourne un snapshot complet et safe de l'état compliance "
            "du client courant : statut KYC public, état de compte, "
            "et signaux compliance neutralisés (gated). À appeler en "
            "premier avant tout raisonnement compliance. Idempotent. "
            "Aucun argument requis."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance",
}


def execute(ctx: ToolContext, **_kwargs: Any) -> dict[str, Any]:
    """Lit l'état compliance via le repo introspectif. Best-effort.

    En cas de client_id manquant (ONBOARDING / ADMIN_BO), retourne un
    payload partiel mais valide (jamais d'exception).
    """
    actor_kind = ctx.actor_kind.value if ctx.actor_kind else None
    client_id = ctx.client_id

    if not client_id:
        # Cas ONBOARDING / pré-pe_clients : on ne peut pas lire le repo
        # client. L'agent saura raisonner via les tools registration.
        return {
            "actor_kind": actor_kind,
            "client": {
                "client_status": None,
                "kyc_status": None,
                "account_state": None,
                "login_frozen": None,
            },
            "safe_signals": {
                "requires_doc_upload": False,
                "requires_step_up": False,
                "client_facing_message": None,
            },
        }

    try:
        snapshot = compliance_repo.fetch_compliance_state_snapshot(
            ctx.db, client_id=client_id
        )
    except Exception:  # noqa: BLE001 — best-effort, jamais propager.
        logger.exception(
            "read_compliance_state.repo_error agent=%s conv=%s client_id=%s",
            ctx.agent_id,
            ctx.conversation_id,
            client_id,
        )
        return {
            "actor_kind": actor_kind,
            "client": {
                "client_status": None,
                "kyc_status": None,
                "account_state": None,
                "login_frozen": None,
            },
            "safe_signals": {
                "requires_doc_upload": False,
                "requires_step_up": False,
                "client_facing_message": None,
            },
            "error": "repo_unavailable",
        }

    return {
        "actor_kind": actor_kind,
        "client": snapshot.get("status") or {},
        "safe_signals": snapshot.get("safe_signals") or {},
    }

"""Tool transverse `handoff_to_agent` — Phase 2c.

Permet à un sub-agent de **transférer définitivement** la suite du
tour client à un autre sub-agent. Cas d'usage canonique :

  - `compliance.remediation` enquête sur les signaux AML / docs
  - aucun signal bloquant détecté → handoff vers
    `compliance.transactional` qui répond à la vraie question
    transactionnelle initiale du client

Contrairement à :py:mod:`consult_specialist`, qui appelle un
sous-runtime et **revient** avec du texte, le `handoff` ne revient
pas : le runtime switche `agent_id`, recharge prompt + tools, et
laisse le target sub-agent **terminer le tour** (texte, ask, etc.).

──────────────────────────────────────────────────────────────────────
Pattern interrupt-based — comme `diagnose_compliance_topic`

Le tool valide les arguments et retourne un payload signal :

    {
      "interrupt_with_handoff": True,
      "target_agent": "compliance.transactional",
      "reason":       "no_compliance_signal_detected",
    }

Le runtime intercepte ce signal :
  1. Vérifie les **autorisations de chaîne** (whitelist
     `_ALLOWED_HANDOFFS`).
  2. Vérifie les **préconditions d'investigation** (au moins
     `_MIN_INVESTIGATION_TOOLS_FOR_HANDOFF` tools L0 read appelés
     en amont par le caller).
  3. Switch `current_agent_id` vers `target_agent`.
  4. Recharge prompt + toolset.
  5. Continue la boucle (le target produit la réponse finale).

──────────────────────────────────────────────────────────────────────
Garde-fous

  - **Max 1 handoff par tour client.**
  - **Pas de cycles** : `compliance.transactional → handoff → compliance.remediation`
    est interdit (one-way de remediation vers fonctionnel uniquement).
  - **Pas de handoff** depuis un specialist consulté (`consult_in_progress=True`).
  - **Investigation requise** : `compliance.remediation` doit avoir
    appelé au moins 2 tools de lecture compliance avant de pouvoir
    handoff (sinon le handoff serait un bypass paresseux du filtre
    AML).

Cf. `docs/arquantix/MULTI_AGENTS.md` § 2.5 et `COMPLIANCE_TOPICS.md` § 7.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Whitelist de transitions autorisées
# ─────────────────────────────────────────────────────────────────────


# Pour chaque caller, l'ensemble de targets autorisés.
# *La validation finale est effectuée côté runtime* (le tool ne fait
# que valider la forme — la cohérence chaîne est globale).
_ALLOWED_HANDOFFS: dict[str, frozenset[str]] = {
    # remediation peut handoff vers tx ou general (filtre AML passé)
    "compliance.remediation": frozenset({
        "compliance.transactional",
        "compliance.general",
    }),
    # registration peut handoff vers general si question hors scope
    # onboarding (rare). PAS vers transactional (pas de TX en KYC pending).
    "compliance.registration": frozenset({"compliance.general"}),
    # general peut handoff vers les autres compliance si une
    # spécialisation devient évidente (rare, fail-safe).
    "compliance.general": frozenset({
        "compliance.remediation",
        "compliance.transactional",
    }),
    # transactional ne peut PAS handoff (terminal côté chaîne).
    # Il consulte product en consult_specialist si besoin.
}


# Minimum de tools de lecture compliance à avoir appelés AVANT un
# handoff depuis remediation. Le but : empêcher le LLM de bypass
# l'investigation par paresse.
_MIN_INVESTIGATION_TOOLS_FOR_HANDOFF = 2

# Tools comptés comme « investigation compliance » (read-only L0).
_INVESTIGATION_TOOLS = frozenset({
    "read_documents",
    "read_external_aml_signals",
    "read_compliance_state",
    "read_transactions",
    "read_registration_progress",
})


# ─────────────────────────────────────────────────────────────────────
# Tool spec
# ─────────────────────────────────────────────────────────────────────


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "handoff_to_agent",
        "description": (
            "Transfère définitivement la suite de ce tour à un autre "
            "sub-agent. À utiliser quand tu as terminé ton rôle de "
            "filtre / spécialiste et qu'un autre sub-agent est "
            "mieux placé pour produire la réponse finale au client. "
            "Convention : un seul handoff par tour ; après handoff, "
            "le target produit le texte/CTA final. ATTENTION : "
            "interrompt ta boucle — appelle ce tool en dernier. "
            "Cibles autorisées limitées (cf. liste ci-dessous)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "description": (
                        "ID du sub-agent cible. Cibles autorisées : "
                        "depuis `compliance.remediation` → "
                        "`compliance.transactional` ou "
                        "`compliance.general`. Depuis "
                        "`compliance.registration` → "
                        "`compliance.general`."
                    ),
                    "enum": [
                        "compliance.transactional",
                        "compliance.remediation",
                        "compliance.general",
                    ],
                    "maxLength": 64,
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Brève raison machine-friendly (ex. "
                        "'no_compliance_signal_detected', "
                        "'tx_question_outside_scope'). Pas de "
                        "justification client-facing ici."
                    ),
                    "minLength": 3,
                    "maxLength": 80,
                },
            },
            "required": ["target_agent", "reason"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "*",  # Marqueur : transverse, registry décide qui l'expose.
}


# ─────────────────────────────────────────────────────────────────────
# Validation côté tool (forme + autorisation locale)
# ─────────────────────────────────────────────────────────────────────


def is_handoff_allowed(*, source_agent: str, target_agent: str) -> bool:
    """True si la transition `source → target` est dans la whitelist."""
    if not source_agent or not target_agent:
        return False
    if source_agent == target_agent:
        return False
    allowed = _ALLOWED_HANDOFFS.get(source_agent)
    if allowed is None:
        return False
    return target_agent in allowed


def investigation_done(
    *, source_agent: str, tools_called: list[str]
) -> tuple[bool, list[str]]:
    """Vérifie que les préconditions d'investigation sont remplies.

    Retourne ``(ok, missing_tools_hint)`` où ``missing_tools_hint``
    aide le LLM à corriger sa séquence : si le handoff est refusé,
    il sait quels tools il devrait appeler avant.

    Pour ``compliance.remediation`` : on exige au moins
    ``_MIN_INVESTIGATION_TOOLS_FOR_HANDOFF`` outils différents parmi
    `_INVESTIGATION_TOOLS`. Pour les autres sources, pas de
    précondition (handoff plus rare et déjà restreint par whitelist).
    """
    if source_agent != "compliance.remediation":
        return True, []
    distinct_invest = {
        t for t in (tools_called or []) if t in _INVESTIGATION_TOOLS
    }
    if len(distinct_invest) >= _MIN_INVESTIGATION_TOOLS_FOR_HANDOFF:
        return True, []
    missing = sorted(_INVESTIGATION_TOOLS - distinct_invest)
    return False, missing


# ─────────────────────────────────────────────────────────────────────
# Execute — produit le signal d'interruption
# ─────────────────────────────────────────────────────────────────────


def execute(
    ctx: ToolContext,
    *,
    target_agent: str,
    reason: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    safe_target = (target_agent or "").strip().lower()
    safe_reason = (reason or "").strip()[:80]

    if not safe_target:
        return {"error": "missing_target_agent"}

    if not safe_reason:
        return {"error": "missing_reason"}

    if not is_handoff_allowed(
        source_agent=ctx.agent_id, target_agent=safe_target
    ):
        logger.warning(
            "handoff_to_agent.not_allowed source=%s target=%s",
            ctx.agent_id,
            safe_target,
        )
        return {
            "error": "handoff_not_allowed",
            "source_agent": ctx.agent_id,
            "target_agent": safe_target,
            "allowed": sorted(
                list(_ALLOWED_HANDOFFS.get(ctx.agent_id) or [])
            ),
        }

    # La précondition d'investigation est vérifiée côté runtime
    # (qui connaît la liste `tools_called` du tour). Ici on signale
    # juste l'intention.
    return {
        "interrupt_with_handoff": True,
        "target_agent": safe_target,
        "reason": safe_reason,
        "source_agent": ctx.agent_id,
    }


__all__ = [
    "SPEC",
    "execute",
    "investigation_done",
    "is_handoff_allowed",
]

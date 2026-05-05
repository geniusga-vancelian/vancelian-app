"""Tool transverse `consult_specialist` — cross-agent consultation Phase 2c.

Permet à un sub-agent (typiquement `compliance.transactional` ou
`compliance.general`) de **demander à un autre agent racine** une
information factuelle pour composer une réponse riche, **sans
quitter le tour client courant**.

──────────────────────────────────────────────────────────────────────
Pattern interrupt-based — comme `ask_user_question`

Le tool ne fait pas l'appel lui-même : il **valide** le purpose et
les params, puis retourne un payload signal :

    {
      "interrupt_with_consult": True,
      "target_agent":   "product",
      "purpose":        "explain_deposit_delay",
      "params":         {"method": "bank_transfer_in"},
      "question":       "Quel est le délai standard ...?",
    }

Le runtime intercepte ce signal, lance un **sous-runtime sandboxé**
sur l'agent target, capture le texte final, puis **remplace** le
résultat de tool injecté au LLM caller par :

    {
      "specialist_target":  "product",
      "specialist_purpose": "explain_deposit_delay",
      "specialist_text":    "<réponse markdown du specialist>",
      "duration_ms":        480,
    }

Ainsi, du point de vue du LLM caller, c'est juste un tool synchrone
qui retourne du texte exploitable. La complexité du sous-runtime
reste invisible.

──────────────────────────────────────────────────────────────────────
Sécurité — aucun signal libre

Le LLM caller **ne formule pas la question** : seul le couple
``(purpose, params)`` est accepté, et la question naturelle est
composée déterministiquement par
:py:func:`consult_purposes.build_question`. Cela élimine tout risque
de **tipping-off cross-agent** (un agent compliance ne peut pas leak
un signal AML interne dans une question vers product).

──────────────────────────────────────────────────────────────────────
Limitations Phase 2c

  - **Profondeur 1** : un specialist consulté ne peut PAS lui-même
    appeler `consult_specialist` (le runtime filtre ce tool quand
    `consult_in_progress=True`).
  - **N consultations max par tour caller** : limite hardcodée à 3
    (config-overridable plus tard si besoin).

Cf. `docs/arquantix/MULTI_AGENTS.md` § 2.5 et `PRODUCT_AGENT.md` § 5.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared import consult_purposes

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "consult_specialist",
        "description": (
            "Consulte un autre agent racine (ex. `product`) pour "
            "obtenir une information factuelle (délai, base produit). "
            "À utiliser pour composer une réponse riche au client : "
            "tu poses la question via un `purpose` whitelisté + "
            "`params` structurés (PAS de question libre), tu reçois "
            "le texte du specialist et tu peux le citer ou paraphraser "
            "dans ta réponse finale. Idempotent. Sans side-effect. "
            "Profondeur 1 : un specialist consulté ne peut pas "
            "lui-même consulter."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "Agent racine cible. `product` pour les bases "
                        "produit / délais opérationnels. `trust` "
                        "(Cognitive Bot v4 — Lot 4) pour les encarts "
                        "factuels rassurants sur la régulation, la "
                        "custody ou la sécurité."
                    ),
                    "enum": ["product", "trust"],
                    "maxLength": 32,
                },
                "purpose": {
                    "type": "string",
                    "description": (
                        "Identifiant whitelisté du sujet de "
                        "consultation. Cibles product : "
                        "`explain_deposit_delay`, "
                        "`explain_withdrawal_delay`, "
                        "`explain_kyc_review_typical_delay`, "
                        "`explain_product_basics`, "
                        "`explain_swap_settlement_delay`. Cibles "
                        "trust : `reassure_about_regulation`, "
                        "`reassure_about_custody`, "
                        "`reassure_about_security`."
                    ),
                    "maxLength": 64,
                },
                "params": {
                    "type": "object",
                    "description": (
                        "Paramètres structurés selon le `purpose`. "
                        "Ex. pour `explain_deposit_delay` : "
                        "`{\"method\": \"bank_transfer_in\"}`. "
                        "Vide pour les purpose sans param."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["target", "purpose"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "*",  # Marqueur : transverse (filtré côté registry agent par agent).
}


def execute(
    ctx: ToolContext,
    *,
    target: str,
    purpose: str,
    params: Optional[dict[str, Any]] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Validation des inputs + signal d'interruption pour le runtime.

    Le runtime se charge ensuite de :
      1. Lancer un sous-loop sur `target_agent`,
      2. Capturer le texte final,
      3. Remplacer le résultat du tool par un payload texte exploitable.
    """
    safe_target = (target or "").strip().lower()
    safe_purpose = (purpose or "").strip()

    if not consult_purposes.is_known_purpose(safe_purpose):
        logger.warning(
            "consult_specialist.unknown_purpose agent=%s conv=%s purpose=%r",
            ctx.agent_id,
            ctx.conversation_id,
            purpose,
        )
        return {
            "error": "unknown_purpose",
            "purpose": safe_purpose,
            "available_purposes": [
                p["name"] for p in consult_purposes.list_known_purposes()
            ],
        }

    expected_target = consult_purposes.target_agent_for(safe_purpose)
    if expected_target and safe_target != expected_target:
        logger.warning(
            "consult_specialist.target_mismatch agent=%s purpose=%s "
            "got=%r expected=%r",
            ctx.agent_id,
            safe_purpose,
            safe_target,
            expected_target,
        )
        return {
            "error": "target_mismatch",
            "purpose": safe_purpose,
            "target_for_purpose": expected_target,
        }

    ok, errors, normalized = consult_purposes.validate_params(
        safe_purpose, params
    )
    if not ok:
        logger.info(
            "consult_specialist.invalid_params agent=%s purpose=%s errors=%s",
            ctx.agent_id,
            safe_purpose,
            errors,
        )
        return {
            "error": "invalid_params",
            "purpose": safe_purpose,
            "details": errors,
        }

    question = consult_purposes.build_question(safe_purpose, normalized)
    if not question:
        return {"error": "purpose_no_question", "purpose": safe_purpose}

    # Signal au runtime : il déclenche un sous-loop sur `target_agent`
    # avec `question` comme user_message. La valeur réelle injectée
    # au LLM caller sera composée par le runtime (specialist_text + meta).
    return {
        "interrupt_with_consult": True,
        "target_agent": expected_target,
        "purpose": safe_purpose,
        "params": normalized,
        "question": question,
    }

"""Persistance « attente de réponse » après QCM ou liste fermée.

Permet d’ancrer résolution des suivis ultra-courts (« B », « le 2 », …) et
injecte une ligne de contexte machine dans `memory_state` pour le tour user
suivant.

Schéma `message_payload["expected_answer_scope"]` (JSONB, rétro-compatible) :

  * ``kind`` : ``multiple_choice`` | ``listing_choice`` (auto-QCM annexé).
  * ``source`` : ``router_qcm`` | ``agent_qcm_tool`` | ``auto_qcm``.
  * ``prompt_excerpt`` : début court du prompt (audit / debug UI).
  * ``choices`` : liste ``{"id"|null, "label": str}`` des options hors freeform.

Référence : ``docs/arquantix/ASSISTANCE_BOT_REFERENCE.md`` §11.
"""

from __future__ import annotations

from typing import Any, Optional


EXPECTED_ANSWER_SCOPE_KEY = "expected_answer_scope"
PENDING_EXPECTATION_MEMORY_KEY = "pending_answer_expectation"


def merge_expected_answer_scope_into_payload(
    payload: Optional[dict[str, Any]],
    scope: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Retourne un payload étendu (copie défensive si ``payload`` non vide)."""
    if scope is None or not isinstance(scope, dict) or not scope:
        return payload
    out = dict(payload) if isinstance(payload, dict) else {}
    out[EXPECTED_ANSWER_SCOPE_KEY] = scope
    return out


def build_scope_router_qcm(
    *,
    prompt: str,
    option_dicts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": "multiple_choice",
        "source": "router_qcm",
        "prompt_excerpt": (prompt or "")[:400],
        "choices": list(_normalize_choice_dicts(option_dicts)),
    }


def build_scope_agent_qcm(
    *,
    prompt: str,
    option_dicts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": "multiple_choice",
        "source": "agent_qcm_tool",
        "prompt_excerpt": (prompt or "")[:400],
        "choices": list(_normalize_choice_dicts(option_dicts)),
    }


def build_scope_auto_qcm(
    *,
    prompt: str,
    option_strings: list[str],
) -> dict[str, Any]:
    """Pour auto-QCM : options = libellés (index 1-based côté texte utilisateur)."""
    choices = []
    for i, label in enumerate(option_strings, start=1):
        t = str(label or "").strip()[:240]
        if t:
            choices.append({"ordinal": i, "label": t})
    return {
        "kind": "listing_choice",
        "source": "auto_qcm",
        "prompt_excerpt": (prompt or "")[:400],
        "choices": choices,
    }


def _normalize_choice_dicts(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_freeform = False
    for item in raw:
        if not isinstance(item, dict):
            continue
        oid = item.get("id")
        oid_s = None if oid is None else str(oid).strip()
        lbl = str(item.get("label") or "").strip()[:260]
        if not lbl:
            continue
        if oid_s == "freeform":
            seen_freeform = True
            continue  # hors périmètre « réponse fermée »
        entry: dict[str, Any] = {"label": lbl}
        if oid_s:
            entry["id"] = oid_s[:128]
        out.append(entry)
    return out


def extract_pending_expectation_from_recent_turns(
    recent_turns: Optional[list[dict[str, Any]]],
) -> Optional[dict[str, Any]]:
    """À appeler alors que ``recent_turns`` se termine par le **user courant**.

    Lit le dernier tour **assistant** et renvoie son ``expected_answer_scope``
    ou un scope synthétique si ``message_type=choices``, ou depuis ``auto_qcm``.
    """
    if not recent_turns or len(recent_turns) < 2:
        return None
    last = recent_turns[-1]
    if not isinstance(last, dict) or last.get("role") != "user":
        return None
    assistant = recent_turns[-2]
    if not isinstance(assistant, dict) or assistant.get("role") != "assistant":
        return None

    mp = assistant.get("message_payload")
    if isinstance(mp, dict):
        scoped = mp.get(EXPECTED_ANSWER_SCOPE_KEY)
        if isinstance(scoped, dict) and scoped.get("choices"):
            return scoped
        mt = (
            str(assistant.get("message_type") or "text").strip().lower()
        )
        if mt == "choices" and isinstance(mp.get("options"), list):
            return build_scope_agent_qcm(
                prompt=str(assistant.get("content") or "")[:600],
                option_dicts=mp["options"],  # type: ignore[list-item]
            )
        aq = mp.get("auto_qcm")
        if isinstance(aq, dict) and aq.get("options"):
            opts = aq["options"]
            if isinstance(opts, list):
                prompts = aq.get("prompt") or assistant.get("content") or ""
                str_opts = [str(x) for x in opts if x is not None]
                if str_opts:
                    return build_scope_auto_qcm(prompt=str(prompts), option_strings=str_opts)

    return None


def render_pending_expectation_for_prompt(exp: Optional[dict[str, Any]]) -> str:
    """Bloc court injecté dans le system prompt agents (Pas le router pour éviter bruit)."""
    if not isinstance(exp, dict) or not exp:
        return ""
    choices = exp.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    lines = ["## Attente de réponse (tour précédent)", ""]
    pe = exp.get("prompt_excerpt")
    if isinstance(pe, str) and pe.strip():
        lines.append(f"Prompt / question : {_one_line(pe)}")
        lines.append("")
    lines.append("Réponses fermées encore valides pour ce tour (le user peut répondre très court) :")
    for c in choices[:14]:
        if not isinstance(c, dict):
            continue
        oid = c.get("id") or c.get("ordinal")
        lbl = c.get("label")
        if not lbl:
            continue
        pref = f"({oid}) " if oid is not None else "- "
        lines.append(f"- {pref}{lbl}")
    lines.append("")
    lines.append(
        "Interprète toute réponse elliptique (lettre, chiffre, « le premier », …) "
        "comme désignant **l’option correspondante**, sans redemander inutilement."
    )
    return "\n".join(lines)


def _one_line(s: str, *, mx: int = 220) -> str:
    t = " ".join(s.strip().split())
    if len(t) <= mx:
        return t
    return t[: mx - 1] + "…"


__all__ = [
    "EXPECTED_ANSWER_SCOPE_KEY",
    "PENDING_EXPECTATION_MEMORY_KEY",
    "merge_expected_answer_scope_into_payload",
    "build_scope_router_qcm",
    "build_scope_agent_qcm",
    "build_scope_auto_qcm",
    "extract_pending_expectation_from_recent_turns",
    "render_pending_expectation_for_prompt",
]

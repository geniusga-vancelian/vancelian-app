"""Audit trail des décisions agents — Phase 2a.

Deux responsabilités :

  1. **Sanitizer anti-tipping-off** (`sanitize_reasoning`) : remplace les
     mots blacklistés par `[REDACTED]` dans tout texte de raisonnement
     LLM avant persistance / log. Défense en profondeur — même si un
     futur dev oublie de filtrer, le sanitizer rattrape.

  2. **Persistance row** (`persist_decision`) : écrit un `agent_decision`
     dans la table `assistance_agent_decisions` (migration 148). Best-effort :
     une erreur de persistance ne fait JAMAIS planter le runtime.

Spec de référence : `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 4.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from database import AssistanceAgentDecision

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Sanitizer anti-tipping-off (défense en profondeur)
# ─────────────────────────────────────────────────────────────────────────


# Liste des mots interdits dans tout texte LLM persistable. Doit être
# alignée avec `tests/test_assistance_short_circuits_unit.py::TIPPING_OFF_BLACKLIST`.
# Le `\b` regex word boundary évite les faux positifs (ex. ne pas matcher
# "ample" dans "example"). On normalise en minuscules avant comparaison.
TIPPING_OFF_BLACKLIST: tuple[str, ...] = (
    # État/action sur le compte qui ne doit pas leak
    "fraude",
    "fraud",
    "blanchiment",
    "money laundering",
    "suspicion",
    "suspect",
    "soupçon",
    "soupcon",
    "soupçonné",
    "soupconne",
    "enquête",
    "enquete",
    "investigation",
    "watchlist",
    "ofac",
    "pep",
    "sanction",
    "sanctioned",
    "embargo",
    # Niveaux/scores internes
    "risk_score",
    "level_high",
    "level_medium",
    "score_high",
    "score_medium",
    # Décisions internes
    "block_for_aml",
    "deny_for_aml",
    "freeze_for_aml",
    # Intitulés équipes
    "compliance team",
    "fraud team",
    "aml team",
)


_RE_FLAGS = re.IGNORECASE | re.UNICODE


def _compile_blacklist_regex() -> re.Pattern[str]:
    """Compile une seule regex à `\\b(<term1>|<term2>|...)\\b`."""
    escaped = "|".join(re.escape(w) for w in TIPPING_OFF_BLACKLIST)
    pattern = rf"\b({escaped})\b"
    return re.compile(pattern, _RE_FLAGS)


_BLACKLIST_RE = _compile_blacklist_regex()


def sanitize_reasoning(text: str | None) -> tuple[str, int]:
    """Censure les termes blacklistés. Retourne `(texte_safe, n_redactions)`.

    Args:
        text: chaîne libre potentiellement issue d'un LLM. ``None`` →
              `("", 0)`.

    Returns:
        Tuple `(safe_text, hits)` où `hits` est le nombre de
        substitutions effectuées (utile pour métrique
        `assistance_agent_tipping_off_redactions_total`).

    Notes:
        - Idempotent : `sanitize(sanitize(t))` == `sanitize(t)` (le
          token `[REDACTED]` n'est lui-même pas dans la blacklist).
        - Pas de tokenisation linguistique : on travaille au niveau mot
          via word-boundary regex. C'est suffisant pour le périmètre
          spécifié et conserve une perf O(n).
    """
    if not text:
        return "", 0

    counter = {"n": 0}

    def _replace(_m: re.Match[str]) -> str:
        counter["n"] += 1
        return "[REDACTED]"

    cleaned = _BLACKLIST_RE.sub(_replace, text)
    return cleaned, counter["n"]


# ─────────────────────────────────────────────────────────────────────────
# Persistance d'une décision agent (table 148)
# ─────────────────────────────────────────────────────────────────────────


def _coerce_uuid(value: Any) -> Optional[UUID]:
    """Tolère str ou UUID, renvoie None si invalide ou None."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def persist_decision(
    db: Session,
    *,
    conversation_id: Any,
    message_id: Any = None,
    agent_id: str,
    iteration: int,
    tool_name: str,
    autonomy_level: str,
    arguments: Optional[dict] = None,
    result_summary: Optional[dict] = None,
    proposed_action: Optional[str] = None,
    target_client_id: Any = None,
    target_person_id: Any = None,
    reasoning_summary: Optional[str] = None,
    review_status: str = "auto",
    duration_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    correlation_id: Optional[str] = None,
    extra_columns: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Persiste une row `assistance_agent_decisions`. Best-effort.

    Garanties :
      - `reasoning_summary` est **toujours** sanitizé avant écriture
        (sécurité de défense en profondeur).
      - Aucune exception remontée : en cas d'échec DB on log et on
        retourne ``None`` (le runtime continue).
      - Le commit/flush est délégué à l'appelant (le runtime peut
        regrouper plusieurs décisions par tour).

    Args:
        autonomy_level: doit être dans `{"L0","L1","L2","L3"}`. Sinon, on
                        log un warning et on stocke quand même pour
                        traçabilité (CHECK SQL fera office de barrière
                        tertiaire).

    Returns:
        L'`id` (UUID stringifié) de la row persistée, ou ``None`` en cas
        d'échec.

    Cognitive Bot v4 — Lot 6 (2026-05-04). Le kwarg ``extra_columns``
    permet à un caller de remplir des colonnes natives (ex.
    ``emotional_intent``, ``conversation_stage``, ``trust_level``,
    ``primary_goal``, ``next_best_action``, ``knowledge_level``)
    sans coupler le module ``audit`` à un schéma cognitif spécifique.
    Seules les clés correspondant à un attribut existant de
    ``AssistanceAgentDecision`` sont appliquées (best-effort, silent
    ignore sur les autres).
    """
    conv_uuid = _coerce_uuid(conversation_id)
    if conv_uuid is None:
        logger.warning(
            "audit.persist_decision invalid conversation_id=%r — skip",
            conversation_id,
        )
        return None

    if autonomy_level not in ("L0", "L1", "L2", "L3"):
        logger.warning(
            "audit.persist_decision invalid autonomy_level=%r tool=%s",
            autonomy_level,
            tool_name,
        )

    safe_reasoning, redactions = sanitize_reasoning(reasoning_summary)
    if redactions > 0:
        logger.warning(
            "audit.persist_decision sanitized n=%d agent=%s tool=%s",
            redactions,
            agent_id,
            tool_name,
        )

    row_id = uuid4()
    # CRITIQUE : on encapsule dans un SAVEPOINT (`begin_nested`) pour
    # isoler tout échec de persistance sans corrompre la transaction
    # parente (où le user/assistant message est en train d'être persisté).
    # Sans cela, une PendingRollbackError sur ce flush polluerait la
    # session et bloquerait tout flush ultérieur → SSE coincé → "en
    # attente" infini côté Flutter (cf. incident 2026-05-02).
    try:
        with db.begin_nested():
            row = AssistanceAgentDecision(
                id=row_id,
                conversation_id=conv_uuid,
                message_id=_coerce_uuid(message_id),
                agent_id=agent_id[:32],
                iteration=int(iteration),
                tool_name=tool_name[:64],
                autonomy_level=autonomy_level[:4],
                arguments_json=arguments or {},
                result_summary=result_summary,
                proposed_action=(proposed_action[:64] if proposed_action else None),
                target_client_id=_coerce_uuid(target_client_id),
                target_person_id=_coerce_uuid(target_person_id),
                reasoning_summary=safe_reasoning or None,
                review_status=review_status[:16],
                duration_ms=duration_ms,
                error_code=(error_code[:32] if error_code else None),
                correlation_id=(correlation_id[:64] if correlation_id else None),
            )
            # Cognitive Bot v4 — Lot 6 : double-write des colonnes
            # cognitives via setattr best-effort. Toute clé inconnue
            # (typo, schéma futur) est silently ignorée — le runtime
            # ne doit jamais casser à cause d'une colonne absente côté
            # ORM (ex. environnement pré-migration 152).
            if extra_columns:
                for key, value in extra_columns.items():
                    if value is None:
                        continue
                    if hasattr(row, key):
                        setattr(row, key, value)
            db.add(row)
            # le flush implicite se fait au commit du savepoint
    except Exception:
        logger.exception(
            "audit.persist_decision_failed conv=%s agent=%s tool=%s",
            conv_uuid,
            agent_id,
            tool_name,
        )
        return None

    return str(row_id)


def result_summary(result: Any, *, max_chars: int = 4096) -> dict:
    """Construit un résumé JSON-safe d'un retour de tool.

    Convention :
      - Si `result` est un dict, on shallow-clone et on tronque les
        valeurs str trop longues (anti bloat JSONB).
      - Sinon, on enveloppe dans `{"value": str(result)}` tronqué.

    Pas une serialization sécurité-stricte : c'est juste un garde-fou
    contre les payloads aberrants. La sanitization tipping-off s'applique
    en parallèle sur le `reasoning_summary` (pas ici).
    """
    if isinstance(result, dict):
        out = {}
        for k, v in result.items():
            if isinstance(v, str) and len(v) > max_chars:
                out[k] = v[:max_chars] + "…"
            elif isinstance(v, (dict, list)):
                # On garde la structure mais on évite les profondeurs absurdes
                out[k] = v
            else:
                out[k] = v
        return out
    if isinstance(result, list):
        return {"value": result[:50]}
    s = str(result)
    if len(s) > max_chars:
        s = s[:max_chars] + "…"
    return {"value": s}

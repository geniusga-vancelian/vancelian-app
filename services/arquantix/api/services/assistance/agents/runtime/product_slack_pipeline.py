"""Pipeline multi-phases agent **product** aligné sur le bot Slack (Karpathy).

Phases (cf. discussion archi 2026-05) :
  1. Guardrail entrée (IN_DOMAIN / …) — LLM + JSON.
  2. Pass 1 retrieval — LLM lit ``index.md`` + question, tool `return_wiki_paths`.
  3. Chargement FS — corps des fiches tronqués, injectés dans le system prompt.
  4. Génération — ``run_agent_loop`` habituel (tools SQL / widgets / wiki).
  5. Juge sortie (optionnel) — PASS / REWRITE / BUFFER.

Activé par défaut ; désactivable avec ``ASSISTANCE_PRODUCT_SLACK_PIPELINE_ENABLED=false``
et pour les tours top-level ``agent_id=product`` (pas les sous-loops
``consult_specialist``).

Voir ``config.assistance_product_*`` pour les sous-flags.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, AsyncIterator, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.config import (
    assistance_product_pipeline_index_max_chars,
    assistance_product_pipeline_model,
    assistance_product_pipeline_output_judge_enabled,
    assistance_product_pipeline_page_max_chars,
    assistance_product_slack_pipeline_enabled,
)
from services.assistance.agents.openai_client import (
    chat_completion,
    chat_completion_with_tools,
)
from services.assistance.agents.prompt_builder import load_agent_system_prompt
from services.assistance.agents.repositories import wiki_repo
from services.assistance.agents.runtime.agent_loop import run_agent_loop
from services.assistance.agents.tools import registry as tools_registry
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_INDEX_FILE = wiki_repo.WIKI_ROOT / "index.md"
_SQL_SENTINEL = "__use_sql_catalog__"
_PASS1_TOOL_NAME = "return_wiki_paths"

_BLOCKED_FALLBACK_FR = (
    "Je ne peux pas confirmer cette réponse avec nos sources internes. "
    "Pour une vérification personnalisée, contacte le support Vancelian "
    "via la rubrique Aide de l'application."
)
_BLOCKED_FALLBACK_EN = (
    "I can't confirm this answer against our internal sources. "
    "For a personalized check, please contact Vancelian support "
    "through the in-app Help section."
)

_PASS1_TOOL_SPEC: dict = {
    "type": "function",
    "function": {
        "name": _PASS1_TOOL_NAME,
        "description": (
            "Retourne 0 à 5 chemins relatifs de fiches wiki EXACTEMENT "
            "tels que listés dans index.md (ex. faq/savings/foo.md), "
            "ou le sentinelle __use_sql_catalog__ seul si le SQL canonique "
            "suffit sans wiki MD."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 0,
                    "maxItems": 5,
                    "items": {"type": "string", "minLength": 1, "maxLength": 200},
                },
                "reason": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 400,
                },
            },
            "required": ["paths", "reason"],
            "additionalProperties": False,
        },
    },
}


def _load_prompt_file(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("product_slack_pipeline.prompt_read_failed path=%s exc=%s", path, exc)
        return ""


def _language_hint_for_replies(
    user_message: str,
    recent_turns: Optional[list[dict]] = None,
) -> str:
    """Heuristique FR vs EN pour les réponses scriptées (guardrail, juge BLOCK).

    Les messages courts sans accents (ex. *« sur quoi tu me proposes d'investir ? »*)
    retombaient en EN — mauvais fallback. On enrichit les marqueurs FR et on
    regarde l'historique user récent si le tour courant est ambigu.
    """
    raw = user_message or ""
    text = raw.lower()
    if re.search(r"[àâäéèêëïîôùûüçœæ]", raw):
        return "fr"
    fr_markers = (
        "comment ",
        "pourquoi ",
        "combien ",
        "qu'est-ce",
        "quel ",
        "quelle ",
        "quels ",
        "quoi ",
        "délai",
        "frais ",
        "bonjour",
        "merci",
        "coffre",
        "offre ",
        " tu ",
        " vous ",
        "sur quoi",
        " propose",
        " proposes",
        " investir",
        "investir ",
        "épargne",
        "retraite",
        "placement",
        " conseil",
        " connais",
        "où ",
        " où ",  # nbsp variants rare; "où" with accent handled above
        " dans ",
        " avec ",
        " pour ",
        " sur ",
        " mon ",
        " ma ",
        " mes ",
        " tes ",
        " ses ",
        " leur ",
        "ceux ",
        "celui ",
        "selon ",
        "dis-moi",
        "est-ce",
    )
    if any(m in text for m in fr_markers):
        return "fr"
    if recent_turns:
        for t in reversed(recent_turns[-8:]):
            if not isinstance(t, dict):
                continue
            if (t.get("role") or "").strip() != "user":
                continue
            c = str(t.get("content") or "")
            if re.search(r"[àâäéèêëïîôùûüçœæ]", c):
                return "fr"
            cl = c.lower()
            if any(m in cl for m in fr_markers):
                return "fr"
    return "en"


def _format_recent_turns(turns: list[dict], *, max_turns: int = 8) -> str:
    if not turns:
        return ""
    tail = turns[-max_turns:]
    lines: list[str] = []
    for t in tail:
        role = (t.get("role") or "").strip()
        content = (t.get("content") or "").strip().replace("\n", " ")
        if not role or not content:
            continue
        lines.append(f"[{role}] {content[:400]}")
    if not lines:
        return ""
    return "Historique (derniers tours) :\n" + "\n".join(lines)


def _load_index_text() -> str:
    try:
        raw = _INDEX_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("product_slack_pipeline.index_read_failed exc=%s", exc)
        return ""
    cap = assistance_product_pipeline_index_max_chars()
    if cap and len(raw) > cap:
        return raw[:cap] + "\n\n[… index tronqué …]"
    return raw


def normalize_index_path(raw: str) -> str:
    p = (raw or "").strip().strip("`").strip()
    if p.lower().startswith("wiki/"):
        p = p[5:]
    return p


_NON_FAQ_TOP_FOR_PATH = frozenset({"concepts", "entities", "policies"})


def wiki_markdown_relative_path(category: str, slug: str) -> str:
    """Aligné sur `web/src/lib/admin/assistanceWikiRefs.ts` → `wikiMarkdownRelativePath`."""
    c = (category or "").strip().lower()
    s = (slug or "").strip().lower()
    if c in _NON_FAQ_TOP_FOR_PATH:
        return f"{c}/{s}.md"
    return f"faq/{c}/{s}.md"


def parse_index_path_to_category_slug(rel_path: str) -> Optional[tuple[str, str]]:
    """Parse ``faq/cat/slug.md`` ou ``concepts/slug.md`` → (category, slug)."""
    p = normalize_index_path(rel_path)
    if not p or p == _SQL_SENTINEL:
        return None
    if p.endswith(".md"):
        p = p[:-3]
    parts = [x for x in p.replace("\\", "/").split("/") if x]
    if len(parts) < 2:
        return None
    if parts[0] == "faq" and len(parts) >= 3:
        cat, slug = parts[1], parts[2]
        if cat in wiki_repo.FAQ_CATEGORIES:
            return cat, slug
        return None
    if parts[0] in wiki_repo.NON_FAQ_DIRS and len(parts) >= 2:
        return parts[0], parts[1]
    return None


def _run_input_guardrail(
    *,
    user_message: str,
    recent_turns: list[dict],
) -> dict[str, Any]:
    system = _load_prompt_file("product_pipeline_input_guardrail.md")
    if not system:
        return {
            "verdict": "IN_DOMAIN",
            "reply_fr": "",
            "reply_en": "",
            "use_wiki": True,
        }
    user_parts = [
        f"Message client :\n{user_message.strip()}",
        _format_recent_turns(recent_turns),
    ]
    user_content = "\n\n".join(x for x in user_parts if x)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    model = assistance_product_pipeline_model()
    raw = chat_completion(
        messages,
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("product_slack_pipeline.guardrail_json_invalid raw=%s", raw[:200])
        return {
            "verdict": "IN_DOMAIN",
            "reply_fr": "",
            "reply_en": "",
            "use_wiki": True,
        }
    verdict = str(data.get("verdict") or "IN_DOMAIN").strip().upper()
    if verdict not in {
        "IN_DOMAIN",
        "OFF_TOPIC",
        "PROMPT_INJECTION",
        "PII_RISK",
    }:
        verdict = "IN_DOMAIN"
    return {
        "verdict": verdict,
        "reply_fr": str(data.get("reply_fr") or ""),
        "reply_en": str(data.get("reply_en") or ""),
        "use_wiki": bool(data.get("use_wiki", True)),
    }


def _run_pass1_paths(
    *,
    user_message: str,
    recent_turns: list[dict],
) -> tuple[list[str], str]:
    system = _load_prompt_file("product_pipeline_pass1.md")
    index_text = _load_index_text()
    if not system or not index_text:
        return [], "index_or_prompt_missing"
    user_block = "\n\n".join(
        [
            f"Question client :\n{user_message.strip()}",
            _format_recent_turns(recent_turns),
            "---\nINDEX.MD\n---\n" + index_text,
        ]
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_block},
    ]
    model = assistance_product_pipeline_model()
    try:
        msg = chat_completion_with_tools(
            messages,
            model=model,
            tools=[_PASS1_TOOL_SPEC],
            tool_choice={"type": "function", "function": {"name": _PASS1_TOOL_NAME}},
            temperature=0.1,
        )
    except LLMError as exc:
        logger.warning("product_slack_pipeline.pass1_llm_error exc=%s", exc)
        return [], "llm_error"

    tool_calls = (msg or {}).get("tool_calls") or []
    for call in tool_calls:
        fn = (call or {}).get("function") or {}
        if fn.get("name") != _PASS1_TOOL_NAME:
            continue
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            return [], "bad_tool_args"
        paths_raw = args.get("paths") if isinstance(args, dict) else None
        if not isinstance(paths_raw, list):
            return [], "no_paths"
        paths = [str(p).strip() for p in paths_raw if str(p).strip()]
        reason = str((args or {}).get("reason") or "") if isinstance(args, dict) else ""
        logger.info(
            "product_slack_pipeline.pass1_ok paths=%d reason=%.80s",
            len(paths),
            reason,
        )
        return paths, reason
    return [], "no_tool_call"


def _build_preload_block_and_refs(
    paths: list[str],
) -> tuple[str, list[dict[str, str]]]:
    """Construit le bloc system « pré-chargé » + liste JSON des fiches réellement lues FS."""
    seen: set[tuple[str, str]] = set()
    resolved: list[tuple[str, str]] = []
    for raw_path in paths:
        if raw_path.strip() == _SQL_SENTINEL:
            continue
        pair = parse_index_path_to_category_slug(raw_path)
        if pair is None:
            continue
        if pair in seen:
            continue
        seen.add(pair)
        resolved.append(pair)

    max_chars = assistance_product_pipeline_page_max_chars()
    chunks: list[str] = []
    refs: list[dict[str, str]] = []
    for cat, slug in resolved[:5]:
        page = wiki_repo.fetch_page(category=cat, slug=slug)
        if page is None:
            continue
        body = "\n\n".join(
            x for x in (page.short_answer or "", page.details or "") if x
        ).strip() or (page.body_markdown or "")[: max_chars * 2]
        if len(body) > max_chars:
            body = body[:max_chars] + "\n\n[… tronqué …]"
        title = page.title or slug
        chunks.append(f"### {cat}/{slug} — {title}\n\n{body}")
        refs.append(
            {
                "category": cat,
                "slug": slug,
                "title": title,
                "relative_path": wiki_markdown_relative_path(cat, slug),
            }
        )

    if not chunks:
        return "", []

    instr = (
        "Les extraits ci-dessus proviennent du **Pass 3** du pipeline wiki. "
        "Ils sont **prioritaires** pour tout ce qu'ils couvrent. Tu peux "
        "encore appeler `read_wiki_page` pour compléter une fiche absente. "
        "Pour le reste, `select_wiki_pages` + `read_wiki_page` uniquement."
    )
    block = (
        "## Contexte wiki pré-chargé (pipeline produit)\n\n"
        + instr
        + "\n\n---\n\n"
        + "\n\n---\n\n".join(chunks)
    )
    return block, refs


_CRITERIA_KEYS: tuple[str, ...] = (
    "GROUNDED",
    "ACCURATE_VOCABULARY",
    "NO_RECOMMENDATION",
    "COMPLETE",
    "DISCLAIMERS",
)


def normalize_judge_llm_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Valide / normalise le JSON renvoyé par le modèle juge (tests + runtime)."""
    raw_scores = (
        data.get("criteria_scores") if isinstance(data.get("criteria_scores"), dict) else {}
    )
    criteria_scores: dict[str, int] = {}
    for key in _CRITERIA_KEYS:
        try:
            v = int(raw_scores.get(key, 3))
        except (TypeError, ValueError):
            v = 3
        criteria_scores[key] = max(1, min(5, v))

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    gap = str(data.get("knowledge_gap") or "none").lower().strip()
    if gap not in ("none", "minor", "partial", "major"):
        gap = "none"

    raw_disc = data.get("disclaimers_triggered")
    disclaimers: list[str] = []
    if isinstance(raw_disc, list):
        disclaimers = [str(x).strip() for x in raw_disc if str(x).strip()][:24]
    elif isinstance(raw_disc, str) and raw_disc.strip():
        disclaimers = [raw_disc.strip()]

    verdict = str(data.get("verdict") or "PASS").strip().upper()
    if verdict not in ("PASS", "REWRITE", "BLOCK"):
        verdict = "PASS"

    notes = str(data.get("notes") or "").strip()[:2000]
    rewritten = str(data.get("rewritten") or "").strip()

    avg = sum(criteria_scores.values()) / float(len(_CRITERIA_KEYS))
    return {
        "verdict": verdict,
        "criteria_scores": criteria_scores,
        "criteria_average": round(avg, 4),
        "confidence": round(confidence, 4),
        "knowledge_gap": gap,
        "disclaimers_triggered": disclaimers,
        "notes": notes,
        "_rewritten": rewritten,
    }


def judge_metadata_for_persistence(
    normalized: dict[str, Any],
    *,
    rewritten_applied: bool,
    blocked_fallback_applied: bool,
) -> dict[str, Any]:
    """Fragment persistable DB / SSE (sans texte `rewritten`)."""
    return {
        "verdict": normalized.get("verdict"),
        "criteria_scores": dict(normalized.get("criteria_scores") or {}),
        "criteria_average": normalized.get("criteria_average"),
        "confidence": normalized.get("confidence"),
        "knowledge_gap": normalized.get("knowledge_gap"),
        "disclaimers_triggered": list(normalized.get("disclaimers_triggered") or []),
        "notes": str(normalized.get("notes") or "")[:2000],
        "rewritten_applied": bool(rewritten_applied),
        "blocked_fallback_applied": bool(blocked_fallback_applied),
    }


def _run_output_judge(
    *,
    user_message: str,
    assistant_text: str,
    wiki_preload_summary: str,
) -> dict[str, Any]:
    system = _load_prompt_file("product_pipeline_output_judge.md")
    if not system:
        return normalize_judge_llm_payload(
            {"verdict": "PASS", "notes": "judge_prompt_missing"}
        )
    user_content = "\n\n".join(
        [
            f"Question client :\n{user_message.strip()}",
            f"Réponse assistant :\n{assistant_text.strip()}",
            (
                f"Extraits wiki pré-chargés (référence) :\n{wiki_preload_summary[:6000]}"
                if wiki_preload_summary
                else "Aucun pré-chargement wiki (question probablement SQL / outils)."
            ),
        ]
    )
    model = assistance_product_pipeline_model()
    raw = chat_completion(
        [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": "Réponds uniquement avec l'objet JSON demandé.\n\n"
                + user_content,
            },
        ],
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return normalize_judge_llm_payload({"verdict": "PASS", "notes": "judge_json_invalid"})
    if not isinstance(data, dict):
        return normalize_judge_llm_payload({"verdict": "PASS", "notes": "judge_payload_not_object"})
    return normalize_judge_llm_payload(data)


async def iter_product_slack_pipeline_events(
    *,
    db: Session,
    agent_id: str,
    agent_input: AgentInput,
    actor_kind: ActorKind,
    conversation_id: UUID,
    user_id: int,
) -> AsyncIterator[AgentEvent]:
    """Async generator d'`AgentEvent` pour un tour product avec pipeline."""
    if agent_id != "product":
        raise ValueError("product_slack_pipeline applies only to agent product")
    if not assistance_product_slack_pipeline_enabled():
        raise RuntimeError("pipeline disabled — caller should use plain run_agent_loop")

    import asyncio

    user_message = agent_input.user_message or ""
    recent_turns = agent_input.recent_turns or []

    guard = await asyncio.to_thread(
        _run_input_guardrail,
        user_message=user_message,
        recent_turns=recent_turns,
    )
    verdict = str(guard.get("verdict") or "IN_DOMAIN")
    if verdict != "IN_DOMAIN":
        lang = _language_hint_for_replies(user_message, recent_turns)
        if lang == "fr":
            text = (guard.get("reply_fr") or "").strip() or (guard.get("reply_en") or "").strip()
        else:
            text = (guard.get("reply_en") or "").strip() or (guard.get("reply_fr") or "").strip()
        if not text:
            text = (
                "Je peux uniquement t'aider sur Vancelian et nos produits. "
                "Que souhaites-tu savoir ?"
                if lang == "fr"
                else "I can only help with Vancelian and our products. What would you like to know?"
            )
        logger.info(
            "product_slack_pipeline.guard_hit verdict=%s conv=%s",
            verdict,
            conversation_id,
        )
        yield AgentEvent(type="delta", content="")
        yield AgentEvent(type="delta", content=text)
        yield AgentEvent(type="done", completed=True)
        return

    use_wiki = bool(guard.get("use_wiki", True))
    preload_block = ""
    preload_wiki_refs: list[dict[str, str]] = []
    if use_wiki:
        paths, reason = await asyncio.to_thread(
            _run_pass1_paths,
            user_message=user_message,
            recent_turns=recent_turns,
        )
        if paths and any(normalize_index_path(p) == _SQL_SENTINEL for p in paths):
            preload_block = ""
            preload_wiki_refs = []
            logger.info("product_slack_pipeline.sql_sentinel conv=%s reason=%s", conversation_id, reason)
        else:
            block, preload_wiki_refs = await asyncio.to_thread(
                _build_preload_block_and_refs, paths
            )
            preload_block = block

    base_prompt = load_agent_system_prompt(agent_id)
    system_prompt = base_prompt
    if preload_block:
        system_prompt = base_prompt + "\n\n" + preload_block

    relax_guardrail = bool(preload_block)
    judge_enabled = assistance_product_pipeline_output_judge_enabled()

    available_tools = tools_registry.tools_for(agent_id)

    buffered_final: Optional[str] = None
    wiki_summary_for_judge = preload_block[:8000] if preload_block else ""

    async for event in run_agent_loop(
        agent_id=agent_id,
        system_prompt=system_prompt,
        available_tools=available_tools,
        agent_input=agent_input,
        actor_kind=actor_kind,
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        product_pipeline_relax_product_guardrail=relax_guardrail,
    ):
        if (
            judge_enabled
            and event.type == "delta"
            and (event.content or "").strip() != ""
        ):
            buffered_final = event.content
            continue
        if judge_enabled and event.type == "delta" and (event.content or "") == "":
            yield event
            continue
        if judge_enabled and event.type == "done":
            judge_meta_out: Optional[dict] = None
            if buffered_final is not None:
                text = buffered_final.strip()
                if text:
                    judged = await asyncio.to_thread(
                        _run_output_judge,
                        user_message=user_message,
                        assistant_text=text,
                        wiki_preload_summary=wiki_summary_for_judge,
                    )
                    jverdict = str(judged.get("verdict") or "PASS")
                    rewritten_apply = str(judged.get("_rewritten") or "").strip()
                    blocked_fb = False
                    rewritten_applied = False
                    if jverdict == "BLOCK":
                        lang = _language_hint_for_replies(user_message, recent_turns)
                        text = (
                            _BLOCKED_FALLBACK_FR
                            if lang == "fr"
                            else _BLOCKED_FALLBACK_EN
                        )
                        blocked_fb = True
                        logger.warning(
                            "product_slack_pipeline.judge_block conv=%s",
                            conversation_id,
                        )
                    elif jverdict == "REWRITE" and rewritten_apply:
                        text = rewritten_apply
                        rewritten_applied = True
                    judge_meta_out = judge_metadata_for_persistence(
                        judged,
                        rewritten_applied=rewritten_applied,
                        blocked_fallback_applied=blocked_fb,
                    )
                    yield AgentEvent(type="delta", content=text)
            yield AgentEvent(
                type="done",
                completed=event.completed,
                message_id=event.message_id,
                final_agent_id=event.final_agent_id,
                agent_chain=event.agent_chain,
                consultations=event.consultations,
                embeds=event.embeds,
                output_judge_metadata=judge_meta_out,
                wiki_pipeline_preload_refs=preload_wiki_refs if preload_wiki_refs else None,
            )
            continue
        if event.type == "done":
            payload_refs = preload_wiki_refs if preload_wiki_refs else None
            yield AgentEvent(
                type="done",
                completed=event.completed,
                message_id=event.message_id,
                final_agent_id=event.final_agent_id,
                agent_chain=event.agent_chain,
                consultations=event.consultations,
                embeds=event.embeds,
                output_judge_metadata=event.output_judge_metadata,
                runtime_metrics=event.runtime_metrics,
                wiki_pipeline_preload_refs=payload_refs,
            )
            continue
        yield event


def should_use_slack_pipeline(agent_id: str) -> bool:
    """True si le tour courant doit passer par ``iter_product_slack_pipeline_events``."""
    return agent_id == "product" and assistance_product_slack_pipeline_enabled()

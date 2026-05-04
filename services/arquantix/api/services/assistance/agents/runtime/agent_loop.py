"""Runtime agentique Phase 2a — boucle de function-calling itératif.

Conformément à `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 1, ce module
expose un seul point d'entrée :

    async for event in run_agent_loop(...):
        ...

Garanties :

  - **Schema-driven** : le runtime ne connaît aucun champ métier ; il
    découpe par catalogue de tools (cf. `tools/registry.py`).
  - **Autonomy gating** : seul les tools dont le `autonomy_level <=
    autonomy_max(agent_id)` sont exposés au LLM. Le kill-switch global
    force `L0` indépendamment.
  - **Tipping-off filtering matériel** : aucun raisonnement LLM n'est
    persisté avant passage par `audit.sanitize_reasoning`. Idem pour
    chaque résultat de tool destiné à `agent_decisions`.
  - **Borné** : `MAX_ITER`, timeout total, timeout par tool — toutes
    config-driven.
  - **Aucune exception ne sort** : tout problème est mappé sur un
    `AgentEvent(type="error", ...)`. Le caller (service.py) peut
    continuer sa logique de persistance.

Compatibilité : les events yieldés (`started`, `delta`, `choices`,
`done`, `error`) sont identiques à Phase 1 pour ne rien casser côté
mobile.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
from typing import Any, AsyncIterator, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from services.assistance.agents.base import (
    AgentEvent,
    AgentInput,
    ChoiceOption,
)
from services.assistance.agents.config import (
    assistance_agent_autonomy_max,
    assistance_agent_max_iter,
    assistance_agent_model,
    assistance_agent_temperature,
    assistance_agent_timeout_seconds,
    assistance_product_guardrail_enabled,
    assistance_stream_thinking_enabled,
    assistance_tool_timeout_seconds,
    autonomy_le,
)
from services.assistance.agents.openai_client import chat_completion_with_tools
from services.assistance.agents.prompt_builder import load_agent_system_prompt
from services.assistance.agents.runtime import tour_shared_context
from services.assistance.agents.tools import registry as tools_registry
from services.assistance.agents.tools.contracts import (
    ToolContext,
    ToolModule,
    ToolSpec,
    to_openai_tool,
)
from services.assistance.agents.tools.shared import audit
from services.assistance.agents.tools.shared import (
    handoff_to_agent as handoff_to_agent_tool,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Constantes publiques
# ─────────────────────────────────────────────────────────────────────────


MAX_ITER_FALLBACK_MESSAGE = (
    "Je n'arrive pas à finaliser ma réponse pour le moment. "
    "Reformule ta question ou contacte notre équipe via la rubrique « Aide »."
)
"""Texte renvoyé quand `MAX_ITER` est atteint sans réponse finale.

Volontairement neutre (pas de mention « tools », « LLM », « erreur
interne »). Pas de termes anti-tipping-off à protéger ici (constante
statique testée par `test_assistance_short_circuits_unit`)."""


# Limite hard du nombre de consultations specialist par tour client.
# Au-delà, le tool retourne une erreur exploitable par le LLM caller.
# 3 = scénario réaliste max (ex. "explain_deposit_delay" + un fallback).
MAX_CONSULTATIONS_PER_TOUR = 3

# Limite hard de la profondeur de chaîne d'agents (handoff + consult).
# `chain_depth=0` = call direct depuis service.py (top-level tour).
# `chain_depth=1` = sous-runtime spawné par un consult_specialist.
# Profondeur > 1 = interdit (anti-récursion infinie).
MAX_CHAIN_DEPTH = 1


# ─────────────────────────────────────────────────────────────────────────
# Retry LLM sur transient upstream (Phase 2c.1 — résilience OpenAI/Cloudflare)
# ─────────────────────────────────────────────────────────────────────────

# HTTP status codes considérés transient → retry borné. 502/503/504 sont
# typiquement des incidents Cloudflare/edge OpenAI qui rétablissent en
# quelques centaines de ms. 429 = rate-limit transient (le backoff fait
# souvent l'affaire ; pour des 429 persistants, on laisse remonter).
LLM_RETRYABLE_UPSTREAM_CODES: frozenset[str] = frozenset({"502", "503", "504", "429"})

# Nombre maximum de **retries** (en plus de la première tentative). Avec
# 2 retries → pire cas latence = base + 0.5s + 1s = +1.5s, ce qui reste
# acceptable côté UX (le user voit déjà le typing dots).
LLM_MAX_RETRIES = 2

# Backoff fixe par tentative (en secondes). Pas de jitter en V1 — un
# seul user à la fois côté arquantix, pas de risque de thundering herd.
LLM_BACKOFF_SCHEDULE: tuple[float, ...] = (0.5, 1.0)


# ─────────────────────────────────────────────────────────────────────────
# Phase 2 wiki — Guard-rail anti-hallucination agent `product`
# ─────────────────────────────────────────────────────────────────────────
#
# Empiriquement (cf. analyse conv aef5923a, 2026-05-04), gpt-4o-mini
# zappe parfois les tools de lecture sur des questions « faciles » qu'il
# pense connaître, ce qui produit des réponses non-sourcées (turns 30,
# 32) ou des compositions à partir des seuls titres de fiches (turn 42 :
# select_wiki_pages × 2 sans read_wiki_page derrière).
#
# Le guard-rail détecte ces deux patterns en fin de turn et force un
# retry **unique** avec un hint system explicite. Il ne s'applique qu'à
# l'agent `product` et ne se déclenche jamais en sous-loop spécialiste
# (pour ne pas casser les consultations cross-agent où le specialist
# peut légitimement répondre depuis son seul prompt).

# Tools dont l'appel est considéré comme une « lecture de source » côté
# product. `select_wiki_pages` n'en fait PAS partie : il ne retourne que
# les titres + 3 questions preview, pas le contenu.
PRODUCT_KNOWLEDGE_READ_TOOLS: frozenset[str] = frozenset({
    "read_product_knowledge",
    "read_wiki_page",
    "show_instrument_card",
})

PRODUCT_GUARDRAIL_HINT_NO_READ = (
    "Tu n'as appelé aucun tool de lecture (read_product_knowledge, "
    "read_wiki_page, show_instrument_card) avant de répondre. C'est "
    "interdit pour les questions factuelles produit — tu risques de "
    "halluciner. Reformule en commençant par select_wiki_pages(question, "
    "category?) pour identifier la fiche pertinente, puis read_wiki_page("
    "category, slug) pour en lire le contenu — ou read_product_knowledge("
    "slug) si la fiche est dans le SQL canonique. Tu n'as droit qu'à un "
    "seul retry, ne le gâche pas."
)

PRODUCT_GUARDRAIL_HINT_SELECT_WITHOUT_READ = (
    "Tu as appelé select_wiki_pages mais pas read_wiki_page (ni "
    "read_product_knowledge) derrière. select_wiki_pages ne retourne "
    "que les titres et 3 questions preview — pas le contenu des fiches. "
    "Tu dois maintenant appeler read_wiki_page(category, slug) sur le "
    "candidat le plus pertinent (top-1 score) avant de composer ta "
    "réponse. Tu n'as droit qu'à un seul retry."
)


def _check_product_guardrail(tools_called: list[str]) -> Optional[str]:
    """Phase 2 wiki — vérifie qu'un turn agent `product` a consulté ses sources.

    Args:
        tools_called: liste ordonnée des noms de tools effectivement
            appelés pendant ce tour (avant la réponse finale).

    Returns:
        ``None`` si le tour est conforme (au moins un tool de lecture
        appelé). Sinon, un hint à injecter au LLM :

        - ``PRODUCT_GUARDRAIL_HINT_SELECT_WITHOUT_READ`` si
          ``select_wiki_pages`` a été appelé mais aucun read derrière.
        - ``PRODUCT_GUARDRAIL_HINT_NO_READ`` sinon (aucune lecture du
          tout).

    Note: ``ask_user_question`` et ``show_instrument_card`` ne sont pas
    des « lectures » au sens strict mais show_instrument_card retourne
    des données live (carte produit) qu'on considère équivalentes à une
    lecture. ``ask_user_question`` ne déclenche pas de réponse finale
    (il interrupt la boucle via ``interrupt_with_question``), donc le
    guard-rail ne le verra jamais en pratique.
    """
    has_read = any(t in PRODUCT_KNOWLEDGE_READ_TOOLS for t in tools_called)
    if has_read:
        return None
    if "select_wiki_pages" in tools_called:
        return PRODUCT_GUARDRAIL_HINT_SELECT_WITHOUT_READ
    return PRODUCT_GUARDRAIL_HINT_NO_READ


def _llm_error_is_retryable(exc: LLMError) -> bool:
    """Détermine si une `LLMError` correspond à un code HTTP transient.

    Les `LLMError` produites par `openai_client.chat_completion_with_tools`
    et `llm.chat_with_history` ont le format `f"upstream_status_{code}"`
    (cf. `services/assistance/llm.py` ligne 84). Toute autre forme
    (timeout, parse error, …) est considérée non-retryable.
    """
    msg = str(exc) or ""
    if not msg.startswith("upstream_status_"):
        return False
    code = msg.split("upstream_status_", 1)[1].strip()
    return code in LLM_RETRYABLE_UPSTREAM_CODES


async def _llm_call_with_retry(
    completion_fn: Any,
    *,
    messages: list[dict[str, Any]],
    model: str,
    tools: list[dict[str, Any]],
    temperature: float,
    agent_id: str,
    iteration: int,
) -> dict[str, Any]:
    """Wrapper retry-borné autour de `completion_fn`.

    - Retry seulement si l'exception est `LLMError` avec un code
      retryable (cf. `LLM_RETRYABLE_UPSTREAM_CODES`).
    - Backoff fixe selon `LLM_BACKOFF_SCHEDULE` (0.5s, 1.0s).
    - Au plus `LLM_MAX_RETRIES` tentatives supplémentaires (3 essais
      au total).
    - Pour toute autre exception (`LLMError` non-retryable, exception
      non-LLM, etc.) : pas de retry, on remonte direct.

    Logs `agent_loop.llm_retry agent=... iter=... attempt=... code=...`
    pour observabilité.
    """
    last_exc: Optional[LLMError] = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            return await asyncio.to_thread(
                completion_fn,
                messages,
                model=model,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
            )
        except LLMError as exc:
            last_exc = exc
            if attempt >= LLM_MAX_RETRIES or not _llm_error_is_retryable(exc):
                raise
            backoff = LLM_BACKOFF_SCHEDULE[
                min(attempt, len(LLM_BACKOFF_SCHEDULE) - 1)
            ]
            logger.warning(
                "agent_loop.llm_retry agent=%s iter=%d attempt=%d/%d "
                "exc=%s backoff=%.1fs",
                agent_id,
                iteration,
                attempt + 1,
                LLM_MAX_RETRIES,
                exc,
                backoff,
            )
            await asyncio.sleep(backoff)
    # Inatteignable mais filet de sécurité (mypy / défense en profondeur).
    if last_exc is not None:
        raise last_exc
    raise LLMError("upstream_unknown")


# ─────────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────────


def _build_initial_messages(
    *,
    system_prompt: str,
    agent_input: AgentInput,
) -> list[dict[str, Any]]:
    """Construit la liste de messages initiale pour le LLM.

    Schéma : `[system, ...recent_turns, user]`. La mémoire long-terme
    (`agent_input.memory_state`) est concaténée au system prompt si
    présente, pour rester compatible avec le format Phase 1 attendu par
    OpenAI.
    """
    messages: list[dict[str, Any]] = []

    sys_chunks = [system_prompt.strip()]
    mem = agent_input.memory_state or {}
    summary = mem.get("conversation_summary")
    if summary:
        sys_chunks.append("\n## Résumé conversation\n" + summary.strip())
    long_mem = mem.get("client_long_memory")
    if long_mem:
        sys_chunks.append(
            "\n## Mémoire long-terme client\n"
            + json.dumps(long_mem, ensure_ascii=False, indent=2)
        )
    messages.append({"role": "system", "content": "\n".join(sys_chunks)})

    for turn in agent_input.recent_turns or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": agent_input.user_message})
    return messages


def _filter_tools_by_autonomy(
    available: Sequence[ToolModule],
    *,
    autonomy_max: str,
) -> list[ToolModule]:
    """Garde uniquement les tools dont le `autonomy_level <= autonomy_max`."""
    out: list[ToolModule] = []
    for mod in available:
        spec_level = (mod.SPEC.get("autonomy_level") or "L0")  # type: ignore[union-attr]
        if autonomy_le(spec_level, autonomy_max):
            out.append(mod)
    return out


def _build_tool_index(modules: Sequence[ToolModule]) -> dict[str, ToolModule]:
    """Index `tool_name -> module` pour dispatch O(1)."""
    out: dict[str, ToolModule] = {}
    for mod in modules:
        name = (mod.SPEC.get("function") or {}).get("name")  # type: ignore[union-attr]
        if isinstance(name, str) and name:
            out[name] = mod
    return out


def _safe_parse_args(raw: Any) -> dict[str, Any]:
    """Parse les arguments d'un tool_call OpenAI (str JSON ou dict)."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


async def _execute_tool(
    module: ToolModule,
    *,
    ctx: ToolContext,
    args: dict[str, Any],
    timeout_seconds: int,
) -> tuple[dict[str, Any], int, Optional[str]]:
    """Exécute un tool en respectant le timeout. Retourne `(result, duration_ms, error_code)`.

    `error_code` est :
      - `None`           si succès,
      - `"timeout"`      si dépassement,
      - `"internal"`     si exception interne.
    """
    t0 = time.monotonic()
    try:
        raw = module.execute(ctx, **args)  # type: ignore[call-arg]
        if inspect.isawaitable(raw):
            raw = await asyncio.wait_for(raw, timeout=timeout_seconds)
        else:
            # fn synchrone : on l'a déjà appelée — pas de timeout async
            # à appliquer (les tools sync sont supposés rapides ; le
            # timeout LLM total reste une garde tertiaire).
            pass
    except asyncio.TimeoutError:
        duration = int((time.monotonic() - t0) * 1000)
        return {"error": "timeout"}, duration, "timeout"
    except Exception as exc:  # noqa: BLE001 — best-effort.
        duration = int((time.monotonic() - t0) * 1000)
        logger.exception(
            "agent_loop.tool_failed agent=%s tool=%s exc=%s",
            ctx.agent_id,
            (module.SPEC.get("function") or {}).get("name"),  # type: ignore[union-attr]
            exc,
        )
        return {"error": "internal_error"}, duration, "internal"

    duration = int((time.monotonic() - t0) * 1000)
    if not isinstance(raw, dict):
        # Tolérance : on enveloppe pour ne jamais planter le LLM.
        return {"value": raw}, duration, None
    return raw, duration, None


def _tool_result_message(
    tool_call_id: str, tool_name: str, result: dict[str, Any]
) -> dict[str, Any]:
    """Construit le message OpenAI `role: tool` à append à la conversation."""
    try:
        content = json.dumps(result, ensure_ascii=False, default=str)
    except Exception:
        content = json.dumps({"error": "result_unserializable"})
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content,
    }


# ─────────────────────────────────────────────────────────────────────────
# Point d'entrée principal
# ─────────────────────────────────────────────────────────────────────────


async def _run_consult_specialist(
    *,
    target_agent: str,
    question: str,
    agent_input: AgentInput,
    actor_kind: ActorKind,
    db: Session,
    conversation_id: UUID | str,
    user_id: int,
    correlation_id: str,
    chat_completion_fn: Any,
    chain_depth: int,
) -> tuple[str, int]:
    """Lance un sous-loop sandboxé sur `target_agent` pour une consultation.

    Capture le **texte final** émis par le specialist (concaténation des
    `delta`) et l'ignore pour les autres events (choices, error,
    thinking) — la consultation ne doit pas perturber l'UX du tour
    caller. Si le sous-loop échoue ou retourne vide, on retourne ``""``
    et le tool_result émet ``error: specialist_unavailable``.

    Returns:
        Tuple ``(specialist_text, duration_ms)``.
    """
    started = time.monotonic()
    try:
        sub_prompt = load_agent_system_prompt(target_agent)
        sub_tools = tools_registry.tools_for(target_agent)
        sub_input = AgentInput(
            user_message=question,
            recent_turns=[],  # specialist isolé du contexte caller
            memory_state={
                "client_id": (agent_input.memory_state or {}).get("client_id"),
                "person_id": (agent_input.memory_state or {}).get("person_id"),
            },
        )
        text_chunks: list[str] = []
        async for sub_event in run_agent_loop(
            agent_id=target_agent,
            system_prompt=sub_prompt,
            available_tools=sub_tools,
            agent_input=sub_input,
            actor_kind=actor_kind,
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            correlation_id=f"{correlation_id}:consult",
            chat_completion_fn=chat_completion_fn,
            chain_depth=chain_depth + 1,
            consult_in_progress=True,
        ):
            if sub_event.type == "delta" and sub_event.content:
                text_chunks.append(sub_event.content)
            # On ignore choices/thinking/error/done du sous-loop : ils
            # ne doivent pas remonter au client (le specialist répond
            # en backend, pas au client final).
        duration_ms = int((time.monotonic() - started) * 1000)
        return ("".join(text_chunks).strip(), duration_ms)
    except Exception:  # noqa: BLE001
        logger.exception(
            "agent_loop.consult_specialist sub_loop_failed target=%s",
            target_agent,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return ("", duration_ms)


def _filter_orchestration_tools(
    tools: Sequence[ToolModule],
    *,
    consult_in_progress: bool,
    handoff_done: bool,
) -> list[ToolModule]:
    """Retire les tools d'orchestration interdits selon le contexte.

    Phase 2c — règles :
      - Si on est en sous-loop `consult_in_progress=True` (specialist
        appelé via `consult_specialist`), on retire `consult_specialist`
        ET `handoff_to_agent` du toolset (profondeur 1, terminal).
      - Si un `handoff_to_agent` a déjà eu lieu dans le tour, on retire
        `handoff_to_agent` (max 1 par tour).
    """
    out: list[ToolModule] = []
    for mod in tools:
        name = (mod.SPEC.get("function") or {}).get("name")  # type: ignore[union-attr]
        if consult_in_progress and name in (
            "consult_specialist",
            "handoff_to_agent",
        ):
            continue
        if handoff_done and name == "handoff_to_agent":
            continue
        out.append(mod)
    return out


async def run_agent_loop(
    *,
    agent_id: str,
    system_prompt: str,
    available_tools: Sequence[ToolModule],
    agent_input: AgentInput,
    actor_kind: ActorKind,
    db: Session,
    conversation_id: UUID | str,
    user_id: int,
    correlation_id: Optional[str] = None,
    chat_completion_fn: Any = None,
    chain_depth: int = 0,
    consult_in_progress: bool = False,
) -> AsyncIterator[AgentEvent]:
    """Boucle agentique (cf. `MULTI_AGENTS_RUNTIME.md` § 1.0 et § 16).

    Args:
        agent_id        : identifiant agent (`"compliance"`, `"advisor"`,…).
        system_prompt   : prompt système (issu de `prompts/<agent>_system.md`).
        available_tools : modules-tools disponibles (avant filtrage autonomy).
        agent_input     : input métier (user_message + recent_turns + memory).
        actor_kind      : `CUSTOMER` | `ONBOARDING` | `ADMIN_BO` | `SUSPENDED`.
        db              : session SQLAlchemy ouverte.
        conversation_id : UUID de la conv (pour `agent_decisions`).
        user_id         : `admin_users.id` du caller.
        correlation_id  : ID de log/trace ; auto-généré si None.
        chat_completion_fn : injectable pour les tests (sinon
                             `chat_completion_with_tools` réel).
        chain_depth     : Phase 2c — profondeur de chaîne. ``0`` = appel
                          top-level depuis service.py. ``1`` = sous-loop
                          spawné par `consult_specialist`. > 1 interdit.
        consult_in_progress : Phase 2c — True quand cette boucle est un
                              sous-loop spécialiste. Filtre
                              `consult_specialist` et `handoff_to_agent`
                              du toolset (profondeur 1, terminal).

    Yields:
        `AgentEvent` (`started`, `delta`, `choices`, `done`, `error`).
        L'appelant doit consommer l'itérateur jusqu'au bout pour garantir
        que le row `agent_decisions` est bien flushé.
    """
    correlation_id = correlation_id or str(uuid4())[:8]
    audit_session_id = str(uuid4())
    started_at = time.monotonic()

    # ── Court-circuits acteurs (défense en profondeur — déjà filtrés
    # au niveau service mais on vérifie ici pour qu'aucun appel direct
    # au runtime ne contourne la sécurité).
    if actor_kind == ActorKind.ADMIN_BO:
        yield AgentEvent(
            type="error", error_code="actor_admin_bo_not_allowed"
        )
        return
    if actor_kind == ActorKind.SUSPENDED:
        # Pas d'erreur explicite : on délègue au caller (service.py)
        # qui connaît le texte standardisé. Mais on signale.
        yield AgentEvent(
            type="error", error_code="actor_suspended_short_circuit"
        )
        return

    # ── Setup tools ────────────────────────────────────────────────
    # `current_agent_id` peut être muté en cours de loop par le
    # dispatcher Compliance (cf. `_maybe_dispatch_subagent` plus bas)
    # ou par un `handoff_to_agent` (Phase 2c).
    current_agent_id = agent_id
    handoff_done = False  # Phase 2c — max 1 handoff par tour.
    consultations_count = 0  # Phase 2c — borne `MAX_CONSULTATIONS_PER_TOUR`.
    # Historique tools pour `tour_shared_context` (handoff cross-subagent).
    tools_history: list[tuple[str, dict[str, Any]]] = []
    # Chaîne d'agents traversés au top-level (top-level tour seulement).
    # En sous-loop consult, on ne tracke pas (le caller n'en a pas besoin
    # pour son audit — la consultation est traçée par `consultations`).
    agent_chain: list[str] = [current_agent_id] if chain_depth == 0 else []
    # Liste des consultations effectuées (pour message_payload metadata).
    consultations: list[dict[str, Any]] = []

    autonomy_max = assistance_agent_autonomy_max(current_agent_id)
    gated_tools = _filter_tools_by_autonomy(
        available_tools, autonomy_max=autonomy_max
    )
    gated_tools = _filter_orchestration_tools(
        gated_tools,
        consult_in_progress=consult_in_progress,
        handoff_done=handoff_done,
    )
    tool_index = _build_tool_index(gated_tools)
    openai_tools = [to_openai_tool(m.SPEC) for m in gated_tools]  # type: ignore[arg-type]

    messages = _build_initial_messages(
        system_prompt=system_prompt, agent_input=agent_input
    )

    max_iter = assistance_agent_max_iter()
    timeout_total = assistance_agent_timeout_seconds()
    tool_timeout = assistance_tool_timeout_seconds()
    model = assistance_agent_model(current_agent_id)
    temperature = assistance_agent_temperature(current_agent_id, default=0.5)

    completion_fn = chat_completion_fn or chat_completion_with_tools

    tools_called: list[str] = []
    decision_ids: list[str] = []
    interrupt_with_choices: Optional[dict[str, Any]] = None
    early_break_reason: Optional[str] = None
    subagent_dispatched: Optional[str] = None
    # Phase 2 wiki — guard-rail product agent. Cf. _check_product_guardrail.
    # Borné à 1 retry par tour pour éviter les boucles infinies si gpt-4o-mini
    # ignore le hint (cas rare mais théoriquement possible).
    product_guardrail_retry_done = False
    # Phase 2c.2 — Embeds UI structurés produits par les tools (cf.
    # `ToolContext.embeds_to_emit`). On dédoublonne sur la clé naturelle
    # `(type, transaction_id|slug|...)` pour qu'un même tool appelé
    # plusieurs fois ne génère pas N cartes identiques. Inclus dans le
    # `done` event final (top-level uniquement, comme `agent_chain`).
    embeds_collected: list[dict[str, Any]] = []
    embeds_seen_keys: set[tuple[str, str]] = set()

    thinking_enabled = (
        assistance_stream_thinking_enabled() and not consult_in_progress
    )

    # SSE thinking event Phase 2b — UX pour latence du diagnose.
    # Émis seulement pour l'entry-point compliance (top-level dispatcher).
    if current_agent_id == "compliance" and thinking_enabled:
        yield AgentEvent(
            type="thinking",
            thinking_phase="diagnose",
            thinking_agent="compliance",
        )

    yield AgentEvent(type="delta", content="")  # warm-up event (compat)

    for iteration in range(max_iter):
        if time.monotonic() - started_at > timeout_total:
            early_break_reason = "timeout"
            yield AgentEvent(type="error", error_code="agent_timeout")
            break

        # ── Appel LLM (sync sous-jacent, retry borné sur 5xx/429) ──
        try:
            message = await _llm_call_with_retry(
                completion_fn,
                messages=messages,
                model=model,
                tools=openai_tools,
                temperature=temperature,
                agent_id=current_agent_id,
                iteration=iteration,
            )
        except LLMError as exc:
            logger.warning(
                "agent_loop.llm_error agent=%s iter=%d exc=%s",
                current_agent_id,
                iteration,
                exc,
            )
            early_break_reason = "llm_error"
            yield AgentEvent(type="error", error_code="llm_unavailable")
            break

        tool_calls = (message or {}).get("tool_calls") or []

        if tool_calls:
            # Append d'abord le message assistant tel quel (avec tool_calls).
            messages.append({
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": tool_calls,
            })

            for call in tool_calls:
                fn_block = (call or {}).get("function") or {}
                tool_name = fn_block.get("name") or ""
                call_id = call.get("id") or f"call_{iteration}_{len(tools_called)}"
                args = _safe_parse_args(fn_block.get("arguments"))

                module = tool_index.get(tool_name)
                if module is None:
                    logger.warning(
                        "agent_loop.tool_not_found agent=%s name=%r",
                        current_agent_id,
                        tool_name,
                    )
                    messages.append(
                        _tool_result_message(
                            call_id,
                            tool_name or "unknown",
                            {"error": "tool_not_found"},
                        )
                    )
                    decision_id = audit.persist_decision(
                        db,
                        conversation_id=conversation_id,
                        agent_id=current_agent_id,
                        iteration=iteration,
                        tool_name=tool_name or "unknown",
                        autonomy_level="L0",
                        arguments=args,
                        result_summary={"error": "tool_not_found"},
                        error_code="tool_not_found",
                        correlation_id=correlation_id,
                    )
                    if decision_id:
                        decision_ids.append(decision_id)
                    continue

                memory_state = agent_input.memory_state or {}
                ctx = ToolContext(
                    db=db,
                    client_id=str(memory_state.get("client_id"))
                    if memory_state.get("client_id")
                    else None,
                    person_id=str(memory_state.get("person_id"))
                    if memory_state.get("person_id")
                    else None,
                    user_id=user_id,
                    actor_kind=actor_kind,
                    agent_id=current_agent_id,
                    conversation_id=str(conversation_id),
                    iteration=iteration,
                    audit_session_id=audit_session_id,
                    correlation_id=correlation_id,
                )

                result, duration_ms, error_code = await _execute_tool(
                    module,
                    ctx=ctx,
                    args=args,
                    timeout_seconds=tool_timeout,
                )
                tools_called.append(tool_name)
                spec_level = (module.SPEC.get("autonomy_level") or "L0")  # type: ignore[union-attr]

                decision_id = audit.persist_decision(
                    db,
                    conversation_id=conversation_id,
                    agent_id=current_agent_id,
                    iteration=iteration,
                    tool_name=tool_name,
                    autonomy_level=spec_level,
                    arguments=args,
                    result_summary=audit.result_summary(result),
                    duration_ms=duration_ms,
                    error_code=error_code,
                    correlation_id=correlation_id,
                )
                if decision_id:
                    decision_ids.append(decision_id)

                # Track tools_history (pour `tour_shared_context` sur
                # handoff). On exclut les tools d'orchestration et les
                # erreurs (pas de valeur métier à partager).
                if tool_name not in (
                    "consult_specialist",
                    "handoff_to_agent",
                ) and isinstance(result, dict):
                    tools_history.append((tool_name, result))

                # Phase 2c.2 — Collecte des embeds UI produits par le tool.
                # On dédoublonne sur (type, identifiant naturel) pour
                # qu'un re-call du même tool sur la même entité ne crée
                # pas de doublon visuel côté Flutter. La clé d'unicité
                # par défaut est (type, transaction_id|slug|id|key).
                for emb in list(ctx.embeds_to_emit):
                    if not isinstance(emb, dict):
                        continue
                    emb_type = str(emb.get("type") or "").strip()
                    if not emb_type:
                        continue
                    emb_key_value = (
                        str(emb.get("transaction_id") or "")
                        or str(emb.get("slug") or "")
                        or str(emb.get("id") or "")
                        or str(emb.get("key") or "")
                    )
                    dedup_key = (emb_type, emb_key_value)
                    if dedup_key in embeds_seen_keys:
                        continue
                    embeds_seen_keys.add(dedup_key)
                    embeds_collected.append(emb)

                if result.get("interrupt_with_question"):
                    interrupt_with_choices = result
                    # On append quand même un tool_result minimal
                    # (sinon le LLM pourrait être confus si on reprend
                    # la conversation plus tard avec le même historique).
                    messages.append(
                        _tool_result_message(
                            call_id,
                            tool_name,
                            {"status": "interrupt_pending_user"},
                        )
                    )
                    break

                # ── Phase 2c : consult_specialist (sous-loop) ───────
                # Le tool a validé purpose+params et signalé l'intention.
                # On lance un sous-runtime sandboxé sur le target,
                # capture le texte, et l'injecte au LLM caller.
                if result.get("interrupt_with_consult"):
                    target_agent = str(result.get("target_agent") or "")
                    purpose = str(result.get("purpose") or "")
                    question = str(result.get("question") or "")
                    consult_params = result.get("params") or {}

                    # Garde-fous chain depth + nb max consultations.
                    if chain_depth >= MAX_CHAIN_DEPTH:
                        messages.append(
                            _tool_result_message(
                                call_id,
                                tool_name,
                                {
                                    "error": "chain_depth_exceeded",
                                    "max": MAX_CHAIN_DEPTH,
                                },
                            )
                        )
                        continue
                    if (
                        consultations_count
                        >= MAX_CONSULTATIONS_PER_TOUR
                    ):
                        messages.append(
                            _tool_result_message(
                                call_id,
                                tool_name,
                                {
                                    "error": "consult_limit_reached",
                                    "max": MAX_CONSULTATIONS_PER_TOUR,
                                },
                            )
                        )
                        continue

                    if thinking_enabled:
                        yield AgentEvent(
                            type="thinking",
                            thinking_phase=f"consult:{purpose}",
                            thinking_agent=target_agent,
                        )

                    consult_text, consult_duration_ms = (
                        await _run_consult_specialist(
                            target_agent=target_agent,
                            question=question,
                            agent_input=agent_input,
                            actor_kind=actor_kind,
                            db=db,
                            conversation_id=conversation_id,
                            user_id=user_id,
                            correlation_id=correlation_id,
                            chat_completion_fn=chat_completion_fn,
                            chain_depth=chain_depth,
                        )
                    )
                    consultations_count += 1
                    consultations.append(
                        {
                            "target": target_agent,
                            "purpose": purpose,
                            "params": consult_params,
                            "duration_ms": consult_duration_ms,
                            "ok": bool(consult_text.strip()),
                        }
                    )

                    if consult_text.strip():
                        injected = {
                            "specialist_target": target_agent,
                            "specialist_purpose": purpose,
                            "specialist_text": consult_text.strip(),
                            "duration_ms": consult_duration_ms,
                        }
                    else:
                        injected = {
                            "specialist_target": target_agent,
                            "specialist_purpose": purpose,
                            "error": "specialist_unavailable",
                            "duration_ms": consult_duration_ms,
                        }
                    messages.append(
                        _tool_result_message(call_id, tool_name, injected)
                    )
                    continue

                # ── Phase 2c : handoff_to_agent (switch sub-agent) ──
                if result.get("interrupt_with_handoff"):
                    target_agent = str(result.get("target_agent") or "")
                    handoff_reason = str(result.get("reason") or "")

                    # Garde-fous : pas de handoff en mode consult, max 1
                    # handoff par tour.
                    if consult_in_progress:
                        messages.append(
                            _tool_result_message(
                                call_id,
                                tool_name,
                                {"error": "handoff_not_allowed_in_consult"},
                            )
                        )
                        continue
                    if handoff_done:
                        messages.append(
                            _tool_result_message(
                                call_id,
                                tool_name,
                                {"error": "handoff_already_done"},
                            )
                        )
                        continue

                    # Précondition d'investigation (le caller doit avoir
                    # appelé suffisamment de tools L0 read avant).
                    investigation_ok, missing_hint = (
                        handoff_to_agent_tool.investigation_done(
                            source_agent=current_agent_id,
                            tools_called=tools_called,
                        )
                    )
                    if not investigation_ok:
                        messages.append(
                            _tool_result_message(
                                call_id,
                                tool_name,
                                {
                                    "error": "investigation_incomplete",
                                    "tools_to_consider": missing_hint,
                                    "tip": (
                                        "Appelle au moins 2 tools de "
                                        "lecture (read_documents, "
                                        "read_external_aml_signals, "
                                        "read_compliance_state, "
                                        "read_transactions) avant "
                                        "handoff."
                                    ),
                                },
                            )
                        )
                        continue

                    if thinking_enabled:
                        yield AgentEvent(
                            type="thinking",
                            thinking_phase=f"handoff:{handoff_reason}",
                            thinking_agent=target_agent,
                        )

                    logger.info(
                        "agent_loop.handoff source=%s target=%s "
                        "reason=%s conv=%s",
                        current_agent_id,
                        target_agent,
                        handoff_reason,
                        conversation_id,
                    )

                    # Inject tool_result OK pour cohérence historique LLM.
                    messages.append(
                        _tool_result_message(
                            call_id,
                            tool_name,
                            {
                                "status": "handoff_ok",
                                "target_agent": target_agent,
                            },
                        )
                    )

                    # Switch agent + reload prompt+tools+context.
                    current_agent_id = target_agent
                    handoff_done = True
                    if target_agent not in agent_chain:
                        agent_chain.append(target_agent)

                    new_system_prompt = load_agent_system_prompt(
                        target_agent
                    )
                    shared_block = tour_shared_context.format_for_prompt(
                        tour_shared_context.aggregate_tour_context(
                            tools_history
                        )
                    )
                    if shared_block:
                        new_system_prompt = (
                            f"{new_system_prompt}\n\n{shared_block}"
                        )

                    new_available = tools_registry.tools_for(target_agent)
                    new_autonomy = assistance_agent_autonomy_max(
                        target_agent
                    )
                    new_gated = _filter_tools_by_autonomy(
                        new_available, autonomy_max=new_autonomy
                    )
                    new_gated = _filter_orchestration_tools(
                        new_gated,
                        consult_in_progress=consult_in_progress,
                        handoff_done=handoff_done,
                    )
                    tool_index = _build_tool_index(new_gated)
                    openai_tools = [
                        to_openai_tool(m.SPEC) for m in new_gated  # type: ignore[arg-type]
                    ]
                    if messages and messages[0].get("role") == "system":
                        new_initial = _build_initial_messages(
                            system_prompt=new_system_prompt,
                            agent_input=agent_input,
                        )
                        messages[0] = new_initial[0]

                    model = assistance_agent_model(target_agent)
                    temperature = assistance_agent_temperature(
                        target_agent, default=0.5
                    )
                    continue

                # ── Cas standard : append tool result tel quel ──────
                messages.append(
                    _tool_result_message(call_id, tool_name, result)
                )

                # ── Phase 2b : Compliance dispatcher ────────────────
                # Si on est sur l'entry-point `compliance` et que le LLM
                # vient d'appeler `diagnose_compliance_topic`, on switche
                # vers le sub-agent topique pour la suite de la boucle.
                if (
                    current_agent_id == "compliance"
                    and tool_name == "diagnose_compliance_topic"
                    and isinstance(result, dict)
                    and result.get("dominant_topic")
                ):
                    new_agent_id = tools_registry.compliance_subagent_id(
                        str(result.get("dominant_topic"))
                    )
                    logger.info(
                        "agent_loop.compliance_dispatch from=%s to=%s "
                        "topic=%s confidence=%.2f conv=%s",
                        current_agent_id,
                        new_agent_id,
                        result.get("dominant_topic"),
                        float(result.get("confidence") or 0.0),
                        conversation_id,
                    )
                    current_agent_id = new_agent_id
                    subagent_dispatched = new_agent_id
                    if new_agent_id not in agent_chain:
                        agent_chain.append(new_agent_id)

                    # Reload prompt + tools pour le sub-agent.
                    new_system_prompt = load_agent_system_prompt(new_agent_id)
                    new_available_tools = tools_registry.tools_for(new_agent_id)
                    new_autonomy_max = assistance_agent_autonomy_max(
                        new_agent_id
                    )
                    new_gated = _filter_tools_by_autonomy(
                        new_available_tools, autonomy_max=new_autonomy_max
                    )
                    new_gated = _filter_orchestration_tools(
                        new_gated,
                        consult_in_progress=consult_in_progress,
                        handoff_done=handoff_done,
                    )
                    tool_index = _build_tool_index(new_gated)
                    openai_tools = [
                        to_openai_tool(m.SPEC) for m in new_gated  # type: ignore[arg-type]
                    ]
                    # Remplace le system prompt en tête (messages[0] est
                    # toujours le système, par construction).
                    if messages and messages[0].get("role") == "system":
                        # Préserve la mémoire long-terme déjà concaténée
                        # par `_build_initial_messages` (postfixée avec des
                        # ## headers). On la préserve en re-construisant
                        # via le helper.
                        new_messages_initial = _build_initial_messages(
                            system_prompt=new_system_prompt,
                            agent_input=agent_input,
                        )
                        messages[0] = new_messages_initial[0]

                    # Ajuste model + temperature si surchargés pour ce sub-agent.
                    model = assistance_agent_model(new_agent_id)
                    temperature = assistance_agent_temperature(
                        new_agent_id, default=0.5
                    )

            if interrupt_with_choices is not None:
                early_break_reason = "choices_emitted"
                opts_raw = interrupt_with_choices.get("options") or []
                options: list[ChoiceOption] = []
                for o in opts_raw:
                    if not isinstance(o, dict):
                        continue
                    oid = o.get("id")
                    olabel = o.get("label")
                    if not oid or not olabel:
                        continue
                    options.append(
                        ChoiceOption(
                            id=str(oid),
                            label=str(olabel),
                            agent_hint=(
                                str(o["agent_hint"])
                                if o.get("agent_hint")
                                else None
                            ),
                            deep_link=(
                                str(o["deep_link"])
                                if o.get("deep_link")
                                else None
                            ),
                        )
                    )
                yield AgentEvent(
                    type="choices",
                    prompt=str(interrupt_with_choices.get("prompt") or "")[:240],
                    options=options,
                    allow_freeform=bool(
                        interrupt_with_choices.get("allow_freeform", True)
                    ),
                )
                break

            # Continuer la boucle pour laisser le LLM raisonner sur les résultats.
            continue

        # ── Pas de tool_calls → réponse finale ────────────────────
        content = (message or {}).get("content") or ""

        # ── Phase 2 wiki — guard-rail product agent ────────────────
        # Si l'agent `product` arrive ici sans avoir appelé un tool de
        # lecture, on injecte un hint system et on rejoue la boucle
        # **une seule fois**. Voir `_check_product_guardrail` et la
        # config `assistance_product_guardrail_enabled()`.
        # Ne s'applique pas en sous-loop consult (un specialist peut
        # légitimement répondre depuis son seul prompt sur des
        # questions purement définitionnelles).
        if (
            current_agent_id == "product"
            and not product_guardrail_retry_done
            and not consult_in_progress
            and assistance_product_guardrail_enabled()
        ):
            guardrail_hint = _check_product_guardrail(tools_called)
            if guardrail_hint is not None:
                logger.warning(
                    "agent_loop.product_guardrail_triggered iter=%d "
                    "tools_called=%s reason=%s conv=%s corr=%s",
                    iteration,
                    ",".join(tools_called) or "-",
                    (
                        "select_without_read"
                        if "select_wiki_pages" in tools_called
                        else "no_read"
                    ),
                    conversation_id,
                    correlation_id,
                )
                # Append le brouillon assistant + le hint system, puis
                # `continue` pour relancer le LLM avec le contexte enrichi.
                # On garde le brouillon dans l'historique pour que le LLM
                # voie ce qu'il a tenté de répondre (et pourquoi c'est
                # rejeté), c'est plus efficace pédagogiquement qu'un
                # simple message d'erreur abstrait.
                messages.append({
                    "role": "assistant",
                    "content": content or "(réponse vide)",
                })
                messages.append({
                    "role": "system",
                    "content": guardrail_hint,
                })
                product_guardrail_retry_done = True
                continue

        if not content.strip():
            content = MAX_ITER_FALLBACK_MESSAGE
        yield AgentEvent(type="delta", content=content)
        early_break_reason = "final_answer"
        break
    else:
        # Boucle terminée sans break (= MAX_ITER atteint)
        early_break_reason = "max_iter"
        yield AgentEvent(type="delta", content=MAX_ITER_FALLBACK_MESSAGE)

    duration_total_ms = int((time.monotonic() - started_at) * 1000)
    logger.info(
        "agent_loop.tour_done agent=%s subagent=%s iter=%d tools=%s "
        "duration_ms=%d decisions=%d reason=%s chain=%s consults=%d "
        "corr=%s",
        agent_id,
        subagent_dispatched or "-",
        iteration + 1 if "iteration" in dir() else 0,
        ",".join(tools_called) or "-",
        duration_total_ms,
        len(decision_ids),
        early_break_reason,
        ">".join(agent_chain) if agent_chain else "-",
        consultations_count,
        correlation_id,
    )

    # En sous-loop consult, on n'émet pas agent_chain/consultations/embeds
    # (le caller top-level les portera dans son propre done event).
    final_chain = (
        agent_chain
        if (chain_depth == 0 and len(agent_chain) > 1)
        else None
    )
    final_consultations = (
        consultations
        if (chain_depth == 0 and consultations)
        else None
    )
    final_embeds = (
        embeds_collected
        if (chain_depth == 0 and embeds_collected)
        else None
    )

    yield AgentEvent(
        type="done",
        completed=True,
        final_agent_id=(
            current_agent_id if current_agent_id != agent_id else None
        ),
        agent_chain=final_chain,
        consultations=final_consultations,
        embeds=final_embeds,
    )

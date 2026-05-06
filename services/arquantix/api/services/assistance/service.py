"""Logique métier Assistance : conversation lookup/create + persistence + LLM.

Le flux d'un tour :
1. Vérifier conversation existante (FK client) ou en créer une (titre auto).
2. Insérer le message `user` (turn_index = next).
3. Reconstituer l'historique (limité à `assistance_history_max_turns`) et appeler OpenAI.
4. Insérer la réponse `assistant` (turn_index + 1).
5. Mettre à jour `last_message_at` + `updated_at`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import AssistanceConversation, AssistanceMessage
from services.assistance import memory as assistance_memory
from services.assistance import conversation_topic as assistance_conversation_topic
from services.assistance import router_hot_path as assistance_router_hot_path
from services.assistance.agents import router as agent_router
from services.assistance.agents.base import (
    AGENT_DEFAULT_ID,
    AGENT_ROUTER_ID,
    KNOWN_AGENT_IDS,
    RESUME_TOPIC_HINT_ID,
    AgentInput,
    ChoiceOption,
    RouterDecision,
)
from services.assistance.agents.cognitive_state import (
    CognitiveState,
    compute_cognitive_state,
)
from services.assistance.agents.conversation_objective import (
    compute_objective,
)
from services.assistance.agents import client_discovery as discovery_engine
from services.assistance.agents.conversation_continuity import (
    build_previous_bot_context_block,
    decide_auto_qcm,
)
from services.assistance import client_discovery_repo as discovery_repo
from services.assistance.agents.config import (
    assistance_multi_agent_enabled,
    assistance_router_confidence_min,
    assistance_runtime_loop_agents,
    assistance_runtime_loop_enabled,
)
from services.assistance.agents.prompt_builder import load_agent_system_prompt
from services.assistance.agents.registry import get_agent
from services.assistance.agents.runtime import run_agent_loop
from services.assistance.agents.runtime.product_slack_pipeline import (
    iter_product_slack_pipeline_events,
    should_use_slack_pipeline,
)
from services.assistance.agents.tools import registry as tools_registry
from services.assistance.agents.tools.shared.classify_actor import ActorKind
from services.assistance.config import assistance_history_max_turns
from services.assistance.llm import LLMError, chat_markdown, chat_markdown_stream

logger = logging.getLogger(__name__)


# Option spéciale ajoutée systématiquement à tous les QCM "choices" :
# permet à l'utilisateur de dire « rien de tout ça, je reformule »
# (cf. docs/arquantix/MULTI_AGENTS.md § 1.9).
_FREEFORM_CHOICE_ID = "freeform"
_FREEFORM_CHOICE_LABEL = "Rien de tout ça — je reformule"


# ── Phase 2a — Court-circuit SUSPENDED (anti-tipping-off) ───────────────────
# Réponse standardisée renvoyée à un acteur classifié comme `SUSPENDED`
# (login_frozen=true ou account_state ∈ {PARTIAL, BLOCKED}).
#
# Règles de rédaction (cf. `MULTI_AGENTS_RUNTIME.md` § 6 — Sécurité tipping-off
# matérielle) :
#   - Ne JAMAIS dire « votre compte est suspendu / bloqué / gelé / sous
#     enquête / soupçonné », ni mentionner « sécurité », « AML », « KYC »,
#     « fraude », « risque » → ces termes peuvent confirmer à un client
#     malveillant qu'une investigation est en cours.
#   - Texte neutre, factuel, qui renvoie l'utilisateur vers le canal humain
#     (support). Aucun signal ne doit pouvoir être inféré sur l'état
#     interne du dossier.
#   - Le détail de la raison reste tracé côté serveur (logs structurés +
#     futur row `assistance_agent_decisions` Phase 2c).
SUSPENDED_RESPONSE_TEXT = (
    "Pour le moment, l'assistant n'est pas en mesure de traiter votre demande. "
    "Notre équipe support reste à votre disposition via la rubrique « Aide » "
    "de l'application pour vous accompagner."
)
_SUSPENDED_AGENT_USED = "default"
_SUSPENDED_PAYLOAD_REASON = "suspended_short_circuit"


# ── Palier 2 D.2 — Consolidation mémoire async ─────────────────────────────
# Garde une référence aux tâches de consolidation en cours pour éviter
# qu'asyncio les garbage-collecte avant la fin
# (cf. https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task).
# Set module-level — ne nécessite aucun cleanup explicite (les tâches se
# discardent automatiquement via add_done_callback).
_running_consolidations: set[asyncio.Task] = set()


def _schedule_consolidation(session_factory, conversation_id: UUID) -> None:
    """Lance la consolidation mémoire en arrière-plan (Palier 2 D.2).

    Best-effort, hors hot path : appelée APRÈS l'émission du `done` SSE,
    donc 0 latence perçue côté client. Toute erreur reste contenue dans
    `assistance_memory.consolidate_conversation` (logguée, jamais
    propagée). Si l'event loop n'est pas disponible (cas pathologique),
    on log et on abandonne ; la consolidation sera retentée au prochain
    `done`.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "no running loop to schedule consolidation conv=%s",
            conversation_id,
        )
        return
    task = loop.create_task(
        assistance_memory.consolidate_conversation(
            session_factory=session_factory,
            conversation_id=conversation_id,
        )
    )
    _running_consolidations.add(task)
    task.add_done_callback(_running_consolidations.discard)


def _generate_title(content: str, *, max_words: int = 6, max_chars: int = 80) -> str:
    """Titre auto = N premiers mots du premier message utilisateur (fallback gratuit).

    Évite l'appel OpenAI dédié pour le MVP. Si l'utilisateur veut un titre
    LLM-généré plus tard, on le branchera dans une étape séparée.
    """
    text = " ".join((content or "").split())
    if not text:
        return "Conversation"
    words = text.split(" ")
    short = " ".join(words[:max_words])
    if len(short) > max_chars:
        short = short[: max_chars - 1].rstrip() + "…"
    return short


def _next_turn_index(db: Session, conversation_id: UUID) -> int:
    last = (
        db.query(AssistanceMessage.turn_index)
        .filter(AssistanceMessage.conversation_id == conversation_id)
        .order_by(desc(AssistanceMessage.turn_index))
        .limit(1)
        .scalar()
    )
    return (last or 0) + 1


def _safe_get_current_topic(
    db: Session | None, conversation_id: UUID | str | None
) -> dict | None:
    """Lit le slot `current_topic` côté DB, defensive (jamais d'exception
    remontée). Retourne `None` si la colonne n'existe pas encore (migration
    150 pas appliquée — utile pour les tests qui n'utilisent pas de DB).

    Cf. `services.assistance.conversation_topic.get_topic`.
    """
    if db is None or conversation_id is None:
        return None
    try:
        return assistance_conversation_topic.get_topic(db, conversation_id)
    except Exception:  # noqa: BLE001 — never let a memory read kill a turn
        logger.exception(
            "assistance.topic.read_failed conv=%s", conversation_id
        )
        return None


def _decision_kind_label(decision: RouterDecision) -> str:
    """Mappe une `RouterDecision` vers son label de décision canonique.

    Utilisé à 2 endroits :
      * inférence du ``conversation_stage`` (cf.
        ``cognitive_state.infer_conversation_stage``) ;
      * persistance dans ``assistance_agent_decisions`` (cf.
        ``_persist_router_decision``).

    Centralise la logique pour garantir la cohérence des deux usages.
    """
    if decision.redirect_bridge:
        return "redirect_off_topic"
    if decision.fallback_choices and not decision.is_decisive:
        return "ask_clarification"
    return "route_to"


def _safe_load_previous_cognitive_state(
    db: Session | None, conversation_id: UUID | str | None
) -> dict | None:
    """Lit le ``cognitive_state`` du tour précédent depuis
    ``assistance_agent_decisions``.

    Cherche la dernière entrée ``router_classify`` pour cette
    conversation (ordre ``created_at desc``) et extrait son
    ``arguments_json["cognitive_state"]``.

    Defensive — jamais d'exception remontée :
      * ``None`` si pas d'historique (premier tour),
      * ``None`` si l'entrée n'a pas de cognitive_state (legacy <
        Cognitive Bot v4),
      * ``None`` en cas d'erreur DB (best-effort, on dégrade vers un
        état neutre démarrage).
    """
    if db is None or conversation_id is None:
        return None
    try:
        from database import AssistanceAgentDecision

        row = (
            db.query(AssistanceAgentDecision)
            .filter(
                AssistanceAgentDecision.conversation_id == conversation_id,
                AssistanceAgentDecision.tool_name == "router_classify",
            )
            .order_by(AssistanceAgentDecision.created_at.desc())
            .first()
        )
        if row is None:
            return None
        args = row.arguments_json or {}
        if not isinstance(args, dict):
            return None
        prev = args.get("cognitive_state")
        return prev if isinstance(prev, dict) else None
    except Exception:  # noqa: BLE001 — best-effort, never kill a turn
        logger.exception(
            "assistance.cognitive_state.read_failed conv=%s",
            conversation_id,
        )
        return None


def _load_history(
    db: Session, conversation_id: UUID, *, limit: int
) -> list[dict]:
    """Renvoie les ``limit`` derniers messages dans l'ordre chronologique.

    Phase 2 wiki v1.4 patch : on expose aussi `agent_used` pour permettre
    au hot-path router (`router_hot_path.py`) d'identifier l'auteur du
    dernier message assistant. Champ absent / NULL pour les conv legacy
    pré-migration 147 → désactive naturellement le hot-path.
    """
    rows = (
        db.query(AssistanceMessage)
        .filter(AssistanceMessage.conversation_id == conversation_id)
        .order_by(AssistanceMessage.turn_index.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {
            "role": r.role,
            "content": r.content,
            "agent_used": r.agent_used,
        }
        for r in rows
    ]


def _build_context(
    db: Session,
    conv: AssistanceConversation,
) -> list[dict]:
    """Assemble le contexte LLM pour un tour streaming (Palier 2 D.2).

    Construit un payload « contexte enrichi » :
      [optional system memory block + K derniers tours bruts]

    Comportement gracieux :
      - Si la conv n'a **pas encore** de `conversation_summary` ET le
        client n'a pas de `assistance_long_memory` (cas des conv courtes,
        ou avant la première consolidation) → équivalent à
        `_load_history(limit=K)`. **Backward-compatible Palier 1.**
      - Si l'un ou l'autre existe → un message `system` supplémentaire
        est préfixé pour informer le LLM du contexte client + résumé.

    K = `ASSISTANCE_RECENT_TURNS_KEPT` (défaut 8). Au-delà, l'historique
    plus ancien est compressé dans `conversation_summary` et n'est plus
    réinjecté brut → c'est exactement le contrat du rolling summary.
    """
    state = assistance_memory.load_memory_state(db, conv.id)
    if state is None:
        return []

    recent = _load_history(
        db,
        conv.id,
        limit=assistance_memory.assistance_recent_turns_kept(),
    )

    return assistance_memory.build_context(
        summary=state.conversation_summary,
        client_long_memory=state.client_long_memory,
        recent_turns=recent,
    )


def get_conversation_for_client(
    db: Session, *, client_id: UUID, conversation_id: UUID
) -> Optional[AssistanceConversation]:
    """Retourne la conversation **uniquement** si elle appartient au client."""
    return (
        db.query(AssistanceConversation)
        .filter(
            AssistanceConversation.id == conversation_id,
            AssistanceConversation.client_id == client_id,
        )
        .one_or_none()
    )


def list_conversations_for_client(
    db: Session,
    *,
    client_id: UUID,
    status: Optional[str] = None,
    limit: int,
    before: Optional[datetime] = None,
) -> list[AssistanceConversation]:
    """Conversations d'un client triées par activité décroissante (D.1.4).

    Tri sur `last_message_at` quand il est défini, fallback sur `created_at`
    (cas exceptionnel d'une conversation créée mais sans tour). On utilise
    `coalesce(last_message_at, created_at)` pour garantir un ordre stable
    même sur des conversations vides.

    `before` permet une pagination cursor-based : passer le `last_message_at`
    de la dernière conversation reçue pour récupérer les suivantes.
    """
    from sqlalchemy import func

    sort_col = func.coalesce(
        AssistanceConversation.last_message_at,
        AssistanceConversation.created_at,
    )
    q = db.query(AssistanceConversation).filter(
        AssistanceConversation.client_id == client_id,
    )
    if status is not None:
        q = q.filter(AssistanceConversation.status == status)
    if before is not None:
        q = q.filter(sort_col < before)
    q = q.order_by(sort_col.desc(), AssistanceConversation.id.desc()).limit(limit)
    return q.all()


def list_messages_for_client(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: UUID,
    limit: int,
) -> tuple[AssistanceConversation, list[AssistanceMessage]]:
    """Charge l'historique d'une conversation (D.1.6) en vérifiant l'appartenance.

    Retourne `(conversation, messages_chronologiques)` ; lève
    `ValueError("conversation_not_found")` si la conversation n'existe pas
    ou n'appartient pas au client. Les messages sont triés par `turn_index`
    ASC pour permettre un append direct dans la liste UI.

    Pour limiter la mémoire on prend les ``limit`` **derniers** tours
    (turn_index DESC + reverse), car l'utilisateur s'intéresse en priorité
    à la fin du fil.
    """
    conv = get_conversation_for_client(
        db, client_id=client_id, conversation_id=conversation_id
    )
    if conv is None:
        raise ValueError("conversation_not_found")

    rows = (
        db.query(AssistanceMessage)
        .filter(AssistanceMessage.conversation_id == conv.id)
        .order_by(AssistanceMessage.turn_index.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    # D.1.4.2 — pas d'effet de bord ici : la mise à jour de `last_read_at`
    # est désormais déclenchée par un appel client explicite
    # `POST /conversations/{id}/read` (cf. mark_conversation_read).
    return conv, rows


def create_conversation(
    db: Session, *, client_id: UUID, first_user_content: str
) -> AssistanceConversation:
    conv = AssistanceConversation(
        id=uuid4(),
        client_id=client_id,
        title=_generate_title(first_user_content),
        status="active",
    )
    db.add(conv)
    db.flush()
    return conv


def process_chat_turn(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: Optional[UUID],
    user_content: str,
) -> tuple[AssistanceConversation, AssistanceMessage]:
    """Traite un tour : crée/charge la conversation, persiste user, appelle LLM, persiste assistant.

    Lève :
    - `ValueError("conversation_not_found")` si l'ID est fourni mais ne match pas le client.
    - `ValueError("conversation_closed")` si la conversation est marquée close.
    - `LLMError(...)` si l'appel OpenAI échoue (le user message reste persisté).
    """
    # D.1.4.4 — COMMIT ANTICIPÉ (UX optimiste) ───────────────────────────
    # On persiste la conversation + le message user AVANT l'appel LLM
    # (qui peut prendre 5 à 30 s avec OpenAI). Ainsi, si l'utilisateur
    # navigue vers la liste « Mes conversations » pendant l'attente :
    #  - la conversation y apparaît immédiatement (`GET /conversations`)
    #  - en tapant dessus, l'historique montre déjà son message user
    #    (`GET /conversations/{id}/messages`)
    #
    # `last_message_at` reflète l'activité user. `last_assistant_message_at`
    # reste `NULL` tant que la réponse n'est pas arrivée → pas de pastille
    # « non lu » prématurée. La conv ne pourra remonter unread qu'après
    # le second commit (insertion du message assistant).
    conv, _user_msg, user_idx = _persist_user_turn(
        db,
        client_id=client_id,
        conversation_id=conversation_id,
        user_content=user_content,
    )

    history = _load_history(
        db, conv.id, limit=assistance_history_max_turns()
    )

    try:
        assistant_text = chat_markdown(history)
    except LLMError:
        # Le user_msg est déjà persisté par le commit anticipé : pas
        # besoin de re-commiter ici. Le client conserve la conv (visible
        # dans /conversations) et peut réessayer en renvoyant le même
        # `conversation_id`.
        raise

    assistant_msg = AssistanceMessage(
        id=uuid4(),
        conversation_id=conv.id,
        turn_index=user_idx + 1,
        role="assistant",
        content=assistant_text,
    )
    db.add(assistant_msg)

    now = datetime.now(timezone.utc)
    conv.last_message_at = now
    conv.last_assistant_message_at = now
    # D.1.4.2 — par convention, un nouveau message assistant arrive « non
    # lu » par défaut. C'est au client d'appeler explicitement
    # `POST /conversations/{id}/read` lorsqu'il considère que la réponse a
    # été affichée à l'utilisateur. On ne touche donc PAS à `last_read_at`
    # ici — sinon la pastille ne pourrait jamais remonter.
    conv.updated_at = now

    db.commit()
    db.refresh(conv)
    db.refresh(assistant_msg)
    return conv, assistant_msg


def _persist_user_turn(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: Optional[UUID],
    user_content: str,
) -> tuple[AssistanceConversation, AssistanceMessage, int]:
    """Helper privé : (charge conv | crée conv) + persiste user_msg + commit.

    Centralise le pattern « commit anticipé » (D.1.4.4) utilisé par tous
    les flux (nominal, court-circuit). Lève les `ValueError(...)`
    standards (`empty_user_content`, `conversation_not_found`,
    `conversation_closed`).

    Retourne la conv, le message user inséré, et le `turn_index` du user.
    """
    user_content = (user_content or "").strip()
    if not user_content:
        raise ValueError("empty_user_content")

    if conversation_id is not None:
        conv = get_conversation_for_client(
            db, client_id=client_id, conversation_id=conversation_id
        )
        if conv is None:
            raise ValueError("conversation_not_found")
        if conv.status == "closed":
            raise ValueError("conversation_closed")
    else:
        conv = create_conversation(
            db, client_id=client_id, first_user_content=user_content
        )

    user_idx = _next_turn_index(db, conv.id)
    user_msg = AssistanceMessage(
        id=uuid4(),
        conversation_id=conv.id,
        turn_index=user_idx,
        role="user",
        content=user_content,
    )
    db.add(user_msg)

    now_user = datetime.now(timezone.utc)
    conv.last_message_at = now_user
    conv.updated_at = now_user
    db.commit()
    db.refresh(conv)
    db.refresh(user_msg)
    return conv, user_msg, user_idx


def process_suspended_short_circuit(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: Optional[UUID],
    user_content: str,
) -> tuple[AssistanceConversation, AssistanceMessage]:
    """Court-circuit `SUSPENDED` (acteur dont le dossier est gelé) — non-stream.

    Persiste le tour user puis renvoie immédiatement le texte standardisé
    (`SUSPENDED_RESPONSE_TEXT`) sans appeler le LLM ni le router.

    Garanties :
      - Aucune fuite de l'état interne (cf. règle anti-tipping-off — le
        texte est constant, neutre, indépendant du `account_state` exact).
      - Le message user est persisté (audit + UX cohérente : il apparaît
        dans l'historique comme tout autre tour).
      - Le message assistant porte `agent_used="default"` (pas de mention
        de l'agent compliance — le client ne doit même pas pouvoir
        deviner qu'un agent dédié l'a court-circuité), `message_type="text"`,
        `message_payload={"reason": "suspended_short_circuit"}` (lecture
        BO uniquement).

    Lève les mêmes `ValueError(...)` que [process_chat_turn] pour la
    gestion conv (`conversation_not_found`, `conversation_closed`).
    """
    conv, _user_msg, user_idx = _persist_user_turn(
        db,
        client_id=client_id,
        conversation_id=conversation_id,
        user_content=user_content,
    )

    assistant_msg = _persist_assistant_message(
        db,
        conversation_id=conv.id,
        turn_index=user_idx + 1,
        content=SUSPENDED_RESPONSE_TEXT,
        agent_used=_SUSPENDED_AGENT_USED,
        message_type="text",
        message_payload={"reason": _SUSPENDED_PAYLOAD_REASON},
    )

    logger.warning(
        "assistance.actor.short_circuit reason=suspended client_id=%s conv=%s turn=%s",
        client_id,
        conv.id,
        user_idx,
    )

    if assistant_msg is None:
        # Race rare : conversation supprimée entre les deux commits.
        raise ValueError("conversation_not_found")

    return conv, assistant_msg


def start_suspended_chat_turn(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: Optional[UUID],
    user_content: str,
) -> tuple[AssistanceConversation, AssistanceMessage, int]:
    """Variante stream du court-circuit `SUSPENDED`.

    Persiste conv + user_msg uniquement (commit anticipé). Le message
    assistant standardisé est ensuite émis et persisté par
    [stream_suspended_short_circuit] dans une session BDD dédiée.

    Symétrique de [start_chat_turn] mais sans router ni AgentInput :
    aucun appel LLM, aucune lecture mémoire long-terme. Le client
    `SUSPENDED` ne consomme aucun token OpenAI (anti-abuse + cost-saving).
    """
    return _persist_user_turn(
        db,
        client_id=client_id,
        conversation_id=conversation_id,
        user_content=user_content,
    )


def _resolve_resume_topic_hint(
    db: Session, *, conversation_id: UUID
) -> Optional[str]:
    """Résout l'option `resume_topic` d'un QCM de recentrage off-topic.

    Cherche le dernier message assistant `agent_used` **non-router** de
    la conversation : c'est l'agent qui portait le sujet en cours avant
    la digression off-topic. Si trouvé et valide, on l'utilise comme
    `agent_hint` réel ; sinon on retourne `None` → le router refera sa
    passe normale (et tombera probablement sur `default`).

    Pourquoi non-router : un message `agent_used='router'` correspond à
    un QCM (clarification ou recentrage), pas à un vrai tour
    spécialiste — il ne représente aucun sujet à reprendre.
    """
    last_specialist = (
        db.query(AssistanceMessage.agent_used)
        .filter(
            AssistanceMessage.conversation_id == conversation_id,
            AssistanceMessage.role == "assistant",
            AssistanceMessage.agent_used.isnot(None),
            AssistanceMessage.agent_used != AGENT_ROUTER_ID,
        )
        .order_by(desc(AssistanceMessage.turn_index))
        .limit(1)
        .scalar()
    )
    if not last_specialist:
        return None
    candidate = str(last_specialist).strip().lower()
    if candidate not in KNOWN_AGENT_IDS or candidate == AGENT_ROUTER_ID:
        return None
    return candidate


def _resolve_clarification_choice_hint(
    db: Session, *, conversation_id: UUID, hint: str
) -> Optional[str]:
    """Résout un hint correspondant à une option de QCM **agent** précédent.

    Phase 2c.7 — Patch A (continuité post-clarification).

    Contexte du bug fixé ici (cf. conv `fc8a689f` audit) :
        Un sub-agent (ex. `compliance.transactional`) pose une
        clarification via `ask_user_question` avec des options
        `id={list, count, amounts}` qui sont des **identifiants
        sémantiques de clarification**, PAS des `agent_id`. Le client
        clique → Flutter renvoie `agent_hint='count'`. Le fallback de
        `_decide_agent` (`hint in KNOWN_AGENT_IDS`) rejette ce hint, log
        `invalid_hint hint='count'`, et redonne la main au router qui
        reclasse depuis zéro → cassure de la chaîne agent / saut
        vers un autre sub-agent (`advisor`, `compliance.general`…) →
        UX incohérente (la conv « oublie » à qui elle parlait).

    Ce helper rétablit la continuité :
        1. On lit le dernier message assistant `message_type='choices'`
           de la conv.
        2. Si le hint correspond à l'`id` d'une de ses options, on
           retourne le `agent_used` de ce message — qui peut être un
           sub-agent (`compliance.transactional`, `compliance.general`…).
        3. Le caller (`_decide_agent`) renvoie cet agent dans la
           `RouterDecision` → le tour reste sur le bon agent.

    Garde-fous :
        - On ne lit QUE le message assistant le plus récent. Pas de
          recherche en arrière (un QCM trop vieux n'est plus pertinent —
          le client a sans doute changé de sujet).
        - On valide que `agent_used` appartient à `KNOWN_RUNTIME_AGENT_IDS`
          (incl. sub-agents) pour éviter les valeurs corrompues.
        - On retourne `None` plutôt que de planter — le caller fallback
          sur le router classique, comportement actuel préservé.

    Pourquoi pas pour les QCM **router** ? Ces QCM-là ont déjà des
    options `id ∈ {advisor, product, compliance, …}` reconnues par
    `KNOWN_AGENT_IDS` → la branche existante `elif hint in
    KNOWN_AGENT_IDS` les couvre. Ce helper s'occupe uniquement des
    QCM **agent** (où les ids sont sémantiques, pas des agent_id).
    """
    if not hint:
        return None
    last_choices = (
        db.query(
            AssistanceMessage.agent_used,
            AssistanceMessage.message_payload,
        )
        .filter(
            AssistanceMessage.conversation_id == conversation_id,
            AssistanceMessage.role == "assistant",
            AssistanceMessage.message_type == "choices",
        )
        .order_by(desc(AssistanceMessage.turn_index))
        .limit(1)
        .first()
    )
    if last_choices is None:
        return None
    agent_used, payload = last_choices
    if not agent_used or not isinstance(payload, dict):
        return None
    options = payload.get("options") or []
    if not isinstance(options, list):
        return None
    # Match insensible à la casse (Flutter envoie l'`id` brut, mais on
    # est tolérants pour rester cohérent avec le reste du module).
    norm_hint = hint.strip().lower()
    found = False
    for opt in options:
        if not isinstance(opt, dict):
            continue
        opt_id = str(opt.get("id") or "").strip().lower()
        if opt_id and opt_id == norm_hint:
            found = True
            break
    if not found:
        return None
    candidate = str(agent_used).strip().lower()
    if candidate == AGENT_ROUTER_ID:
        # Les QCM router sont déjà gérés par la branche `KNOWN_AGENT_IDS`
        # de `_decide_agent`. Si on arrive ici, c'est que l'`id` n'est pas
        # un agent valide — laisser le router reclasser plutôt que
        # ré-engager un agent qui n'a pas posé la question.
        return None
    if candidate not in tools_registry.KNOWN_RUNTIME_AGENT_IDS:
        return None
    return candidate


async def _run_via_runtime(
    *,
    db: Session,
    agent_id: str,
    agent_input: AgentInput,
    actor_kind: ActorKind,
    conversation_id: UUID,
    user_id: int,
):
    """Wrapper Phase 2a : appelle `runtime.run_agent_loop` avec les
    paramètres dérivés du contexte. Yield les `AgentEvent` directement
    (compatible avec la boucle de consommation dans `stream_assistant_turn`).

    En cas d'absence de tools dans le registry pour cet agent, le caller
    aura déjà court-circuité et utilisé le fallback Phase 1.
    """
    if should_use_slack_pipeline(agent_id):
        async for event in iter_product_slack_pipeline_events(
            db=db,
            agent_id=agent_id,
            agent_input=agent_input,
            actor_kind=actor_kind,
            conversation_id=conversation_id,
            user_id=user_id,
        ):
            yield event
        return
    system_prompt = load_agent_system_prompt(agent_id)
    available_tools = tools_registry.tools_for(agent_id)
    async for event in run_agent_loop(
        agent_id=agent_id,
        system_prompt=system_prompt,
        available_tools=available_tools,
        agent_input=agent_input,
        actor_kind=actor_kind,
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
    ):
        yield event


def _decide_agent(
    *,
    agent_input: AgentInput,
    agent_hint: Optional[str],
    conv_id: UUID,
    db: Optional[Session] = None,
) -> RouterDecision:
    """Décide quel agent doit traiter ce tour (Phase 1 multi-agents).

    Ordre de priorité :
      1. Si le **kill-switch** `ASSISTANCE_MULTI_AGENT_ENABLED=false` →
         force `default` (rollback instantané sans rebuild).
      2. Si le client a fourni `agent_hint = 'resume_topic'` (clic sur
         l'option de reprise dans un QCM de recentrage off-topic) →
         résolution serveur-side via [_resolve_resume_topic_hint].
      3. Si le client a fourni un autre `agent_hint` valide (= clic sur
         une option de QCM précédent) → shortcut, pas de router LLM.
      4. Sinon → appel `router.classify(...)` (function calling natif).

    Toujours retourne une `RouterDecision` exploitable par
    `stream_assistant_turn`. Aucune exception n'est laissée remonter.
    """
    if not assistance_multi_agent_enabled():
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=1.0,
            reasoning="multi_agent_disabled",
        )

    if agent_hint:
        hint = agent_hint.strip().lower()
        # Cas spécial : reprise du sujet courant après un off-topic.
        # On résout côté serveur en relisant la DB pour éviter de faire
        # confiance au client sur l'agent à invoquer (surface d'attaque
        # nulle : pas d'`agent_id` arbitraire accepté).
        if hint == RESUME_TOPIC_HINT_ID:
            if db is not None:
                resolved = _resolve_resume_topic_hint(
                    db, conversation_id=conv_id
                )
                if resolved is not None:
                    return RouterDecision(
                        agent_id=resolved,
                        confidence=1.0,
                        reasoning="resume_topic_resolved",
                    )
            logger.info(
                "assistance.agent.resume_topic_unresolved conv=%s — "
                "fallback router",
                conv_id,
            )
            # Pas de sujet à reprendre → on laisse tourner le router
            # comme un tour normal sur le message brut.
        elif hint in KNOWN_AGENT_IDS and hint != AGENT_ROUTER_ID:
            return RouterDecision(
                agent_id=hint,
                confidence=1.0,
                reasoning="user_clicked_choice",
            )
        else:
            # Phase 2c.7 — Patch A (continuité post-clarification) :
            # avant de tomber en `invalid_hint`, on vérifie si ce hint
            # n'est pas l'`id` d'une option d'un QCM **agent** récent
            # (`ask_user_question` → message persisté `message_type=
            # 'choices'`). Si oui, on remet la main à l'agent qui avait
            # posé la question — c'est lui qui doit interpréter la
            # réponse, pas le router.
            if db is not None:
                resolved = _resolve_clarification_choice_hint(
                    db, conversation_id=conv_id, hint=hint
                )
                if resolved is not None:
                    logger.info(
                        "assistance.agent.clarification_choice_resolved "
                        "conv=%s hint=%r → agent=%s",
                        conv_id,
                        agent_hint,
                        resolved,
                    )
                    return RouterDecision(
                        agent_id=resolved,
                        confidence=1.0,
                        reasoning="clarification_choice_continuity",
                    )
            # Hint inconnu (ni agent_id valide, ni option de QCM agent
            # récent) → on ignore et on laisse tourner le router plutôt
            # que de planter le tour.
            logger.warning(
                "assistance.agent.invalid_hint conv=%s hint=%r — fallback router",
                conv_id,
                agent_hint,
            )

    # Phase 2 wiki v1.4 patch — Hot-path follow-up : si le user envoie
    # un message court qui suit un tour d'agent expert, on conserve cet
    # agent sans appeler le LLM router (économie ~150-300 ms + stabilité
    # conversationnelle). Cf. `router_hot_path.py`.
    hot_path_decision = assistance_router_hot_path.should_skip_router_from_input(
        agent_input,
        agent_hint=agent_hint,
    )
    if hot_path_decision is not None:
        logger.info(
            "assistance.agent.hot_path_bypass conv=%s agent=%s",
            conv_id,
            hot_path_decision.agent_id,
        )
        return hot_path_decision

    try:
        return agent_router.classify(agent_input)
    except Exception as exc:  # noqa: BLE001 — best-effort, jamais propager
        logger.warning(
            "assistance.agent.router_exception conv=%s exc=%s — fallback default",
            conv_id,
            exc,
        )
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_exception",
        )


def start_chat_turn(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: Optional[UUID],
    user_content: str,
    agent_hint: Optional[str] = None,
    person_id: Optional[UUID] = None,
) -> tuple[
    AssistanceConversation,
    AssistanceMessage,
    AgentInput,
    RouterDecision,
    int,
]:
    """1ère phase d'un tour streaming (D.1.4.5 — phase 2 SSE).

    Persiste la conversation et le message user immédiatement (commit
    anticipé), construit le `AgentInput` (mémoire + recent_turns), puis
    appelle le router (sauf shortcut via `agent_hint`).

    Returns:
        - la conversation,
        - le message user inséré,
        - le `AgentInput` à passer à `stream_assistant_turn`,
        - la `RouterDecision` (pour dispatch + log),
        - le `turn_index` du message user.

    Lève les mêmes `ValueError(...)` que [process_chat_turn].
    """
    conv, user_msg, user_idx = _persist_user_turn(
        db,
        client_id=client_id,
        conversation_id=conversation_id,
        user_content=user_content,
    )

    # Palier 2 D.2 — contexte = mémoire long-terme (summary + cross-conv)
    # + K derniers tours bruts. Backward-compatible : sur une conv courte
    # sans summary, c'est exactement les K derniers tours, comme avant.
    state = assistance_memory.load_memory_state(db, conv.id)
    recent_turns = _load_history(
        db,
        conv.id,
        limit=assistance_memory.assistance_recent_turns_kept(),
    )
    # Phase 2b — fix critique : `client_id` et `person_id` injectés
    # explicitement depuis le caller (`MemoryState` ne les expose pas).
    # Le runtime utilise ces deux champs pour construire `ToolContext`,
    # indispensables aux tools introspectifs (compliance_repo, etc.).
    memory_state_dict = {
        "client_id": str(client_id) if client_id else None,
        "person_id": str(person_id) if person_id else None,
        "conversation_summary": (
            getattr(state, "conversation_summary", None) if state else None
        ),
        "client_long_memory": (
            getattr(state, "client_long_memory", None) if state else None
        ),
        "summarized_until_turn": (
            getattr(state, "summarized_until_turn", None) if state else None
        ),
        # Phase 2 wiki v1.4 patch — slot « topic en cours », lu par le
        # router pour stabiliser les follow-ups déictiques. NULL si
        # aucun tool ancrant n'a encore été appelé sur cette conv.
        "current_topic": _safe_get_current_topic(db, conv.id),
    }
    # Cognitive Bot v4 — Lot 1+2 (2026-05-04). Avant `_decide_agent`,
    # on calcule un cognitive_state PRÉLIMINAIRE :
    #   * `emotional_intent` — précis car keyword-only sur user_message.
    #   * `conversation_stage` — hérité du tour précédent (continuité).
    #   * `trust_level` — recalculé avec emotion courante + prev_trust.
    #   * `knowledge_level` — déduit de client_long_memory.
    # Ce snapshot préliminaire est injecté dans `memory_state["cognitive_state"]`
    # pour que le router LLM le voie (cf. `_build_router_messages`).
    # Le state final sera **recalculé** après la décision pour intégrer
    # le `decision_kind` du tour courant (qui peut faire transiter le
    # stage : ask_clarification → CLARIFICATION, route_to advisor →
    # RECOMMENDATION, etc.).
    prev_cog_dict: Optional[dict] = None
    prev_cog_state: Optional[CognitiveState] = None
    try:
        prev_cog_dict = _safe_load_previous_cognitive_state(db, conv.id)
        prev_cog_state = (
            CognitiveState.from_dict(prev_cog_dict)
            if prev_cog_dict
            else None
        )
        preliminary_cog_state = compute_cognitive_state(
            user_message=user_content,
            prev_state=prev_cog_state,
            intent_classification=None,  # pas encore disponible
            last_router_decision_kind=None,  # → continuité (prev_stage)
            client_long_memory=memory_state_dict.get("client_long_memory"),
            recent_turns=recent_turns,
        )
        memory_state_dict["cognitive_state"] = preliminary_cog_state.to_dict()
    except Exception:  # noqa: BLE001 — best-effort, never kill a turn
        logger.exception(
            "assistance.cognitive_state.preliminary_failed conv=%s", conv.id
        )

    # Cognitive Bot v4 — Lot 7 (2026-05-04). Extraction discovery
    # (multi-projet client + paramètres adossés). Best-effort, ne casse
    # jamais un tour. Branchements :
    #   * Lookup cross-conv des projets actifs de la personne (par
    #     ``person_id``). Permet au bot de se souvenir de « achat
    #     maison » même si le client revient 3 jours plus tard dans
    #     une nouvelle conv.
    #   * Extraction keyword (latence < 1 ms) sur le user_message courant.
    #     LLM gating reste branchable en V2 (cf. CLIENT_DISCOVERY.md).
    #   * Persistance des nouveaux projets / floating params dans la
    #     transaction courante (commit délégué à _persist_user_turn).
    #   * Détection switch (« parlons d'autre chose ») → pause des
    #     autres projets actifs.
    #   * Injection du bloc ``[CLIENT DISCOVERY]`` rendu en mémoire,
    #     lu par le router et les agents experts via memory_state.
    #   * Préparation du context block « previous_bot_turn » si user
    #     message laconique (cf. should_embed_previous_bot_turn).
    last_assistant_text: Optional[str] = None
    for turn in reversed(recent_turns or []):
        if isinstance(turn, dict) and turn.get("role") == "assistant":
            last_assistant_text = str(turn.get("content") or "")
            break
    try:
        active_projects = (
            discovery_repo.list_active_projects_for_person(
                db, person_id, limit=5
            )
            if person_id
            else []
        )

        extraction = discovery_engine.extract_discovery_keyword_pass(
            user_message=user_content,
            last_assistant_text=last_assistant_text,
            active_projects=active_projects,
            current_turn=user_idx,
        )

        # Switch detection : on pause les autres projets actifs si signal
        # explicite + un projet est nominativement présent dans extraction.
        if person_id and discovery_engine.detect_project_switch_signal(
            user_content
        ):
            keep_label: Optional[str] = None
            if extraction.new_or_updated_projects:
                keep_label = extraction.new_or_updated_projects[0].label
            discovery_repo.pause_other_active_projects(
                db, person_id=person_id, keep_label=keep_label
            )

        # Upsert des projets détectés. Best-effort : on log mais on ne
        # bloque pas le tour si ça échoue.
        if person_id:
            for proj in extraction.new_or_updated_projects:
                discovery_repo.upsert_project(
                    db,
                    person_id=person_id,
                    conversation_id=conv.id,
                    project=proj,
                    current_turn=user_idx,
                )
            for fp in extraction.floating_parameters:
                discovery_repo.add_floating_parameter(
                    db,
                    conversation_id=conv.id,
                    person_id=person_id,
                    floating=fp,
                    current_turn=user_idx,
                )

        # Re-fetch les projets actifs APRÈS l'upsert pour le rendu prompt.
        if person_id:
            active_projects_post = (
                discovery_repo.list_active_projects_for_person(
                    db, person_id, limit=5
                )
            )
            pending_floating = (
                discovery_repo.list_pending_floating_parameters(
                    db, conv.id, limit=5
                )
            )
        else:
            active_projects_post = []
            pending_floating = []

        rendered = discovery_engine.render_discovery_for_prompt(
            active_projects=active_projects_post,
            floating_parameters=pending_floating,
        )
        if rendered:
            memory_state_dict["client_discovery"] = rendered

        # Préparation du context block previous_bot (utilisé par les
        # agents experts pour les messages laconiques) — c'est juste un
        # texte qu'on pose dans memory_state ; agent_loop décide de
        # l'injecter ou non.
        prev_bot_block = build_previous_bot_context_block(
            user_message=user_content,
            last_assistant_text=last_assistant_text,
        )
        if prev_bot_block:
            memory_state_dict["previous_bot_context_block"] = prev_bot_block
    except Exception:  # noqa: BLE001 — best-effort, never kill a turn
        logger.exception(
            "assistance.client_discovery.failed conv=%s", conv.id
        )

    agent_input = AgentInput(
        user_message=user_content,
        recent_turns=recent_turns,
        memory_state=memory_state_dict,
    )

    decision = _decide_agent(
        agent_input=agent_input,
        agent_hint=agent_hint,
        conv_id=conv.id,
        db=db,
    )
    agent_input.router_metadata = decision

    # Cognitive Bot v4 — Lot 1+2 (2026-05-04). FINALISATION du cognitive
    # state à la lumière de la décision du router (qui peut faire
    # transiter le stage). Calcul de l'`objective` déterministe à partir
    # du cognitive_state final. Tous deux sont attachés à la decision et
    # exposés côté `agent_input.memory_state` pour les agents experts
    # (cf. `agent_loop._build_initial_messages`).
    try:
        final_cog_state = compute_cognitive_state(
            user_message=user_content,
            prev_state=prev_cog_state,
            intent_classification=decision.intent_classification,
            last_router_decision_kind=_decision_kind_label(decision),
            client_long_memory=memory_state_dict.get("client_long_memory"),
            recent_turns=recent_turns,
        )
        decision.cognitive_state = final_cog_state.to_dict()
        memory_state_dict["cognitive_state"] = decision.cognitive_state

        objective = compute_objective(final_cog_state)
        decision.objective = objective.to_dict()
        memory_state_dict["objective"] = decision.objective
    except Exception:  # noqa: BLE001 — best-effort, never kill a turn
        logger.exception(
            "assistance.cognitive_state.finalize_failed conv=%s", conv.id
        )

    logger.info(
        "assistance.agent.tour conv=%s turn=%s router=%s",
        conv.id,
        user_idx,
        json.dumps(decision.to_log_dict(), ensure_ascii=False),
    )

    # Router v2 (2026-05-04) — on persiste la décision du router (avec
    # intent_classification keyword) dans `assistance_agent_decisions`.
    # Cela permet à la vue admin 3-colonnes (workflow trace, cf. v3.0)
    # d'afficher pour chaque turn le `primary_tag` détecté + le scope
    # level — utile pour debugger les misroutings.
    # Cognitive Bot v4 (2026-05-04) — la persistance inclut aussi le
    # ``cognitive_state`` calculé ci-dessus.
    _persist_router_decision(
        db=db,
        conversation_id=conv.id,
        message_id=user_msg.id,
        decision=decision,
        iteration=0,
        client_discovery_block=memory_state_dict.get("client_discovery"),
    )

    # Cognitive Bot v4 — Lot 6 fix (2026-05-05) — commit explicite du
    # router_decision + cognitive_state + objective. Sans cela, le
    # ``begin_nested`` de ``audit.persist_decision`` reste un savepoint
    # qui n'est jamais flushé : la session HTTP ``db`` (Depends/get_db)
    # est ferm\u00e9e à la fin de la requête sans commit explicite, ce qui
    # rollback toutes les decisions cognitives. Le user_msg est commité
    # plus haut (``_persist_user_turn``) et les decisions des agents
    # experts sont sur une session distincte (SessionLocal du
    # ``_drive_pipeline``), donc ce commit ne concerne QUE le router et
    # les snapshots cognitifs du tour. Best-effort : un échec ici ne
    # casse pas le tour utilisateur (le SSE va déjà être lancé).
    try:
        db.commit()
    except Exception:  # noqa: BLE001
        logger.exception(
            "assistance.router.commit_failed conv=%s",
            conv.id,
        )
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass

    return conv, user_msg, agent_input, decision, user_idx


def _persist_router_decision(
    *,
    db: Session,
    conversation_id: UUID,
    message_id: UUID,
    decision: RouterDecision,
    iteration: int = 0,
    client_discovery_block: Optional[str] = None,
) -> None:
    """Persiste la décision du router dans `assistance_agent_decisions`
    pour audit — best-effort, jamais d'exception remontée.

    On encode :
      * ``tool_name = "router_classify"`` — repère stable pour les
        requêtes de la vue admin (filtre / agrégation).
      * ``autonomy_level = "L0"`` — par convention le router est L0
        (pas d'effet de bord, juste sélection d'agent).
      * ``arguments_json`` = la classification keyword + le détail de
        décision (decision_kind = route_to / ask_clarification /
        redirect_off_topic + agent + confidence).
      * ``result_summary`` = ``decision.reasoning`` (déjà tronqué).
    """
    try:
        from services.assistance.agents.tools.shared import audit

        intent = decision.intent_classification or {}
        cog = decision.cognitive_state or {}
        obj = decision.objective or {}

        decision_kind = _decision_kind_label(decision)

        args = {
            "decision_kind": decision_kind,
            "agent_id": decision.agent_id,
            "confidence": round(decision.confidence, 3),
            "intent_classification": intent or None,
            # Cognitive Bot v4 (2026-05-04) — snapshot cognitif du tour
            # (emotional_intent, conversation_stage, trust_level,
            # knowledge_level). Lu au tour suivant via
            # ``_safe_load_previous_cognitive_state`` pour assurer la
            # continuité de l'état (notamment du trust_level qui s'érode
            # / regagne tour par tour). Visible dans la vue admin
            # 3-colonnes pour debug du comportement émotionnel du bot.
            "cognitive_state": cog or None,
            # Cognitive Bot v4 — Lot 2 (2026-05-04) — objectif déterministe
            # du tour (primary_goal + next_best_action + stop_pushing +
            # strategy_hint). Audit dans la vue admin pour valider que le
            # bot a la bonne stratégie selon l'état émotionnel détecté.
            "objective": obj or None,
            # Cognitive Bot v4 — Lot 7 V1.2 (2026-05-05) — snapshot du
            # bloc ``[CLIENT DISCOVERY]`` exactement tel qu'injecté au
            # router LLM ce tour. Permet à l'admin de reconstituer "ce
            # que le bot savait des projets/paramètres du client AU
            # moment de cette décision" — la table
            # ``assistance_client_discovery_projects`` ne stocke que
            # l'état courant, pas l'historique des transitions.
            # Best-effort : ``None`` si le client n'avait pas (encore)
            # de projet identifié.
            "client_discovery_block": client_discovery_block or None,
        }

        # Cognitive Bot v4 — Lot 6 (2026-05-04) — double-write des
        # dimensions cognitives sur les colonnes natives (cf. migration
        # 152). La JSONB ``arguments_json`` reste la source de vérité
        # complète ; les colonnes natives accélèrent les agrégats funnel
        # (cf. ``admin_cognitive_router``) et exposent les données aux
        # outils tiers (Metabase / Retool). ``trust_level`` est coercé
        # en float prudent (best-effort).
        cognitive_columns: dict = {}
        if cog:
            cognitive_columns["emotional_intent"] = cog.get("emotional_intent")
            cognitive_columns["conversation_stage"] = cog.get("conversation_stage")
            cognitive_columns["knowledge_level"] = cog.get("knowledge_level")
            tl_raw = cog.get("trust_level")
            if tl_raw is not None:
                try:
                    cognitive_columns["trust_level"] = float(tl_raw)
                except (TypeError, ValueError):
                    cognitive_columns["trust_level"] = None
        if obj:
            cognitive_columns["primary_goal"] = obj.get("primary_goal")
            cognitive_columns["next_best_action"] = obj.get("next_best_action")

        audit.persist_decision(
            db=db,
            conversation_id=conversation_id,
            message_id=message_id,
            agent_id="router",
            iteration=int(iteration),
            tool_name="router_classify",
            autonomy_level="L0",
            arguments=args,
            reasoning_summary=decision.reasoning or "",
            result_summary=None,
            review_status="auto",
            extra_columns=cognitive_columns or None,
        )
    except Exception:  # noqa: BLE001 — best-effort, ne casse jamais le tour
        logger.exception(
            "assistance.router.persist_decision_failed conv=%s",
            conversation_id,
        )


def _build_choices_payload(
    decision: RouterDecision,
) -> tuple[str, list[ChoiceOption], dict, str]:
    """Prépare le payload du QCM `choices` à émettre + à persister.

    Retourne `(prompt, options_with_freeform, payload_dict, fallback_text)` :
      - `prompt`                 : phrase courte FR à afficher.
      - `options_with_freeform`  : options du LLM + "Rien de tout ça".
      - `payload_dict`           : ce qui sera stocké en JSONB
                                    (`message_payload`).
      - `fallback_text`          : texte lisible stocké en `content`,
                                    pour les clients legacy / l'export.

    Priorité d'extraction du prompt :
      1. `decision.redirect_bridge` (cas off-topic, règle 6 du router) —
         message bienveillant de recentrage.
      2. `decision.reasoning` (cas `ask_clarification`) — phrase de
         demande de précision.
      3. Fallback générique.
    """
    bridge = (decision.redirect_bridge or "").strip()
    reasoning_raw = (decision.reasoning or "").strip()
    prompt = bridge or reasoning_raw or (
        "Pour mieux te répondre, peux-tu préciser ta question ?"
    )

    options: list[ChoiceOption] = list(decision.fallback_choices or [])
    # Ajout systématique de l'option "freeform" en fin de liste si pas
    # déjà présente (l'utilisateur peut toujours dire "rien de tout ça").
    if not any(o.id == _FREEFORM_CHOICE_ID for o in options):
        options.append(
            ChoiceOption(id=_FREEFORM_CHOICE_ID, label=_FREEFORM_CHOICE_LABEL)
        )

    payload_dict = {
        "options": [o.to_dict() for o in options],
        "allow_freeform": True,
    }

    # Texte lisible (fallback pour clients qui ignorent message_type).
    lines = [prompt]
    for i, opt in enumerate(options, start=1):
        lines.append(f"{i}. {opt.label}")
    fallback_text = "\n".join(lines)

    return prompt, options, payload_dict, fallback_text


# Phase 2c.1 — message fallback texte affiché à l'utilisateur quand le
# pipeline LLM échoue de manière transient (ex. OpenAI 502 Cloudflare).
# Volontairement neutre : pas de mention « LLM », « OpenAI », « erreur
# interne ». Idéalement consistant avec `MAX_ITER_FALLBACK_MESSAGE` côté
# runtime (cf. `agents/runtime/agent_loop.py`). Ce texte est aussi le
# seul affiché au user — un client mobile peut le styler en gris/orange
# via le flag `metadata.is_error_fallback=True` exposé dans le payload.
LLM_ERROR_FALLBACK_MESSAGE = (
    "Le service est temporairement indisponible. "
    "Réessaie dans un instant — désolé pour la gêne."
)


def _persist_error_fallback(
    db: Session,
    *,
    conversation_id: UUID,
    turn_index: int,
    agent_used: Optional[str],
    error_code: str,
) -> Optional[AssistanceMessage]:
    """Persiste un message assistant fallback suite à une erreur LLM.

    Émet `message_type='text'` avec `message_payload.metadata` exposant
    `is_error_fallback=True` + `error_code` pour traçabilité (audit BO,
    style UI custom côté mobile). On reste en `text` (pas de nouveau
    type) pour ne rien casser côté Flutter ; le mobile peut détecter
    la metadata et afficher la bulle en orange + icône warning.

    Idempotent côté schéma : pas de modification du modèle, pas de
    migration. Retourne `None` si la conversation a disparu (race rare).
    """
    payload = {
        "metadata": {
            "is_error_fallback": True,
            "error_code": error_code,
        }
    }
    return _persist_assistant_message(
        db,
        conversation_id=conversation_id,
        turn_index=turn_index,
        content=LLM_ERROR_FALLBACK_MESSAGE,
        agent_used=agent_used,
        message_type="text",
        message_payload=payload,
    )


def _persist_assistant_message(
    db: Session,
    *,
    conversation_id: UUID,
    turn_index: int,
    content: str,
    agent_used: Optional[str],
    message_type: str = "text",
    message_payload: Optional[dict] = None,
) -> Optional[AssistanceMessage]:
    """Insère le message assistant avec les colonnes multi-agents.

    Met à jour `last_message_at`, `last_assistant_message_at`,
    `updated_at` (méta conv). Retourne `None` si la conversation a
    disparu (cas race rare).
    """
    conv = db.query(AssistanceConversation).filter(
        AssistanceConversation.id == conversation_id
    ).one_or_none()
    if conv is None:
        return None

    msg = AssistanceMessage(
        id=uuid4(),
        conversation_id=conv.id,
        turn_index=turn_index,
        role="assistant",
        content=content,
        agent_used=agent_used,
        message_type=message_type,
        message_payload=message_payload,
    )
    db.add(msg)

    now = datetime.now(timezone.utc)
    conv.last_message_at = now
    conv.last_assistant_message_at = now
    conv.updated_at = now
    db.commit()
    db.refresh(msg)
    return msg


async def stream_assistant_turn(
    *,
    session_factory,
    conversation_id: UUID,
    user_idx: int,
    agent_input: AgentInput,
    decision: RouterDecision,
    client_id: Optional[UUID] = None,
    actor_kind: Optional[ActorKind] = None,
    user_id: Optional[int] = None,
    person_id: Optional[UUID] = None,
) -> "AsyncIterator[dict]":
    """Pipeline multi-agents → events SSE applicatifs (D.1.4.5).

    Yield des events typés (cf. doc § 1.9 et § 3) :
      - `{'type': 'delta', 'content': '...'}`  → token assistant.
      - `{'type': 'choices', 'prompt': '...', 'options': [...]}`
        → QCM si le router est indécis (`decision.fallback_choices`).
      - `{'type': 'done', 'message_id': '<uuid>', 'agent_used': '<id>'}`
        → fin du tour, message persisté.
      - `{'type': 'error', 'message': '<code>'}` → échec récupérable.

    **Robustesse** :
      - Session BDD dédiée (`session_factory()`), survit aux cancels HTTP.
      - Si le LLM échoue en plein stream, le partiel est persisté.
      - Aucune exception ne remonte hors de cette coroutine.
    """
    from typing import AsyncIterator  # local import for runtime hint

    db = session_factory()
    started_at = time.monotonic()
    full_text = ""
    completed = False
    # Le path `choices` couvre 2 cas :
    #   - clarification : router indécis avec options de désambiguïsation ;
    #   - off-topic    : router émet un bridge de recentrage (peut avoir
    #                    0 option de catégorie, l'option `freeform` étant
    #                    ajoutée systématiquement par _build_choices_payload).
    is_choices_path = decision.is_off_topic or (
        bool(decision.fallback_choices) and not decision.is_decisive
    )
    agent_id = AGENT_ROUTER_ID if is_choices_path else decision.agent_id

    try:
        # ── Cas QCM (router indécis) ────────────────────────────────
        if is_choices_path:
            prompt, options, payload_dict, fallback_text = _build_choices_payload(
                decision
            )
            yield {
                "type": "choices",
                "prompt": prompt,
                "options": [o.to_dict() for o in options],
                "allow_freeform": True,
            }
            msg = _persist_assistant_message(
                db,
                conversation_id=conversation_id,
                turn_index=user_idx + 1,
                content=fallback_text,
                agent_used=AGENT_ROUTER_ID,
                message_type="choices",
                message_payload=payload_dict,
            )
            if msg is None:
                yield {"type": "error", "message": "conversation_gone"}
                return
            yield {
                "type": "done",
                "message_id": str(msg.id),
                "completed": True,
                "agent_used": AGENT_ROUTER_ID,
                "message_type": "choices",
            }
            sub_path = "off_topic" if decision.is_off_topic else "clarification"
            logger.info(
                "assistance.agent.tour_done conv=%s turn=%s "
                "agent=%s latency_ms=%.0f path=choices sub=%s",
                conversation_id,
                user_idx + 1,
                AGENT_ROUTER_ID,
                (time.monotonic() - started_at) * 1000,
                sub_path,
            )
            # Pas de consolidation mémoire pour un QCM (pas un vrai tour).
            return

        # ── Cas nominal (agent répond) ──────────────────────────────
        # Phase 2a : si le runtime loop est activé pour cet agent ET
        # qu'on a tout ce qu'il faut (actor_kind, user_id), on dispatche
        # via le runtime (multi-tools). Sinon, fallback Phase 1.
        #
        # Phase 2c.7 — Patch A2 (continuité post-clarification) :
        # `decision.agent_id` peut être un sub-agent (ex.
        # `compliance.transactional`) quand `_resolve_clarification_choice_hint`
        # rétablit la continuité après un clic sur QCM. Or
        # `assistance_runtime_loop_agents()` ne contient que les
        # **top-levels** (`compliance`, `product`, `advisor`, `market`).
        # On dérive donc le top-level (split sur le `.`) pour le check
        # de runtime — `tools_registry.tools_for(...)` accepte déjà
        # parfaitement les sub-agents, et `load_agent_system_prompt`
        # normalise `compliance.transactional` → `compliance_transactional`.
        runtime_top_level = decision.agent_id.split(".", 1)[0]
        use_runtime = (
            assistance_runtime_loop_enabled()
            and runtime_top_level in assistance_runtime_loop_agents()
            and actor_kind is not None
            and user_id is not None
            and bool(tools_registry.tools_for(decision.agent_id))
        )

        try:
            if use_runtime:
                event_iter = _run_via_runtime(
                    db=db,
                    agent_id=decision.agent_id,
                    agent_input=agent_input,
                    actor_kind=actor_kind,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
            else:
                agent = get_agent(
                    decision.agent_id,
                    client_id=str(client_id) if client_id else None,
                )
                event_iter = agent.stream(agent_input=agent_input)
        except ValueError as exc:
            logger.warning(
                "assistance.agent.unknown_id conv=%s id=%s exc=%s",
                conversation_id,
                decision.agent_id,
                exc,
            )
            yield {"type": "error", "message": "agent_unknown"}
            return

        runtime_choices: Optional[dict] = None
        # Phase 2b : capté via AgentEvent(type='done', final_agent_id=...)
        # pour persister le **sub-agent** réellement utilisé (ex.
        # `compliance.transactional` au lieu du top-level `compliance`).
        final_agent_id: Optional[str] = None
        # Phase 2c : chaîne d'agents traversés + consultations specialists.
        # Stockés dans `message_payload.metadata.{agent_chain, consultations}`
        # pour audit + future UI BO (visualisation du chemin).
        runtime_agent_chain: Optional[list[str]] = None
        runtime_consultations: Optional[list[dict]] = None
        # Phase 2c.2 — embeds UI structurés (cartes `transaction_detail`,
        # etc.). Persistés à part dans `message_payload.embeds` (clé top-
        # level distincte de `metadata` car affichés directement par le
        # client, pas un audit).
        runtime_embeds: Optional[list[dict]] = None
        runtime_output_judge: Optional[dict] = None
        try:
            async for event in event_iter:
                if event.type == "delta":
                    full_text += event.content or ""
                    yield {"type": "delta", "content": event.content or ""}
                elif event.type == "thinking":
                    # Phase 2b : event d'UX intermédiaire (non persisté).
                    # Le client peut afficher un sous-titre discret pour
                    # rassurer pendant les phases de classification (ex:
                    # diagnose_compliance_topic).
                    yield {
                        "type": "thinking",
                        "phase": event.thinking_phase or "",
                        "agent": event.thinking_agent or "",
                    }
                elif event.type == "choices":
                    # Phase 2a/2b : le runtime peut émettre un `choices`
                    # via le tool `ask_user_question`. On capture le
                    # payload pour le persister en `message_type=choices`.
                    # `to_dict()` propage `agent_hint` et `deep_link` si
                    # présents (Phase 2b).
                    options = event.options or []
                    runtime_choices = {
                        "prompt": event.prompt or "",
                        "options": [o.to_dict() for o in options],
                        "allow_freeform": bool(event.allow_freeform),
                    }
                    yield {
                        "type": "choices",
                        "prompt": runtime_choices["prompt"],
                        "options": runtime_choices["options"],
                        "allow_freeform": runtime_choices["allow_freeform"],
                    }
                elif event.type == "error":
                    # C.2 — fallback persistant : on émet l'event
                    # `error` (le mobile peut afficher un toast
                    # transient) puis on **persiste** un message
                    # assistant fallback texte et on yield un `done`
                    # propre avec son `message_id`. Cela fait sortir
                    # le client de son state loading sans qu'il
                    # reste à poller indéfiniment un assistant qui
                    # n'arriverait jamais.
                    error_code_local = event.error_code or "agent_error"
                    yield {
                        "type": "error",
                        "message": error_code_local,
                    }
                    fb_agent = final_agent_id or decision.agent_id
                    fb_msg = _persist_error_fallback(
                        db,
                        conversation_id=conversation_id,
                        turn_index=user_idx + 1,
                        agent_used=fb_agent,
                        error_code=error_code_local,
                    )
                    if fb_msg is not None:
                        yield {
                            "type": "done",
                            "message_id": str(fb_msg.id),
                            "completed": False,
                            "agent_used": fb_agent,
                            "message_type": "text",
                        }
                        logger.info(
                            "assistance.agent.tour_error_fallback "
                            "conv=%s turn=%s agent=%s code=%s",
                            conversation_id,
                            user_idx + 1,
                            fb_agent,
                            error_code_local,
                        )
                    return
                elif event.type == "done":
                    completed = True
                    if event.final_agent_id:
                        final_agent_id = event.final_agent_id
                    if event.agent_chain:
                        runtime_agent_chain = list(event.agent_chain)
                    if event.consultations:
                        runtime_consultations = list(event.consultations)
                    if event.embeds:
                        runtime_embeds = list(event.embeds)
                    if event.output_judge_metadata:
                        runtime_output_judge = dict(event.output_judge_metadata)
                    # On n'émet pas le `done` ici — on le fera après la
                    # persistance avec un vrai `message_id`.
                    break
        except LLMError as exc:
            # Idem branche `event.type == "error"` ci-dessus : on émet
            # l'erreur SSE puis on persiste un fallback + on yield un
            # done propre, pour ne pas laisser le client en loading
            # infini. Cas atteint si un agent legacy (ex. `default` via
            # `_llm_agent_base`) lève directement une `LLMError` au lieu
            # de la convertir en `AgentEvent(type='error')`.
            logger.warning(
                "assistance.agent.%s llm_error conv=%s exc=%s",
                agent_id,
                conversation_id,
                exc,
            )
            yield {"type": "error", "message": "llm_unavailable"}
            fb_agent = final_agent_id or decision.agent_id
            fb_msg = _persist_error_fallback(
                db,
                conversation_id=conversation_id,
                turn_index=user_idx + 1,
                agent_used=fb_agent,
                error_code="llm_unavailable",
            )
            if fb_msg is not None:
                yield {
                    "type": "done",
                    "message_id": str(fb_msg.id),
                    "completed": False,
                    "agent_used": fb_agent,
                    "message_type": "text",
                }
                logger.info(
                    "assistance.agent.tour_error_fallback "
                    "conv=%s turn=%s agent=%s code=%s",
                    conversation_id,
                    user_idx + 1,
                    fb_agent,
                    "llm_unavailable",
                )
            return

        # Persistance — choisir le bon `message_type` selon ce que le
        # runtime / agent a émis (texte standard vs QCM via runtime).
        # `agent_used_persisted` reflète le sub-agent réellement utilisé
        # (Phase 2b), ou retombe sur `decision.agent_id` (top-level)
        # quand pas de dispatch (Phase 2a/sub-agents non-compliance).
        agent_used_persisted = final_agent_id or decision.agent_id

        # Phase 2c : metadata orchestration multi-agent (audit + future
        # UI BO). On l'attache à `message_payload` (qui devient ainsi
        # toujours présent quand il y a chaînage, même sur un message
        # `text` standard).
        orchestration_meta: dict = {}
        if runtime_agent_chain and len(runtime_agent_chain) > 1:
            orchestration_meta["agent_chain"] = runtime_agent_chain
        if runtime_consultations:
            orchestration_meta["consultations"] = runtime_consultations
        if runtime_output_judge:
            orchestration_meta["product_pipeline_output_judge"] = (
                runtime_output_judge
            )

        # Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). AUTO-QCM
        # post-process : si l'agent a streamé un texte contenant une
        # liste numérotée + question, et qu'aucun QCM n'a été émis via
        # `ask_user_question`, on promote la liste en QCM cliquable
        # **annexé** au message texte. La décision est centralisée
        # dans `decide_auto_qcm` qui applique tous les garde-fous (E) :
        # kill-switch env, whitelist agents, anti-double-QCM,
        # anti-redondance avec embeds CTA, lecture `[OBJECTIVE]`
        # (`stop_pushing`, `next_best_action`).
        # Le payload est :
        #   * persisté dans `message_payload.auto_qcm` (rétro-compat
        #     totale : `message_type` reste `text`, le client qui ne
        #     sait pas lire `auto_qcm` voit juste le texte) ;
        #   * exposé en SSE via la clé `done.auto_qcm` (atomique avec
        #     le `done` final, pas de nouvel event mid-stream).
        # Cf. `CLIENT_DISCOVERY.md` §4 + `docs/arquantix/COGNITIVE_BOT.md`
        # §11 (Lot 7 V1.1 livré).
        auto_qcm_payload: Optional[dict] = None
        try:
            auto_qcm_decision = decide_auto_qcm(
                full_text=full_text,
                agent_id=agent_used_persisted,
                runtime_choices_present=(runtime_choices is not None),
                runtime_embeds=runtime_embeds,
                objective=getattr(decision, "objective", None),
            )
            if auto_qcm_decision.promoted and auto_qcm_decision.candidate:
                cand = auto_qcm_decision.candidate
                auto_qcm_payload = {
                    "prompt": cand.prompt,
                    "options": list(cand.options),
                    "source": "auto_promoted",
                    "truncated": bool(cand.truncated),
                }
                logger.info(
                    "assistance.auto_qcm.emitted conv=%s agent=%s "
                    "items=%d truncated=%s",
                    conversation_id,
                    agent_used_persisted,
                    len(cand.options),
                    cand.truncated,
                )
            else:
                # On log les skips à `debug` pour ne pas spammer en prod
                # mais permettre l'audit en dev.
                logger.debug(
                    "assistance.auto_qcm.skipped conv=%s agent=%s "
                    "reason=%s",
                    conversation_id,
                    agent_used_persisted,
                    auto_qcm_decision.skip_reason,
                )
        except Exception:  # noqa: BLE001 — best-effort, ne kill jamais le tour
            logger.exception(
                "assistance.auto_qcm.decide_failed conv=%s agent=%s",
                conversation_id,
                agent_used_persisted,
            )

        if runtime_choices is not None:
            choices_payload = {
                "options": runtime_choices["options"],
                "allow_freeform": runtime_choices["allow_freeform"],
            }
            if orchestration_meta:
                choices_payload["metadata"] = orchestration_meta
            if runtime_embeds:
                choices_payload["embeds"] = runtime_embeds
            msg = _persist_assistant_message(
                db,
                conversation_id=conversation_id,
                turn_index=user_idx + 1,
                content=runtime_choices["prompt"]
                or "[Question utilisateur]",
                agent_used=agent_used_persisted,
                message_type="choices",
                message_payload=choices_payload,
            )
        else:
            text_payload: Optional[dict] = None
            if orchestration_meta or runtime_embeds or auto_qcm_payload or runtime_output_judge:
                text_payload = {}
                if orchestration_meta:
                    text_payload["metadata"] = orchestration_meta
                if runtime_embeds:
                    text_payload["embeds"] = runtime_embeds
                if auto_qcm_payload:
                    text_payload["auto_qcm"] = auto_qcm_payload
            msg = _persist_assistant_message(
                db,
                conversation_id=conversation_id,
                turn_index=user_idx + 1,
                content=full_text.strip() or "[Réponse vide]",
                agent_used=agent_used_persisted,
                message_type="text",
                message_payload=text_payload,
            )
        if msg is None:
            yield {"type": "error", "message": "conversation_gone"}
            return

        final_message_type = "choices" if runtime_choices is not None else "text"
        # Phase 2c.2 — propage `embeds` au client en live via SSE pour
        # que le widget UI (ex. carte `transaction_detail`) s'instancie
        # immédiatement à la réception du `done`, sans attendre un
        # reload via `/conversations/{id}/messages`. Le payload est
        # déjà persisté en DB ci-dessus dans `message_payload.embeds`,
        # donc un reload aurait fonctionné — ici on évite juste
        # l'aller-retour superflu.
        done_payload: dict = {
            "type": "done",
            "message_id": str(msg.id),
            "completed": completed,
            "agent_used": agent_used_persisted,
            "message_type": final_message_type,
        }
        if runtime_embeds:
            done_payload["embeds"] = runtime_embeds
        # Lot 7 V1.1 — atomicité : l'auto-QCM est livré dans le `done`
        # final (pas un event mid-stream) pour éviter race conditions
        # avec `ask_user_question` et garantir que le client reçoit
        # texte + QCM exactement quand le tour est persisté en DB.
        if auto_qcm_payload:
            done_payload["auto_qcm"] = auto_qcm_payload
        if runtime_output_judge:
            done_payload["product_pipeline_output_judge"] = runtime_output_judge
        yield done_payload

        logger.info(
            "assistance.agent.tour_done conv=%s turn=%s "
            "agent=%s subagent=%s latency_ms=%.0f path=%s "
            "chain=%s consults=%d",
            conversation_id,
            user_idx + 1,
            decision.agent_id,
            agent_used_persisted if agent_used_persisted != decision.agent_id else "-",
            (time.monotonic() - started_at) * 1000,
            final_message_type,
            ">".join(runtime_agent_chain) if runtime_agent_chain else "-",
            len(runtime_consultations) if runtime_consultations else 0,
        )

        # ── Palier 2 D.2 — Consolidation mémoire long-terme ─────────
        # On skip la consolidation si le tour a fini sur un QCM (pas
        # un vrai tour assistant complet) — symétrique avec Phase 1.
        if runtime_choices is None:
            _schedule_consolidation(session_factory, conversation_id)
    except asyncio.CancelledError:
        # Annulation **volontaire** par le client (POST /chat/turn/{id}/cancel,
        # cf. routes.py D.1.4.7 — bouton stop côté mobile).
        #
        # Distinct du disconnect réseau : ici on TUE explicitement le tour
        # → on **ne commit aucun message assistant** en BDD pour respecter
        # l'intention utilisateur (« je veux que ça s'arrête, pas que ça
        # apparaisse plus tard »). Le `finally` ferme la session DB.
        #
        # Re-raise impératif : sinon la task ne se termine pas et reste
        # marquée « en flight » dans `_PENDING_STREAM_TASKS`.
        logger.info(
            "assistance.agent.stream_cancelled conv=%s agent=%s "
            "tokens_streamed=%d latency_ms=%.0f",
            conversation_id,
            agent_id,
            len(full_text),
            (time.monotonic() - started_at) * 1000,
        )
        raise
    except Exception:
        logger.exception("stream_assistant_turn fatal error")
        try:
            yield {"type": "error", "message": "stream_failed"}
        except Exception:
            pass
        # Tentative de commit du partiel si on a au moins quelque chose.
        if full_text.strip():
            try:
                _persist_assistant_message(
                    db,
                    conversation_id=conversation_id,
                    turn_index=user_idx + 1,
                    content=full_text.strip() + "\n\n_[Réponse interrompue]_",
                    agent_used=decision.agent_id,
                    message_type="text",
                    message_payload=None,
                )
            except Exception:
                logger.exception("failed to persist partial assistant message")
    finally:
        try:
            db.close()
        except Exception:
            pass


async def stream_suspended_short_circuit(
    *,
    session_factory,
    conversation_id: UUID,
    user_idx: int,
    client_id: Optional[UUID] = None,
) -> "AsyncIterator[dict]":
    """Stream SSE court-circuité pour acteur `SUSPENDED` (anti-tipping-off).

    Émet le texte standardisé en un seul `delta` puis un `done`, sans
    appeler le router ni les agents LLM. Persiste le message assistant
    dans une session BDD dédiée (survit au disconnect client comme le
    pipeline nominal).

    Sémantique :
      - `agent_used="default"` (pas de mention de l'agent compliance —
        le client ne doit pas pouvoir distinguer ce cas du flux nominal).
      - `message_type="text"`, `message_payload={"reason": "suspended_short_circuit"}`
        (lecture BO uniquement).
      - Aucune consolidation mémoire (pas de tour utile).

    Le commit du `user_msg` a déjà eu lieu en amont (côté route → service)
    via `process_suspended_short_circuit`-style logique. Ici on ne
    persiste QUE le message assistant.
    """
    from typing import AsyncIterator  # local import for runtime hint

    db = session_factory()
    started_at = time.monotonic()
    try:
        yield {"type": "delta", "content": SUSPENDED_RESPONSE_TEXT}

        msg = _persist_assistant_message(
            db,
            conversation_id=conversation_id,
            turn_index=user_idx + 1,
            content=SUSPENDED_RESPONSE_TEXT,
            agent_used=_SUSPENDED_AGENT_USED,
            message_type="text",
            message_payload={"reason": _SUSPENDED_PAYLOAD_REASON},
        )
        if msg is None:
            yield {"type": "error", "message": "conversation_gone"}
            return

        yield {
            "type": "done",
            "message_id": str(msg.id),
            "completed": True,
            "agent_used": _SUSPENDED_AGENT_USED,
            "message_type": "text",
        }

        logger.warning(
            "assistance.actor.short_circuit_stream reason=suspended "
            "client_id=%s conv=%s turn=%s latency_ms=%.0f",
            client_id,
            conversation_id,
            user_idx + 1,
            (time.monotonic() - started_at) * 1000,
        )
    except Exception:
        logger.exception("stream_suspended_short_circuit fatal error")
        try:
            yield {"type": "error", "message": "stream_failed"}
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass


def mark_conversation_read(
    db: Session, *, client_id: UUID, conversation_id: UUID
) -> AssistanceConversation:
    """Marque la conversation comme lue (D.1.4.2).

    Posé sur appel client explicite `POST /conversations/{id}/read` après
    affichage d'une réponse assistant côté UI. La pastille « non lu »
    disparaît dès que `last_read_at >= last_assistant_message_at`.

    Lève `ValueError("conversation_not_found")` si la conversation
    n'existe pas pour ce client.
    """
    conv = get_conversation_for_client(
        db, client_id=client_id, conversation_id=conversation_id
    )
    if conv is None:
        raise ValueError("conversation_not_found")

    conv.last_read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conv)
    return conv

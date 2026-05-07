"""FastAPI router — `/api/app/assistance/chat/turn`.

MVP D.0.1 + D.0.2 + D.1.1 :
- 401 sans bearer token (`get_current_user_or_admin`).
- 403 si JWT valide mais `auth.client_id is None` (ex. admin sans client lié).
- Rate-limit 30 req/min/client (configurable via `ASSISTANCE_RL_*`).
- Persistence des conversations + tours en base.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from services.assistance.config import (
    assistance_voice_max_audio_bytes,
    assistance_voice_whisper_enabled,
)
from services.assistance.llm import LLMError
from services.assistance.rate_limit import check_assistance_quota
from services.assistance.voice import (
    VoiceTranscriptionError,
    transcribe_audio_with_whisper,
)
from services.assistance.schemas import (
    ChatTurnRequest,
    ChatTurnResponse,
    ConversationListResponse,
    ConversationMessageItem,
    ConversationMessagesResponse,
    ConversationSummaryItem,
    DEFAULT_CONVERSATIONS_LIMIT,
    DEFAULT_MESSAGES_LIMIT,
    MAX_CONVERSATIONS_LIMIT,
    MAX_MESSAGES_LIMIT,
)
from services.assistance.agents.tools.shared import ActorKind, classify_actor
from services.auth.client_id_resolver import patch_auth_client_id_from_person
from services.assistance.service import (
    get_conversation_for_client,
    list_conversations_for_client,
    list_messages_for_client,
    mark_conversation_read,
    process_chat_turn,
    process_suspended_short_circuit,
    start_chat_turn,
    start_suspended_chat_turn,
    stream_assistant_turn,
    stream_suspended_short_circuit,
)
from services.auth.dependencies import get_current_user_or_admin
from services.auth.models import AuthContext

# Registre global des tasks de streaming en cours (D.1.4.5 — Revolut-grade).
#
# Conserve une référence à chaque pipeline async pour deux raisons :
#
# 1. **Anti-GC** : empêche Python de garbage-collecter une task encore en
#    flight si le client HTTP se déconnecte en plein stream. Ainsi le
#    commit final côté serveur a toujours lieu — la prochaine ouverture
#    de la conv affichera la réponse complète.
#
# 2. **Cancel volontaire** (D.1.4.7) : indexé par `str(conversation_id)`
#    pour permettre à l'endpoint POST `/chat/turn/{conv_id}/cancel`
#    d'arrêter la génération en cours quand l'utilisateur clique le
#    bouton stop côté mobile. La task est `cancel()`-ée → `CancelledError`
#    se propage dans `stream_assistant_turn`, qui n'attrape que
#    `Exception` (pas `BaseException`) — donc aucun message assistant
#    n'est commité en BDD pour ce tour.
#
# Note : si plusieurs tours s'empilent sur la même conv (cas pathologique :
# deux POST /chat/turn/stream successifs avant la fin du premier), la
# 2ᵉ task écrase la 1ʳᵉ dans le dict mais le `add_done_callback` est
# tolérant (cf. `_unregister_pending_task`).
_PENDING_STREAM_TASKS: dict[str, asyncio.Task] = {}


def _unregister_pending_task(conv_id_str: str, task: asyncio.Task) -> None:
    """Callback de désinscription du registre des tasks en flight.

    Vérifie que la task qu'on retire est bien celle enregistrée pour
    cette conv (sinon une task plus récente vient de prendre la place
    — on ne la touche pas).
    """
    current = _PENDING_STREAM_TASKS.get(conv_id_str)
    if current is task:
        _PENDING_STREAM_TASKS.pop(conv_id_str, None)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app/assistance", tags=["assistance"])


def _chat_turn_response_model(conv, assistant_msg) -> ChatTurnResponse:
    """Expose ``embeds`` / ``auto_qcm`` pour les clients non-stream (parité SSE ``done``)."""
    mp = assistant_msg.message_payload if assistant_msg.message_payload else None
    embeds = None
    auto_qcm = None
    if isinstance(mp, dict):
        embeds = mp.get("embeds")
        auto_qcm = mp.get("auto_qcm")

    return ChatTurnResponse(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        content=assistant_msg.content,
        agent_used=assistant_msg.agent_used,
        message_type=assistant_msg.message_type or "text",
        embeds=embeds,
        auto_qcm=auto_qcm,
        message_payload=assistant_msg.message_payload,
    )


def _compute_unread_state(row) -> tuple[bool, bool]:
    """Retourne `(awaiting_response, unread_response)` (D.1.4.6).

    Deux états distincts, mutuellement non exclusifs en théorie mais
    `awaiting_response` prend sémantiquement le pas (puisque tant qu'aucune
    réponse n'est commitée, l'éventuelle réponse précédente reste lue ou
    non selon `last_read_at`) — on laisse le client choisir l'icône à
    afficher en priorisant `awaiting_response` :

    - **awaiting_response** : `last_message_at > last_assistant_message_at`
      (ou `last_assistant_message_at IS NULL` alors que `last_message_at`
      existe). Sémantique : l'utilisateur a posé une question, l'assistant
      n'a pas encore commité sa réponse (stream en cours / échec / offline).
      → pastille grise + horloge côté client.

    - **unread_response** : `last_assistant_message_at > last_read_at`
      (avec `last_read_at IS NULL` traité comme epoch). Sémantique : une
      réponse assistant a été commitée et l'utilisateur n'a pas encore
      ouvert la conversation depuis.
      → pastille indigo + check côté client.

    Les deux signalent « quelque chose de nouveau » et alimentent le flag
    legacy `unread` (=`awaiting_response OR unread_response`) pour les
    anciens clients.
    """
    last_message = getattr(row, "last_message_at", None)
    last_assistant = getattr(row, "last_assistant_message_at", None)
    last_read = getattr(row, "last_read_at", None)

    awaiting = False
    if last_message is not None and (
        last_assistant is None or last_assistant < last_message
    ):
        awaiting = True

    unread_response = False
    if last_assistant is not None:
        if last_read is None or last_assistant > last_read:
            unread_response = True

    return awaiting, unread_response


def _require_client(auth: AuthContext, db: Session) -> None:
    """Garde-fou commun : 403 si le bearer JWT n'est pas associé à un client.

    **Fix BUG B (cache identité jwt_only)** :
    La résolution `resolve_identity_for_auth_context_fast` peut retourner
    un `AuthContext` avec `client_id=None` alors que le client existe en
    base. Cas reproductible : cache identité en miss + JWT contient un
    `person_id` → mode `jwt_only` → pas de lookup DB → `client_id` à None.
    Conséquence visible : 403 `client_required` sur `/conversations`
    poll en boucle (constatée le 02 mai), pendant que `/chat/turn` peut
    encore passer si un appel précédent a chauffé le cache.

    Comportement de ce garde-fou :
      1. Si `auth.client_id` est déjà résolu → OK (chemin nominal, 0 cost).
      2. Sinon, si `auth.person_id` est connu → lookup DB ciblé
         `pe_clients.id WHERE person_id = ?`, et on patch `auth.client_id`
         en place (Pydantic v2 mutable). Pas de warm cache global ici
         pour rester scoped au seul endpoint qui en a besoin — on évite
         d'introduire un side-effect global depuis le module assistance.
      3. Sinon → 403 `client_required` (cas légitime : admin sans client
         lié, JWT mal formé, etc.).
    """
    if patch_auth_client_id_from_person(auth, db):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": {
                "code": "client_required",
                "message": "This endpoint requires a client-scoped session.",
            }
        },
    )


def _classify_chat_actor(auth: AuthContext, db: Session) -> ActorKind:
    """Garde-fou + classification d'acteur pour `/chat/*` (Phase 2a).

    Combine le patch BUG B de [_require_client] (cache identité jwt_only)
    avec `classify_actor()` pour distinguer les 4 types d'acteurs avant
    tout dispatch agent (cf. `MULTI_AGENTS_RUNTIME.md` § 4 et
    `AUDIT_AUTH_IDENTITIES.md` § 7).

    Mapping résultat → comportement :
      - `ADMIN_BO`     → 403 `actor_admin_bo` (décision audit identité :
        les admins backoffice n'ont rien à faire dans le chat client).
      - `ONBOARDING`   → 403 `client_required` (legacy — le compte client
        n'est pas encore créé. Sera spécialisé en Phase 3 quand l'agent
        registration sera branché).
      - `CUSTOMER`     → retourne `ActorKind.CUSTOMER` (flux nominal).
      - `SUSPENDED`    → retourne `ActorKind.SUSPENDED` (le caller doit
        orchestrer le court-circuit anti-tipping-off).

    Le caller doit ensuite :
      - vérifier le rate-limit `check_assistance_quota` (qui s'applique
        identiquement à CUSTOMER et SUSPENDED — un suspended peut tenter
        de spam, on doit le freiner),
      - dispatcher selon `actor` (court-circuit ou flux nominal).
    """
    patch_auth_client_id_from_person(auth, db)
    actor = classify_actor(auth, db)

    if actor == ActorKind.ADMIN_BO:
        logger.warning(
            "assistance.chat.actor_admin_bo_blocked user_id=%s person_id=%s",
            getattr(auth, "user_id", None),
            getattr(auth, "person_id", None),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "actor_admin_bo",
                    "message": "Backoffice admins cannot use the assistance chat.",
                }
            },
        )

    if actor == ActorKind.ONBOARDING:
        # Compatibilité Phase 2a : on garde le code legacy `client_required`
        # tant que le mobile n'a pas appris à reconnaître `actor_onboarding`.
        # Spécialisation prévue en Phase 3 (registration agent).
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "client_required",
                    "message": "This endpoint requires a client-scoped session.",
                }
            },
        )

    return actor


@router.post("/chat/turn", response_model=ChatTurnResponse)
def chat_turn(
    body: ChatTurnRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> ChatTurnResponse:
    actor = _classify_chat_actor(auth, db)

    check_assistance_quota(str(auth.client_id))

    try:
        if actor == ActorKind.SUSPENDED:
            conv, assistant_msg = process_suspended_short_circuit(
                db,
                client_id=auth.client_id,
                conversation_id=body.conversation_id,
                user_content=body.content,
            )
        else:
            conv, assistant_msg = process_chat_turn(
                db,
                client_id=auth.client_id,
                conversation_id=body.conversation_id,
                user_content=body.content,
                agent_hint=body.agent_hint,
                person_id=auth.person_id,
                actor_kind=actor,
                user_id=auth.user_id,
            )
    except ValueError as exc:
        code = str(exc)
        if code in {"conversation_not_found", "conversation_closed"}:
            http_status = status.HTTP_404_NOT_FOUND if code == "conversation_not_found" else status.HTTP_409_CONFLICT
            raise HTTPException(
                status_code=http_status,
                detail={"error": {"code": code, "message": code.replace("_", " ")}},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": code, "message": code.replace("_", " ")}},
        ) from exc
    except LLMError as exc:
        logger.warning("assistance.chat_turn llm_error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "llm_unavailable",
                    "message": "Assistance LLM is temporarily unavailable.",
                }
            },
        ) from exc

    return _chat_turn_response_model(conv, assistant_msg)


def _sse_format(event_type: str, data: dict) -> str:
    """Formate un event SSE conforme `text/event-stream`.

    Format :
        event: <type>\\n
        data: <json>\\n
        \\n

    Le double `\\n\\n` final marque la fin de l'event côté EventSource.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/turn/stream")
async def chat_turn_stream(
    body: ChatTurnRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> StreamingResponse:
    """Streaming SSE d'un tour assistant (D.1.4.5 — phase 2).

    Flow :
    1. Auth + rate-limit.
    2. Crée la conv + commit user (réutilise [start_chat_turn]).
    3. Émet immédiatement un event `started` avec `conversation_id` et
       `user_message_id` (le client peut persister l'ID en local storage
       dès la 1ʳᵉ frame, avant même le 1ᵉʳ token assistant).
    4. Lance [stream_assistant_turn] dans une task référencée globalement,
       qui consomme OpenAI en stream et alimente une queue.
    5. Pour chaque event yieldé par la task, ré-émet en SSE.
    6. Le commit du message assistant en BDD a lieu **dans la task**, donc
       même si le client se déconnecte, la réponse complète sera persistée
       et accessible via `GET /messages` au prochain refresh.

    Format SSE applicatif :
    - `event: started` — `{conversation_id, user_message_id}`
    - `event: delta`   — `{content: '<token>'}`
    - `event: done`    — `{message_id, completed: bool}`
    - `event: error`   — `{message: '<code>'}`
    """
    actor = _classify_chat_actor(auth, db)
    check_assistance_quota(str(auth.client_id))

    # Phase 1 — création conv + commit user (+ routing si CUSTOMER).
    # Pour `SUSPENDED` : on saute le router et l'AgentInput (zero token
    # OpenAI) — le court-circuit standardisé sera émis en Phase 2.
    agent_input = None
    decision = None
    try:
        if actor == ActorKind.SUSPENDED:
            conv, user_msg, user_idx = start_suspended_chat_turn(
                db,
                client_id=auth.client_id,
                conversation_id=body.conversation_id,
                user_content=body.content,
            )
        else:
            conv, user_msg, agent_input, decision, user_idx = start_chat_turn(
                db,
                client_id=auth.client_id,
                conversation_id=body.conversation_id,
                user_content=body.content,
                agent_hint=body.agent_hint,
                person_id=auth.person_id,
            )
    except ValueError as exc:
        code = str(exc)
        if code in {"conversation_not_found", "conversation_closed"}:
            http_status = (
                status.HTTP_404_NOT_FOUND
                if code == "conversation_not_found"
                else status.HTTP_409_CONFLICT
            )
            raise HTTPException(
                status_code=http_status,
                detail={"error": {"code": code, "message": code.replace("_", " ")}},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": code, "message": code.replace("_", " ")}},
        ) from exc

    conversation_id = conv.id
    user_message_id = str(user_msg.id)
    conversation_id_str = str(conversation_id)
    client_id_for_agent = auth.client_id  # capturé pour la closure
    is_suspended = actor == ActorKind.SUSPENDED

    # Phase 2 — relai SSE alimenté par la task background.
    queue: asyncio.Queue = asyncio.Queue()

    async def _drive_pipeline() -> None:
        """Tourne en background, alimente la queue, survit au disconnect client."""
        try:
            if is_suspended:
                async for ev in stream_suspended_short_circuit(
                    session_factory=SessionLocal,
                    conversation_id=conversation_id,
                    user_idx=user_idx,
                    client_id=client_id_for_agent,
                ):
                    await queue.put(ev)
            else:
                async for ev in stream_assistant_turn(
                    session_factory=SessionLocal,
                    conversation_id=conversation_id,
                    user_idx=user_idx,
                    agent_input=agent_input,
                    decision=decision,
                    client_id=client_id_for_agent,
                    actor_kind=actor,
                    user_id=auth.user_id,
                    person_id=auth.person_id,
                ):
                    await queue.put(ev)
        except Exception:
            logger.exception("stream pipeline crashed")
            try:
                await queue.put({"type": "error", "message": "stream_failed"})
            except Exception:
                pass
        finally:
            await queue.put(None)

    task = asyncio.create_task(_drive_pipeline())
    _PENDING_STREAM_TASKS[conversation_id_str] = task
    task.add_done_callback(
        lambda t, cid=conversation_id_str: _unregister_pending_task(cid, t)
    )

    async def event_stream():
        # 1ʳᵉ frame : ID de conversation + message user, dispo avant le 1ᵉʳ token.
        yield _sse_format(
            "started",
            {
                "conversation_id": conversation_id_str,
                "user_message_id": user_message_id,
            },
        )
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                event_type = item.pop("type", "delta")
                yield _sse_format(event_type, item)
        except asyncio.CancelledError:
            # Client disconnect : la task continue grâce à _PENDING_STREAM_TASKS,
            # le commit BDD a lieu côté serveur.
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            # Désactive le buffering côté reverse-proxy nginx s'il y en a un.
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        pattern="^(active|closed)$",
    ),
    limit: int = Query(
        default=DEFAULT_CONVERSATIONS_LIMIT,
        ge=1,
        le=MAX_CONVERSATIONS_LIMIT,
    ),
    before: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> ConversationListResponse:
    """Liste des conversations du client courant (D.1.4).

    Triées par `last_message_at` décroissant (fallback `created_at`). Cursor-
    based pagination via `before` (ISO 8601). `status=active|closed` permet
    de filtrer ; sans filtre on retourne tout.
    """
    _require_client(auth, db)

    rows = list_conversations_for_client(
        db,
        client_id=auth.client_id,
        status=status_filter,
        limit=limit,
        before=before,
    )

    items: list[ConversationSummaryItem] = []
    for row in rows:
        awaiting, unread_response = _compute_unread_state(row)
        items.append(
            ConversationSummaryItem(
                id=row.id,
                title=row.title,
                status=row.status,
                created_at=row.created_at,
                last_message_at=row.last_message_at,
                awaiting_response=awaiting,
                unread_response=unread_response,
                unread=awaiting or unread_response,
            )
        )

    return ConversationListResponse(conversations=items)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
def list_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(
        default=DEFAULT_MESSAGES_LIMIT,
        ge=1,
        le=MAX_MESSAGES_LIMIT,
    ),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> ConversationMessagesResponse:
    """Historique des messages d'une conversation (D.1.6 — reprise visuelle).

    Retourne 404 si la conversation n'appartient pas au client courant
    (volontaire : pas de leak entre clients, on ne distingue pas
    « inexistante » de « pas à toi »).
    """
    _require_client(auth, db)

    try:
        conv, rows = list_messages_for_client(
            db,
            client_id=auth.client_id,
            conversation_id=conversation_id,
            limit=limit,
        )
    except ValueError as exc:
        if str(exc) == "conversation_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "conversation_not_found",
                        "message": "Conversation not found",
                    }
                },
            ) from exc
        raise

    return ConversationMessagesResponse(
        conversation_id=conv.id,
        title=conv.title,
        status=conv.status,
        messages=[
            ConversationMessageItem(
                id=row.id,
                turn_index=row.turn_index,
                role=row.role,
                content=row.content,
                created_at=row.created_at,
                # D.1.6.1 — sans `message_type` + `message_payload`, le
                # client perd au reload de la conversation : les QCM
                # multi-agents (`message_type='choices'`), les embeds UI
                # (`message_payload.embeds[]`, ex. carte `transaction_detail`)
                # et la metadata multi-agent (`agent_used`, chain).
                # Persistés en DB ; il suffisait de les ré-exposer au
                # GET historique.
                message_type=row.message_type or "text",
                message_payload=row.message_payload,
            )
            for row in rows
        ],
    )


@router.post(
    "/conversations/{conversation_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def post_conversation_read(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> Response:
    """Marque une conversation comme lue (D.1.4.2).

    Le client (Flutter) appelle ce endpoint :
    - juste après avoir affiché la réponse retournée par `/chat/turn`,
    - juste après avoir chargé l'historique via `/messages`.

    Convention : un nouveau message assistant est « non lu » par défaut ;
    seul ce POST explicite met à jour `last_read_at`. La pastille côté
    liste de conversations disparaît dès que
    `last_read_at >= last_assistant_message_at`.

    Retourne 204 No Content (idempotent) ou 404 si la conversation
    n'appartient pas au client courant.
    """
    _require_client(auth, db)

    try:
        mark_conversation_read(
            db,
            client_id=auth.client_id,
            conversation_id=conversation_id,
        )
    except ValueError as exc:
        if str(exc) == "conversation_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "conversation_not_found",
                        "message": "Conversation not found",
                    }
                },
            ) from exc
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/chat/turn/{conversation_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def cancel_chat_turn(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> Response:
    """Annule volontairement le tour assistant en cours sur une conversation.

    UX cible (D.1.4.7) : bouton « stop » côté mobile, équivalent du
    carré ChatGPT. L'utilisateur clique → la `Task` du pipeline async
    correspondante est `cancel()`-ée. `CancelledError` se propage à
    `stream_assistant_turn` qui n'attrape que `Exception` (pas
    `BaseException`) — donc **aucun message assistant n'est commité**
    en BDD pour ce tour. Le `finally` ferme proprement la session.

    Sémantique :
      - **Idempotent** : retourne 204 même s'il n'y a pas de task en
        cours (déjà finie / jamais existé). On ne révèle pas l'état
        d'autres clients.
      - **Ownership obligatoire** : 404 si la conversation n'appartient
        pas au client courant, **avant** toute interaction avec le
        registre des tasks (anti-énumération).
      - **Distinct du disconnect réseau** : un disconnect HTTP du client
        laisse la task vivante (commit du message). Seul cet endpoint
        explicite tue la task.
    """
    _require_client(auth, db)

    # Garde d'ownership : on ne doit jamais permettre à un client A de
    # tuer une génération de B, même si A connaît l'UUID de B (anti-
    # IDOR). On ne révèle pas l'existence : 404 quoi qu'il arrive si
    # la conversation n'appartient pas au client courant.
    conv = get_conversation_for_client(
        db, client_id=auth.client_id, conversation_id=conversation_id
    )
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "conversation_not_found",
                    "message": "Conversation not found",
                }
            },
        )

    conv_id_str = str(conversation_id)
    task = _PENDING_STREAM_TASKS.get(conv_id_str)
    if task is not None and not task.done():
        # `cancel()` propage CancelledError à la prochaine `await` de la
        # coroutine pipeline (typiquement le `await event_iter.__anext__()`
        # dans `stream_assistant_turn`). Aucun commit BDD ne sera fait.
        task.cancel()
        logger.info(
            "assistance.agent.cancelled conv=%s client=%s",
            conv_id_str,
            auth.client_id,
        )
    else:
        # Pas de task en flight pour cette conv : soit déjà finie, soit
        # jamais existé. C'est OK — l'endpoint est idempotent côté client.
        logger.debug(
            "assistance.agent.cancel_noop conv=%s client=%s",
            conv_id_str,
            auth.client_id,
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# Voice input (D.1.4.8) — uniquement pour le moteur Whisper côté mobile.
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/voice/transcribe",
    response_model=None,
)
async def post_voice_transcribe(
    audio: UploadFile = File(..., description="Fichier audio (m4a, wav, mp3, …) ≤ 10 MB"),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_user_or_admin),
) -> dict[str, str]:
    """Transcrit un fichier audio uploadé via l'API OpenAI Whisper.

    Utilisé uniquement quand le mobile tourne avec
    `ASSISTANCE_VOICE_ENGINE=whisper` (le défaut `native` ne touche pas
    à cet endpoint, la transcription est locale).

    Sécurité :
    - **Auth obligatoire** (Bearer JWT). 401 sinon.
    - **Client lié** obligatoire (pas d'admin sans `client_id`). 403 sinon.
    - **Kill-switch** `ASSISTANCE_VOICE_WHISPER_ENABLED` :
        - false (défaut) → 503 immédiat, sans appel OpenAI.
        - true  → on traite la requête.
    - **Taille max** : on coupe à `ASSISTANCE_VOICE_MAX_BYTES` (10 MB
      par défaut) pour éviter un upload géant qui exploserait le coût.
    - Pas de rate-limit dédié pour l'instant : le rate-limit chat
      (`check_assistance_quota`) couvre déjà l'envoi du message qui suit.
      Si ça devient un vecteur d'abus on en ajoutera un séparé.
    - **Aucune persistance** : ni l'audio ni le texte ne sont stockés
      ici. C'est le tour suivant `/chat/turn` qui persistera le message
      utilisateur (avec le texte transcrit).

    Réponse : `{ "transcript": "…" }` (200) ou erreur structurée.
    """
    _require_client(auth, db)

    if not assistance_voice_whisper_enabled():
        # Kill-switch côté serveur. L'UI mobile peut afficher un fallback
        # vers le moteur natif.
        logger.info(
            "assistance.voice disabled client=%s",
            auth.client_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "voice_whisper_disabled",
                    "message": "Voice transcription is disabled on this server.",
                }
            },
        )

    # Lecture du body (FastAPI a déjà streamé l'upload). On lit la
    # totalité en mémoire — Whisper a besoin du fichier complet et la
    # limite de 10 MB rend ça acceptable.
    max_bytes = assistance_voice_max_audio_bytes()
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "voice_audio_empty",
                    "message": "Empty audio file.",
                }
            },
        )
    if len(audio_bytes) > max_bytes:
        logger.warning(
            "assistance.voice oversize client=%s bytes=%d max=%d",
            auth.client_id,
            len(audio_bytes),
            max_bytes,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "voice_audio_too_large",
                    "message": f"Audio file exceeds {max_bytes} bytes.",
                }
            },
        )

    filename = audio.filename or "voice.m4a"
    # Quelques clients (notamment iOS) envoient `application/octet-stream`
    # — on retombe sur audio/m4a qui est ce que Whisper attend pour aacLc.
    content_type = audio.content_type or "audio/m4a"
    if content_type == "application/octet-stream":
        content_type = "audio/m4a"

    try:
        transcript = await transcribe_audio_with_whisper(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            language_hint="fr",  # Vancelian = app FR-first.
        )
    except VoiceTranscriptionError as exc:
        logger.warning(
            "assistance.voice transcribe_failed client=%s err=%s",
            auth.client_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "voice_transcribe_failed",
                    "message": "Audio transcription failed.",
                }
            },
        ) from exc

    # Trim final pour ne pas envoyer d'espaces parasites au client.
    transcript = transcript.strip()
    return {"transcript": transcript}

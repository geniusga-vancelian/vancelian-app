"""Schémas Pydantic — payload `/api/app/assistance/*`."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Garde-fou contre les payloads abusifs (prompt-flood).
MAX_USER_CONTENT_LEN = 4000

# Pagination historique (D.1.6).
DEFAULT_MESSAGES_LIMIT = 100
MAX_MESSAGES_LIMIT = 200

# Pagination liste de conversations (D.1.4).
DEFAULT_CONVERSATIONS_LIMIT = 50
MAX_CONVERSATIONS_LIMIT = 100


class ChatTurnRequest(BaseModel):
    """Tour utilisateur. `conversation_id` absent → nouvelle conversation.

    Multi-agents Phase 1 (cf. docs/arquantix/MULTI_AGENTS.md § 1.9.3) :
    `agent_hint` permet de **shortcut** le router quand l'utilisateur a
    cliqué une option d'un QCM précédent. Doit être un `agent_id` connu
    (`compliance`, `advisor`, `product`, `market`, `action`, `trust`, `default`) ou None.
    """

    conversation_id: Optional[UUID] = None
    content: str = Field(..., min_length=1, max_length=MAX_USER_CONTENT_LEN)
    agent_hint: Optional[str] = Field(
        default=None,
        description=(
            "Identifiant d'agent à invoquer directement, court-circuite "
            "le router. Utile après clic sur une option d'un QCM `choices`."
        ),
    )


class ChatTurnResponse(BaseModel):
    """Tour assistant + meta alignée sur l'événement SSE ``done``.

    Les champs ``embeds`` / ``auto_qcm`` reflètent le ``done`` stream pour
    que les clients **non-stream** puissent instancier widgets + QCM.
    Les messages ``text`` avec embeds seulement ont aussi ces clés tirées
    de ``message_payload``.
    """

    conversation_id: UUID
    message_id: UUID
    content: str
    agent_used: Optional[str] = None
    message_type: Optional[str] = Field(
        default="text",
        description="''text'' | ''choices'' (router ou ask_user_question).",
    )
    embeds: Optional[List[dict[str, Any]]] = Field(
        default=None,
        description="Cartes structurées (transaction_detail, etc.).",
    )
    auto_qcm: Optional[dict[str, Any]] = Field(
        default=None,
        description="QCM annexé automatiquement au message texte (Lot 7).",
    )
    message_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Payload brut (options QCM ``choices``, métadonnées, etc.).",
    )


class ConversationMessageItem(BaseModel):
    """Un message historique (user ou assistant) — sortie de l'endpoint historique."""

    id: UUID
    turn_index: int
    role: str
    content: str
    created_at: datetime
    # Multi-agents Phase 1 (cf. docs/arquantix/MULTI_AGENTS.md § 4).
    agent_used: Optional[str] = None
    message_type: str = "text"
    message_payload: Optional[dict] = None


class ConversationMessagesResponse(BaseModel):
    """Historique d'une conversation (D.1.6) — ordre chronologique croissant.

    Utilisé par Flutter au démarrage du Search Screen quand un
    `conversation_id` est restauré depuis le secure storage : on rejoue les
    derniers tours dans l'UI sans avoir à les regénérer côté LLM.
    """

    conversation_id: UUID
    title: Optional[str]
    status: str
    messages: List[ConversationMessageItem]


class ConversationSummaryItem(BaseModel):
    """Résumé d'une conversation pour la page « Mes conversations » (D.1.4).

    On évite ici les listes de messages : juste les méta-données pour afficher
    une carte (titre, statut, date dernier message). Si l'utilisateur tape sur
    la carte, le client va appeler `…/conversations/{id}/messages` pour
    obtenir le détail (D.1.6).
    """

    id: UUID
    title: Optional[str]
    status: str
    created_at: datetime
    last_message_at: Optional[datetime]

    # D.1.4.6 — états « pastille » distincts pour pouvoir choisir l'icône
    # côté client (gris+horloge vs indigo+check).
    #
    # `awaiting_response` : l'utilisateur vient de poser une question,
    # l'assistant n'a pas encore commité sa réponse (stream en cours,
    # ou échec, ou client offline). Pastille **grise + horloge**.
    awaiting_response: bool = False
    # `unread_response` : l'assistant a commité une réponse postérieure
    # à `last_read_at`. Pastille **indigo + check**.
    unread_response: bool = False
    # D.1.4.2 (back-compat) — true ⇒ il y a quelque chose de nouveau à voir.
    # Équivalent à `awaiting_response OR unread_response`. Conservé pour les
    # anciens clients qui ne distinguent pas les deux états.
    unread: bool = False


class ConversationListResponse(BaseModel):
    """Liste paginée des conversations d'un client (D.1.4)."""

    conversations: List[ConversationSummaryItem]

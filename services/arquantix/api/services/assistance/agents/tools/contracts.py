"""Contrats publics du runtime des tools agents — Phase 2a.

Ce module définit :

  - `AutonomyLevel` (`L0` | `L1` | `L2` | `L3`)  : enum + helpers.
  - `ToolContext`        : injection runtime → tool (filtré, sans AuthContext brut).
  - `ToolSpec`           : `TypedDict` proche de la function-spec OpenAI,
                           augmentée des métadonnées internes (autonomy_level,
                           agent_id).
  - `ToolModule` (Protocol) : contrat statique d'un module-tool.

Spec de référence : `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 2.

Aucune dépendance LLM/HTTP : ce module est pure-types pour casser tout
risque d'import circulaire entre runtime ↔ tools ↔ repositories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Literal,
    Optional,
    Protocol,
    TypedDict,
    runtime_checkable,
)

from sqlalchemy.orm import Session

from services.assistance.agents.tools.shared.classify_actor import ActorKind


AutonomyLevel = Literal["L0", "L1", "L2", "L3"]
"""Niveau d'autonomie d'un tool. Cf. RUNTIME § 3.

  - `L0` : read-only, idempotent. Aucun side-effect.
  - `L1` : advisory (proposition journalisée, validation humaine async).
  - `L2` : action mutative low-risk, auto-exécutée + journalisée.
  - `L3` : action mutative high-risk, jamais Phase 2.
"""


# ─────────────────────────────────────────────────────────────────────────
# ToolContext — injection runtime → tool
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolContext:
    """Contexte filtré injecté à chaque appel de tool.

    Garanties de sécurité :
      - Pas d'`AuthContext` brut → impossible pour un tool de muter le
        flag `is_admin` ou de consulter le `zero_trust_role`.
      - Tous les IDs sont stringifiés (UUID hex) pour éviter les fuites
        d'objets ORM.
      - `db` est une session SQLAlchemy ouverte (rollback géré côté
        runtime).

    Cf. RUNTIME § 2.3.
    """

    db: Session
    client_id: Optional[str]
    person_id: Optional[str]
    user_id: int
    actor_kind: ActorKind
    agent_id: str
    conversation_id: str
    iteration: int
    audit_session_id: str
    correlation_id: str
    # Phase 2c.2 — Collecteur d'embeds UI structurés que les tools peuvent
    # alimenter pour faire afficher un widget dédié côté Flutter (carte
    # `transaction_detail`, etc.). Le runtime aggrège ces embeds après
    # chaque itération et les inclut dans `AgentEvent(type='done')`.
    #
    # Le champ est une `list` mutable : `frozen=True` empêche la
    # réassignation du field mais autorise `ctx.embeds_to_emit.append(...)`,
    # qui est le seul usage attendu côté tool.
    #
    # Convention d'item : `dict` JSON-safe contenant au moins une clé
    # `type` (str) parmi le catalogue côté Flutter
    # (`AssistanceEmbed.type`). Ex. :
    #   {"type": "transaction_detail",
    #    "transaction_id": "abc-...",
    #    "actions": [{"kind": ..., "label": ..., "deep_link": ...}, ...]}
    embeds_to_emit: list[dict] = field(default_factory=list)

    # ─────────────────────────────────────────────────────────────────
    # Cognitive Bot v4 — Lot 2 (2026-05-06) — état cognitif du tour
    # ─────────────────────────────────────────────────────────────────
    #
    # Snapshot **dict-form** (pas dataclass typée) calculé en amont par
    # ``services.assistance.service.start_chat_turn`` puis transporté
    # via ``agent_input.memory_state``. Le runtime
    # (``agent_loop.run_agent_loop``) recopie ces dicts dans le
    # ``ToolContext`` pour les rendre lisibles depuis n'importe quel
    # tool — ex. ``select_wiki_pages`` peut adapter le ``selection_reason``
    # selon ``emotional_intent``, ``read_compliance_state`` peut
    # privilégier un message court si ``stop_pushing=True``, etc.
    #
    # Pourquoi ``dict`` et pas ``CognitiveState`` typé :
    #   * pas de cycle d'import (``contracts.py`` est très bas niveau).
    #   * sérialisable trivialement (audit / log / propagation cross-agent).
    #   * fidèle au format réel transporté via ``memory_state``.
    #
    # Pour typer côté tool, faire :
    #   ``CognitiveState.from_dict(ctx.cognitive_state)``
    # ou utiliser les helpers de
    # ``services.assistance.agents.tools.shared.cognitive_context``.
    #
    # Convention :
    #   * ``None`` = état non disponible (cas test, démarrage avant
    #     calcul, ou échec best-effort en amont). Les tools doivent
    #     traiter ``None`` comme un ``NEUTRAL/discovery`` implicite.
    #   * Sinon, ``dict`` JSON-safe conforme à
    #     ``CognitiveState.to_dict()`` /
    #     ``ConversationObjective.to_dict()``.
    cognitive_state: Optional[dict] = None
    objective: Optional[dict] = None

    # ─────────────────────────────────────────────────────────────────
    # Cognitive Bot v4 — Lot 4 (2026-05-06) — topic mémoire cross-tour
    # ─────────────────────────────────────────────────────────────────
    #
    # Snapshot **dict-form** du slot ``current_topic`` persisté côté
    # ``AssistanceConversation.current_topic`` (cf.
    # ``services.assistance.conversation_topic``). Lu jusqu'ici
    # uniquement par le router pour stabiliser les follow-ups
    # déictiques (« et lui ? », « combien ça coûte ? »…). Lot 4
    # l'expose aussi aux tools des sub-agents pour qu'ils puissent :
    #
    #   * ``select_wiki_pages`` : prioriser les fiches liées au sujet
    #     en cours sans réinterpréter la requête.
    #   * ``show_instrument_card`` / ``show_bundle_detail`` : valider
    #     que le sujet ciblé correspond bien au sujet actif (anti
    #     dérive de tool call).
    #   * Tout tool ``read_*`` : enrichir un payload texte avec un
    #     contexte « tu parles de X » sans dépendre du history LLM.
    #
    # Schéma typique (cf. ``conversation_topic.infer_topic_from_tool_call``)
    #   {
    #     "kind": "vancelian_product" | "instrument" | "topic_other",
    #     "product_code": "TOP5" | None,
    #     "instrument_symbol": "BTC" | None,
    #     "agent_owner": "product",
    #     "set_at_turn": 3,
    #     "set_by_tool": "show_bundle_detail",
    #     "confidence": 0.95,
    #     "set_at": "2026-05-06T11:42:00Z",
    #   }
    #
    # Convention :
    #   * ``None`` = pas de topic actif (tour 0, ou explicitement
    #     ``clear_topic``). Les tools traitent l'absence comme
    #     « topic non contraint ».
    #   * Sinon, ``dict`` JSON-safe ; les tools doivent toujours passer
    #     par les helpers de
    #     ``services.assistance.agents.tools.shared.topic_context``
    #     pour la lecture défensive.
    current_topic: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────
# ToolSpec — contrat OpenAI augmenté des métadonnées internes
# ─────────────────────────────────────────────────────────────────────────


class ToolFunctionSpec(TypedDict, total=False):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolSpec(TypedDict, total=False):
    """Spec d'un tool, format proche de l'API OpenAI function-calling.

    Champs OpenAI standard :
      - `type`     : toujours ``"function"``.
      - `function` : `{name, description, parameters}` (JSON Schema).

    Champs internes (filtrés avant l'envoi à OpenAI) :
      - `autonomy_level` : `AutonomyLevel`.
      - `agent_id`       : ``"compliance"`` | ``"advisor"`` | …
    """

    type: Literal["function"]
    function: ToolFunctionSpec
    autonomy_level: AutonomyLevel
    agent_id: str


def to_openai_tool(spec: ToolSpec) -> dict[str, Any]:
    """Convertit une `ToolSpec` interne en payload accepté par l'API OpenAI.

    Strip les métadonnées internes (`autonomy_level`, `agent_id`) que
    l'API ne reconnaît pas. Renvoie un nouveau dict (pas de mutation).
    """
    return {
        "type": "function",
        "function": dict(spec.get("function") or {}),
    }


# ─────────────────────────────────────────────────────────────────────────
# Protocol d'un module-tool
# ─────────────────────────────────────────────────────────────────────────


@runtime_checkable
class ToolModule(Protocol):
    """Contrat statique qu'un fichier-tool doit exposer.

    Convention : un fichier `tools/<agent>/<tool_name>.py` expose deux
    symboles top-level :

      - `SPEC: ToolSpec`  : la spec OpenAI augmentée.
      - `execute(ctx: ToolContext, **kwargs) -> dict | Awaitable[dict]`
        : l'implémentation (sync ou async). Le runtime gère les deux.

    Cf. RUNTIME § 2.2.
    """

    SPEC: ToolSpec

    @staticmethod
    def execute(ctx: ToolContext, **kwargs: Any) -> Any:
        """Exécute le tool. Peut être sync (renvoie ``dict``) ou async
        (renvoie ``Awaitable[dict]``).

        Convention de retour :
          - Toujours un `dict` JSON-serializable.
          - En cas d'échec attendu, retourner `{"error": "<code>"}`
            (le LLM peut raisonner dessus). NE PAS lever d'exception
            sur les erreurs métier non-fatales.
          - Pour signaler une demande de question utilisateur (cas
            `ask_user_question`), inclure `"interrupt_with_question": True`
            (cf. RUNTIME § 7).
        """
        ...


ToolExecuteFn = Callable[..., Any]
"""Type alias pour la fn `execute` d'un tool (sync ou async)."""

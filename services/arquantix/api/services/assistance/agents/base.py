"""Interface commune des agents assistance + types I/O.

Chaque agent concret (`assistant_default`, `compliance`, `advisor`,
`product`, `market`) implémente `AgentBase` et expose un `agent_id`
unique aligné avec :

  - la valeur stockée dans `assistance_messages.agent_used`
  - le label visible côté Flutter (badge `agent_used`)
  - la clé d'env var de modèle `ASSISTANCE_AGENT_<ID>_MODEL`

Référence d'architecture : `docs/arquantix/MULTI_AGENTS.md` § 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Literal, Optional, Protocol

# ── Identifiants d'agent (alignés avec le doc d'archi) ──────────────────

AGENT_DEFAULT_ID = "default"
AGENT_ROUTER_ID = "router"
AGENT_COMPLIANCE_ID = "compliance"
AGENT_ADVISOR_ID = "advisor"
AGENT_PRODUCT_ID = "product"
AGENT_MARKET_ID = "market"
# Cognitive Bot v4 — Lot 4 (2026-05-04) : agent dédié confiance &
# sécurité. Routable directement par le router pour questions purement
# sécurité/régulation/custody, et consultable par advisor /
# compliance.general en sous-routine pour fournir un encart factuel
# rassurant dans une réponse synthétique.
AGENT_TRUST_ID = "trust"

KNOWN_AGENT_IDS = frozenset({
    AGENT_DEFAULT_ID,
    AGENT_ROUTER_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_ADVISOR_ID,
    AGENT_PRODUCT_ID,
    AGENT_MARKET_ID,
    AGENT_TRUST_ID,
})

# Pseudo-`agent_hint` que le client renvoie quand l'utilisateur clique
# sur l'option « Reprendre <sujet> » d'un QCM de recentrage off-topic
# (cf. router `redirect_off_topic` § règle 6 du prompt). Ce n'est PAS un
# agent_id : `service._decide_agent` le résout vers le dernier
# `agent_used` non-router en lisant `assistance_messages`.
RESUME_TOPIC_HINT_ID = "resume_topic"

# Labels affichés côté Flutter (cf. § 1.2 du doc).
AGENT_LABELS: dict[str, str] = {
    AGENT_DEFAULT_ID: "",  # pas de badge pour le fallback
    AGENT_COMPLIANCE_ID: "Assistance compte",
    AGENT_ADVISOR_ID: "Conseil placement",
    AGENT_PRODUCT_ID: "Produits Vancelian",
    AGENT_MARKET_ID: "Veille marché",
    AGENT_TRUST_ID: "Confiance & sécurité",
}


# ── Types de messages SSE (event "type") ────────────────────────────────

AgentEventType = Literal[
    "delta",      # token assistant (streaming Markdown)
    "choices",    # QCM poussé par le router (cf. § 1.9)
    "done",       # fin du tour, message persisté
    "error",      # échec récupérable côté agent (LLM / tool)
    "thinking",   # phase intermédiaire visible (Phase 2b — diagnose, etc.)
]


# ── Dataclasses I/O ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ChoiceOption:
    """Option d'un QCM `choices`. Cf. doc § 1.9.1 et `COMPLIANCE_TOPICS.md` § 5.

    `id` : utilisé côté client comme `agent_hint` à renvoyer (ex.
    `"compliance"`) sauf valeur spéciale `"freeform"` qui signifie
    *« rien de tout ça, je reformule »*.

    Phase 2b — extension :
      - `agent_hint` : si présent, signal explicite de bascule d'agent
        (préféré sur l'`id` brut, plus auto-documenté).
      - `deep_link`  : si présent, le tap déclenche une **navigation
        Flutter** au lieu d'un nouveau message LLM (cf.
        `AssistanceDeepLinkResolver`). Mutuellement exclusif avec
        `agent_hint` — validé en amont par
        `_validate_choice_option` (raise si les deux sont remplis).
    """

    id: str
    label: str
    agent_hint: Optional[str] = None
    deep_link: Optional[str] = None

    def to_dict(self) -> dict:
        out: dict = {"id": self.id, "label": self.label}
        if self.agent_hint:
            out["agent_hint"] = self.agent_hint
        if self.deep_link:
            out["deep_link"] = self.deep_link
        return out


@dataclass
class AgentInput:
    """Payload remis à un agent pour produire une réponse.

    Construit par `service.py` après le passage du router (ou directement
    en cas d'`agent_hint` côté client). Contient :

    - `user_message`     : texte brut du dernier tour user.
    - `recent_turns`     : K derniers tours user/assistant déjà chargés
                           (cf. `memory.assistance_recent_turns_kept`).
    - `memory_state`     : snapshot retourné par `memory.load_memory_state`
                           (résumé conv + facts + long-memory client).
                           **Lecture seule** côté agent — l'écriture
                           reste exclusive au summarizer post-tour.
    - `router_metadata`  : décision du router (utile pour debug et pour
                           passer des entités extraites au prompt agent).
    """

    user_message: str
    recent_turns: list[dict]
    memory_state: dict
    router_metadata: Optional["RouterDecision"] = None


@dataclass
class AgentEvent:
    """Événement émis par `AgentBase.stream` (mappé 1-1 vers SSE).

    Le `service.py` qui consomme l'itérateur transforme ces events en
    SSE applicatif côté HTTP : `event: <type>\ndata: <json>`.
    """

    type: AgentEventType
    # Payloads selon le type :
    content: Optional[str] = None                  # type='delta'
    options: Optional[list[ChoiceOption]] = None   # type='choices'
    prompt: Optional[str] = None                   # type='choices'
    allow_freeform: bool = True                    # type='choices'
    message_id: Optional[str] = None               # type='done' (UUID stringifié)
    completed: bool = True                         # type='done'
    final_agent_id: Optional[str] = None           # type='done' (sub-agent réellement utilisé)
    # Phase 2c — orchestration multi-agent (cf. MULTI_AGENTS.md § 2.5).
    # Tous deux portés par `type='done'`.
    agent_chain: Optional[list[str]] = None        # type='done' (chaîne de sub-agents)
    consultations: Optional[list[dict]] = None     # type='done' (specialist consults)
    # Phase 2c.2 — embeds UI structurés produits par les tools (ex.
    # `transaction_detail`). Persistés dans `message_payload.embeds` et
    # rendus côté Flutter par des widgets dédiés (skeleton pendant fetch
    # des détails complets via API authentifiée). Le mécanisme est
    # générique : chaque embed a un `type` propre (ex. `transaction_detail`,
    # futur `product_card`, `portfolio_summary`…) que le client dispatche.
    embeds: Optional[list[dict]] = None            # type='done'
    # Pipeline product (Slack-like) : métadonnées du juge sortie — persistées
    # dans `message_payload.metadata.product_pipeline_output_judge`.
    output_judge_metadata: Optional[dict] = None   # type='done'
    # Fiches wiki effectivement injectées dans le system prompt (Pass 1 → FS),
    # pour l’admin (cohérent même sans appel `read_wiki_page`).
    wiki_pipeline_preload_refs: Optional[list[dict]] = None  # type='done'
    # Cognitive Bot v4 — Lot 5 « Observabilité » (2026-05-06).
    # Compteurs cumulés du tour, pour audit + UX admin (admin
    # conversation viewer). JSON-safe, valeurs numériques uniquement.
    # Présent uniquement sur le done event top-level (chain_depth == 0).
    # Schéma stable :
    #   {
    #     "wiki_calls_count": int,            # appels wiki effectués (succès)
    #     "wiki_quota_blocked_count": int,    # appels wiki bloqués (cap atteint)
    #     "audience_filtered_out_total": int, # fiches retirées pour audience
    #     "stop_pushing_blocked_count": int,  # widgets commerciaux bloqués
    #     "consultations_count": int,         # consult_specialist effectués
    #     "embeds_count": int,                # embeds UI émis (post-dédup)
    #     "dedup_hits": int,                  # tool calls dédupliqués
    #     "emojis_stripped_count": int,       # emojis supprimés par sanitizer post-LLM
    #   }
    runtime_metrics: Optional[dict] = None         # type='done'
    error_code: Optional[str] = None               # type='error'
    thinking_phase: Optional[str] = None           # type='thinking' (ex. 'diagnose')
    thinking_agent: Optional[str] = None           # type='thinking' (ex. 'compliance')

    def to_sse_payload(self) -> dict:
        """Sérialise l'event pour l'envoi SSE (sans le header `event:`)."""
        if self.type == "delta":
            return {"type": "delta", "content": self.content or ""}
        if self.type == "choices":
            return {
                "type": "choices",
                "prompt": self.prompt or "",
                "options": [o.to_dict() for o in (self.options or [])],
                "allow_freeform": self.allow_freeform,
            }
        if self.type == "done":
            payload: dict = {
                "type": "done",
                "message_id": self.message_id,
                "completed": self.completed,
            }
            if self.final_agent_id:
                payload["final_agent_id"] = self.final_agent_id
            if self.agent_chain:
                payload["agent_chain"] = list(self.agent_chain)
            if self.consultations:
                payload["consultations"] = list(self.consultations)
            if self.embeds:
                payload["embeds"] = list(self.embeds)
            if self.output_judge_metadata:
                payload["product_pipeline_output_judge"] = dict(
                    self.output_judge_metadata
                )
            if self.wiki_pipeline_preload_refs:
                payload["product_pipeline_wiki_preload"] = list(
                    self.wiki_pipeline_preload_refs
                )
            if self.runtime_metrics:
                payload["runtime_metrics"] = dict(self.runtime_metrics)
            return payload
        if self.type == "error":
            return {"type": "error", "message": self.error_code or "unknown"}
        if self.type == "thinking":
            return {
                "type": "thinking",
                "phase": self.thinking_phase or "",
                "agent": self.thinking_agent or "",
            }
        return {"type": self.type}


@dataclass
class RouterDecision:
    """Décision produite par `router.classify(...)`.

    `confidence` ∈ [0.0, 1.0]. Si < `ASSISTANCE_ROUTER_CONFIDENCE_MIN`
    (défaut 0.5), le service.py n'instancie pas d'agent et émet à la
    place un event `choices` (QCM, cf. § 1.9 du doc).

    `redirect_bridge` : texte court et bienveillant produit par le
    router quand il choisit `redirect_off_topic` (cf. règle 6 du prompt).
    Quand non-`None`, le `service.py` détecte un off-topic et émet un
    event `choices` dont le `prompt` est ce bridge — UI Flutter
    inchangée, l'utilisateur voit un message de recentrage avec
    optionnellement des chips « Reprendre <sujet> » + catégories
    Vancelian. `fallback_choices` peut être vide (= pas de chips, juste
    le bridge + l'option freeform ajoutée par `_build_choices_payload`).
    """

    agent_id: str
    confidence: float
    reasoning: str = ""
    extracted_entities: dict = field(default_factory=dict)
    fallback_choices: list[ChoiceOption] = field(default_factory=list)
    redirect_bridge: Optional[str] = None
    # Router v2 (2026-05-04) — pré-classification keyword des tags
    # d'intention Vancelian. Persistée dans `assistance_agent_decisions`
    # pour audit / debug via la vue admin 3-colonnes.
    intent_classification: Optional[dict] = None
    # Cognitive Bot v4 — Lot 1 (2026-05-04) — snapshot cognitif du tour
    # (emotional_intent, conversation_stage, trust_level, knowledge_level).
    # Calculé par ``services.assistance.agents.cognitive_state.compute_cognitive_state``,
    # persisté dans ``assistance_agent_decisions.arguments_json`` et lu
    # au tour suivant pour assurer la continuité (notamment du
    # trust_level qui s'érode / regagne tour par tour).
    cognitive_state: Optional[dict] = None
    # Cognitive Bot v4 — Lot 2 (2026-05-04) — objectif du tour calculé
    # de façon déterministe à partir du ``cognitive_state``
    # (cf. ``services.assistance.agents.conversation_objective``).
    # Forme : {primary_goal, next_best_action, stop_pushing,
    # strategy_hint, source_emotion, source_stage}. Injecté dans le
    # system prompt des agents experts pour orienter leur réponse.
    objective: Optional[dict] = None
    # Orchestrateur enrichi (2026-05) : dimensions produit au-delà de
    # l'agent_id — intention métier, urgence, besoin données, etc.
    # Cf. ``orchestration_context.normalize_orchestration``.
    orchestration: Optional[dict] = None

    @property
    def is_decisive(self) -> bool:
        from services.assistance.agents.config import (
            assistance_router_confidence_min,
        )

        return self.confidence >= assistance_router_confidence_min()

    @property
    def is_off_topic(self) -> bool:
        """Vrai quand le router a choisi `redirect_off_topic` (règle 6)."""
        return self.redirect_bridge is not None

    def to_log_dict(self) -> dict:
        out = {
            "agent_id": self.agent_id,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "extracted_entities": self.extracted_entities,
            "off_topic": self.is_off_topic,
        }
        if self.orchestration:
            orch = self.orchestration
            out["orchestration"] = {
                "business_intent": orch.get("business_intent"),
                "urgency": orch.get("urgency"),
                "data_need": orch.get("data_need"),
                "transaction_kind": orch.get("transaction_kind"),
            }
        return out


# ── Type label (pour signatures) ────────────────────────────────────────

AgentLabel = str  # alias sémantique


# ── Interface AgentBase ─────────────────────────────────────────────────


class AgentBase(Protocol):
    """Contrat commun à tous les agents.

    Un agent **ne touche pas la DB en écriture** : la persistance des
    messages assistant + maj des méta conv est faite par `service.py`
    après consommation du dernier event `done`. Ça garantit qu'un crash
    dans un agent ne corrompt pas la conversation.

    Les agents qui ont besoin d'accéder à la DB (compliance, advisor)
    reçoivent une session via leur constructeur, **uniquement pour des
    `SELECT`**.
    """

    agent_id: str
    """Identifiant stable, ex. `"compliance"`. Stocké dans
    `assistance_messages.agent_used`. Doit appartenir à `KNOWN_AGENT_IDS`."""

    display_label: AgentLabel
    """Label utilisateur côté Flutter, ex. *« Assistance compte »*.
    Vide pour `default` (pas de badge)."""

    model_env_var: str
    """Nom de l'env var qui surcharge le modèle OpenAI pour cet agent,
    ex. `"ASSISTANCE_AGENT_COMPLIANCE_MODEL"`."""

    async def stream(self, *, agent_input: AgentInput) -> AsyncIterator[AgentEvent]:
        """Streame la réponse de l'agent sous forme d'events.

        L'implémentation typique :
          1. `yield AgentEvent(type='delta', content='...')` × N (tokens)
          2. `yield AgentEvent(type='done', message_id='<uuid>')`

        Ou en cas d'erreur récupérable :
          1. `yield AgentEvent(type='error', error_code='llm_unavailable')`
        """
        ...
        # pragma: no cover (Protocol body intentionnellement vide)

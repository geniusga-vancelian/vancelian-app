# Multi-agents — Spec du runtime agentique (Phase 2a)

> **Statut :** Phase 2a **LIVRÉE** (2026-05-02). Spec applicable au code en production.
>
> **Dernière mise à jour :** 2026-05-06 (v1.2 — défaut runtime loop actif)
>
> **Objectif :** définir le pattern technique qui permet aux agents
> Vancelian (Compliance, Advisor, Product, Market) de devenir
> **autonomes par capabilities** au lieu d'être des responders statiques.
> Toute Phase V2 ultérieure doit s'appuyer sur ce socle.
>
> **Documents liés :**
> - `MULTI_AGENTS.md` — architecture cible des 5 agents
> - `MULTI_AGENTS_DATA_SOURCES.md` — cartographie data introspective
> - `AUDIT_AUTH_IDENTITIES.md` — règles `client_id` / `user_id` / `classify_actor()`
> - `MEMORY.md` — substrat mémoire long-terme

---

## 0. TL;DR

Le runtime agentique est une **boucle de function-calling itératif**
multi-tour qui remplace le single-shot LLM actuel. Chaque agent expose
un **catalogue de capabilities** (tools OpenAI), le LLM **choisit**
lesquelles appeler à chaque tour, on les exécute, on lui repasse les
résultats, jusqu'à convergence ou kill-switch.

Trois principes-clés :

1. **Schema-driven, pas hardcoded** — les tools découvrent les structures
   métier à l'exécution (registration flows, types de transactions,
   types de docs). Quand le métier évolue, l'agent suit sans modif Python.
2. **Autonomy levels** — toute action mutative est gradée L0/L1/L2/L3
   et peut être contrainte par config sans toucher au code agent.
3. **Sécurité matérielle** — les données AML sensibles ne touchent
   **jamais** la mémoire LLM. Garde par filtrage côté tool, pas par
   prompt.

---

## 1. Architecture du loop

```
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT RUNTIME LOOP                                                 │
│                                                                     │
│  Input :  AgentInput                                                │
│           ├── client_id, person_id (résolus via classify_actor)     │
│           ├── actor_kind (CUSTOMER | ONBOARDING | ADMIN_BO | SUSP.) │
│           ├── recent_turns (cf. MEMORY.md)                          │
│           ├── long_memory                                           │
│           └── user_message                                          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────┐            │
│  │  iteration = 0                                      │            │
│  │  messages = build_initial_messages(input)           │            │
│  │  available_tools = registry.tools_for(agent_id)     │            │
│  │                                                     │            │
│  │  while iteration < MAX_ITER (default = 6):          │            │
│  │      response = openai.chat_completion(             │            │
│  │          model=..., messages=messages,              │            │
│  │          tools=available_tools,                     │            │
│  │          tool_choice="auto")                        │            │
│  │                                                     │            │
│  │      if response.has_tool_calls:                    │            │
│  │          for call in response.tool_calls:           │            │
│  │              result = execute_tool(call, ctx)       │            │
│  │              messages.append(tool_result(call,      │            │
│  │                                          result))   │            │
│  │              audit.append(call, result)             │            │
│  │          iteration += 1                             │            │
│  │          continue                                   │            │
│  │                                                     │            │
│  │      else:                                          │            │
│  │          # final response                           │            │
│  │          stream_response(response.content)          │            │
│  │          break                                      │            │
│  │                                                     │            │
│  │  if iteration == MAX_ITER:                          │            │
│  │      stream_safe_fallback("Je n'arrive pas à...")   │            │
│  └─────────────────────────────────────────────────────┘            │
│                                                                     │
│  Output : AsyncIterator[AgentEvent]                                 │
│           ├── tool_call (debug only, pas streamé au client)         │
│           ├── delta (texte LLM)                                     │
│           ├── choices (QCM via tool ask_user_question)              │
│           └── done (final)                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 Différence avec Phase 1

| Aspect | Phase 1 (single-shot, **legacy**) | Phase 2a (loop) |
|---|---|---|
| Nombre d'appels OpenAI par tour | 1 | 1 à `MAX_ITER` (typiquement 2-4) |
| Tools | **aucun** sur l'agent expert (ex. `ComplianceAgent.stream` : bloc texte depuis **stubs** `compliance_tools`, pas le registry OpenAI) | catalogue par agent (**function calling** réel depuis `tools/registry.py`) |
| Capacité de raisonner sur des données fraîches | non (snapshot statique) | oui (itère pour collecter) |
| Capacité de poser une question | non | oui via `ask_user_question` |
| Capacité d'exécuter une action | non | oui via tools L1/L2/L3 |
| Coût LLM | 1× | 2-4× (acceptable, latence ~1.5-3s) |

### 1.2 Limites de la boucle

- `MAX_ITER` = **6** par défaut (configurable via env `ASSISTANCE_AGENT_MAX_ITER`).
  Au-delà, on coupe et on streame une réponse de fallback.
- **Timeout total** = 25 s par défaut (`ASSISTANCE_AGENT_TIMEOUT_SECONDS`).
  Au-delà, on streame ce qu'on a + on persiste un message d'erreur.
- **Tool call timeout** = 5 s par tool (`ASSISTANCE_TOOL_TIMEOUT_SECONDS`).
  Au-delà, le tool retourne `{"error": "timeout"}` au LLM (qui peut
  raisonner dessus).
- **Aucun parallélisme** entre tools dans la V2a (séquentiel). Phase 2b
  pourra activer le parallel function calling d'OpenAI si besoin.

### 1.3 Modes streaming

L'iterative loop **streame uniquement la dernière itération** (celle qui
produit du texte sans tool call). Les itérations intermédiaires sont
non-streamées (mode `chat_completion` standard, pas `stream`). Côté
client mobile :

```
event: started
data: {"agent_used": "compliance", "iter_count": 3}
event: delta (×N)
data: {"delta": "..."}
event: done
data: {"agent_used": "compliance", "iter_count": 3, "tools_called": ["read_compliance_state","read_documents"]}
```

Le `iter_count` et `tools_called` permettent au client (admin debug)
de visualiser le raisonnement.

### 1.4 Activation du runtime loop (`ASSISTANCE_RUNTIME_LOOP_ENABLED`)

**Depuis la livraison « tool-runtime-default » (2026-05) :**

- **`ASSISTANCE_RUNTIME_LOOP_ENABLED` vaut `true` par défaut** (absence de variable d'environnement = activé).  
  Implémentation : `services/assistance/agents/config.py::assistance_runtime_loop_enabled()`.
- **Rollback explicite (incident, debug Phase 1) :** définir  
  **`ASSISTANCE_RUNTIME_LOOP_ENABLED=false`** — les agents listés dans `ASSISTANCE_RUNTIME_LOOP_AGENTS` repassent sur le chemin **`get_agent(...).stream`** (« Phase 1 »), sans boucle ni tools OpenAI pour l'expert concerné.

**Legacy Phase 1 (compliance)** quand le flag est à `false` :  
`ComplianceAgent` injecte encore un bloc « Contexte instantané » construit depuis `compliance_tools.py` (stub : transactions récentes **souvent vides**, statut compte **neutre**). Les outils **dynamiques** du registry (`read_transactions`, `list_transactions`, stats, etc.) **ne sont pas** proposés au modèle en function calling sur ce chemin.

**Agents passant par le runtime par défaut** (`ASSISTANCE_RUNTIME_LOOP_AGENTS` non défini) :  
`compliance`, `product`, `advisor`, `market`, **`trust`**.

**Sous-agent `compliance.transactional`** (après `diagnose_compliance_topic`) : expose notamment  
`read_transaction_detail`, `list_transactions`, les **stats** (`stats_transaction_counts`, `stats_transaction_amounts`, `stats_portfolio_performance`, `stats_portfolio_allocation`), plus la base `_COMPLIANCE_BASE_TOOLS` (dont `read_transactions`, KYC/registration, documents, wiki). Voir `tools/registry.py`.

**Politique `data_need` (PR3)** : le module `data_need_read_policy.py` n'**empêche** pas les réponses ni les tool calls. Il enregistre un **warning** d'audit (`policy_data_need_reads` / log) si le routeur a posé un `data_need` impliquant des lectures compte/transactions/KYC et qu'**aucun** outil de lecture attendu n'a été invoqué avant la fin du tour — utile pour l'observabilité, pas un garde-fou bloquant.

---

## 2. Tool registry

### 2.1 Structure répertoire

```
services/arquantix/api/services/assistance/agents/
├── tools/
│   ├── __init__.py
│   ├── registry.py              ← NEW : registre des tools par agent
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── classify_actor.py    ← primitive partagée (cf. AUDIT_AUTH_IDENTITIES)
│   │   ├── ask_user_question.py ← tool transverse (tous agents)
│   │   └── audit.py             ← persistance agent_decisions
│   ├── compliance/
│   │   ├── __init__.py
│   │   ├── read_compliance_state.py
│   │   ├── read_registration_progress.py
│   │   ├── read_documents.py
│   │   ├── read_transactions.py
│   │   ├── read_external_aml_signals.py
│   │   ├── request_document_upload.py     ← L2 (Phase 2c)
│   │   ├── create_compliance_ticket.py    ← L2 (Phase 2c)
│   │   └── propose_account_action.py      ← L1 (advisory only)
│   ├── advisor/                            ← Phase 3
│   ├── product/                            ← Phase 5
│   └── market/                             ← Phase 6
└── repositories/
    ├── compliance_repo.py
    ├── registration_repo.py
    └── ...
```

### 2.2 Contrat d'un tool

```python
# services/assistance/agents/tools/compliance/read_compliance_state.py
"""
Tool : read_compliance_state
Agent : compliance
Autonomy level : L0 (read-only)
"""
from typing import Any
from services.assistance.agents.tools.contracts import ToolSpec, ToolContext

def execute(ctx: ToolContext, **kwargs) -> dict[str, Any]:
    """Snapshot introspectif complet de l'état compliance d'un client.

    Returns un dict JSON-serializable. Jamais d'exception (best-effort).
    """
    client_id = ctx.client_id
    return {
        "actor_kind": ctx.actor_kind.value,
        "registration": _safe(registration_repo.fetch_summary, client_id),
        "documents": _safe(compliance_repo.fetch_documents_summary, ctx.person_id),
        "transactions": _safe(compliance_repo.fetch_transactions_summary, client_id),
        "compliance_signals": _safe(  # GATED : retour pré-cuit safe
            compliance_repo.fetch_safe_signals, client_id
        ),
    }

# OpenAI function spec (consommée par le runtime)
SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "read_compliance_state",
        "description": (
            "Retourne un snapshot complet de l'état compliance du client : "
            "registration, documents, transactions, signaux compliance gated. "
            "À appeler en premier avant tout raisonnement compliance. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance",
}
```

### 2.3 ToolContext (injecté par le runtime)

```python
@dataclass(frozen=True)
class ToolContext:
    db: Session
    client_id: Optional[str]       # UUID stringifié, None si ONBOARDING/ADMIN_BO
    person_id: Optional[str]       # UUID stringifié
    user_id: int                   # admin_users.id (à utiliser uniquement pour auth_*)
    actor_kind: ActorKind
    agent_id: str
    conversation_id: str
    iteration: int                 # n° du tour de boucle (0..MAX_ITER)
    audit_session_id: str          # pour traçabilité
    correlation_id: str            # pour logs structurés
    embeds_to_emit: list[dict]     # collecteur d'embeds UI (Phase 2c.2)
    # Cognitive Bot v4 — Lot 2 (2026-05-06)
    cognitive_state: Optional[dict] = None
    objective: Optional[dict] = None
```

Le tool ne reçoit **jamais** le `AuthContext` brut (trop puissant). Le
runtime construit un `ToolContext` filtré qui ne contient **que** ce dont
le tool a besoin.

#### 2.3bis Champs cognitifs — Lot 2 (2026-05-06)

`cognitive_state` et `objective` sont des snapshots **dict-form**
calculés en amont par `services.assistance.service.start_chat_turn`
puis transportés via `agent_input.memory_state`. Le runtime les
recopie dans `ToolContext` pour les rendre lisibles depuis n'importe
quel tool.

| Champ | Forme | Source | Usage typique côté tool |
|---|---|---|---|
| `cognitive_state` | `{emotional_intent, conversation_stage, trust_level, knowledge_level, …}` | `cognitive_state.compute_cognitive_state(...).to_dict()` | Adapter le ton, prioriser certains résultats |
| `objective` | `{primary_goal, next_best_action, stop_pushing, strategy_hint, …}` | `conversation_objective.compute_objective(...).to_dict()` | Bloquer un push commercial si `stop_pushing=True` |

**Pourquoi `dict` et pas une dataclass typée** :

- Pas de cycle d'import (`contracts.py` est très bas niveau).
- Sérialisable trivialement (audit / log / propagation cross-agent).
- Fidèle au format réel transporté via `memory_state`.

**Helpers read-only** dans
`services.assistance.agents.tools.shared.cognitive_context` —
batterie défensive (fallback `NEUTRAL` si l'état est `None` ou
malformé) qui évite que chaque tool réimplémente le boilerplate
`isinstance(...) + dict.get(...) + fallback` :

```python
from services.assistance.agents.tools.shared import (
    get_emotional_intent, get_trust_level, should_stop_pushing,
    get_strategy_hint, cognitive_snapshot,
)

def execute(ctx, *, question, **_):
    if should_stop_pushing(ctx):
        # Pas de CTA, pas d'upsell : restauration de confiance d'abord.
        ...
    emotion = get_emotional_intent(ctx)  # "fear" | "anger" | "neutral" | …
    trust   = get_trust_level(ctx)       # 0.0 .. 1.0
```

**Propagation cross-agent** : `_run_consult_specialist` recopie
`cognitive_state` + `objective` dans le `memory_state` du sub-runtime
avant spawn. Sans cela, le specialist consulté voyait un état
neutre par défaut (bug latent réparé par Lot 2).

Tests : `tests/test_assistance_cognitive_context_unit.py` (39
tests : helpers + plumbing runtime + propagation consult).

#### 2.3ter Champ `current_topic` — Lot 4 (2026-05-06)

`current_topic` est un snapshot **dict-form** du slot persisté côté
`AssistanceConversation.current_topic` (cf.
`services.assistance.conversation_topic` pour la source de vérité).
Lu par le router depuis Phase 2 wiki v1.4 pour stabiliser les
follow-ups déictiques (« et lui ? »), il est **maintenant aussi**
exposé aux tools via `ToolContext.current_topic`.

Schéma typique (cf. `infer_topic_from_tool_call`) :

```python
{
    "kind": "vancelian_product" | "instrument" | "topic_other",
    "product_code": "TOP5" | None,
    "instrument_symbol": "BTC" | None,
    "agent_owner": "product",
    "set_at_turn": 3,
    "set_by_tool": "show_bundle_detail",
    "confidence": 0.95,
    "set_at": "2026-05-06T11:42:00Z",
}
```

**Helpers read-only** dans
`services.assistance.agents.tools.shared.topic_context` :

```python
from services.assistance.agents.tools.shared import (
    get_current_topic_kind,            # "vancelian_product" | … | None
    get_current_topic_product_code,    # "TOP5" | None  (uppercase)
    get_current_topic_instrument_symbol,  # "BTC" | None  (uppercase)
    get_current_topic_label,           # "vancelian_product:TOP5" | …
    topic_matches_product_code,        # bool — utile pour anti-dérive
    topic_matches_instrument_symbol,   # bool
    topic_snapshot,                    # dict JSON-safe pour log / hint
)
```

**Propagation cross-agent** : `_run_consult_specialist` recopie
`current_topic` dans le `memory_state` du sub-runtime — sans quoi
le specialist consulté pouvait dériver vers un autre instrument /
produit alors que le sujet est ancré côté caller.

Tests : `tests/test_assistance_topic_context_unit.py` (40 tests :
shape, helpers défensifs, casing, alignement constantes,
plumbing + propagation consult).

#### 2.3quater Observabilité `runtime_metrics` — Lot 5 (2026-05-06)

L'`AgentEvent(type="done")` porte désormais un champ optionnel
`runtime_metrics: Optional[dict]` qui agrège les compteurs cumulés
du tour. Émis uniquement au top-level (`chain_depth == 0`) et
seulement si au moins une valeur est non-nulle (payload propre
pour les tours simples).

| Clé | Type | Source |
|---|---|---|
| `wiki_calls_count` | int | `select_wiki_pages` + `read_wiki_page` succès (Lot 1) |
| `wiki_quota_blocked_count` | int | Appels wiki court-circuités par `MAX_WIKI_CALLS_PER_TOUR` (Lot 1) |
| `audience_filtered_out_total` | int | Cumul de `result["audience_filtered_out"]` exposé par `select_wiki_pages` (Lot 1) |
| `stop_pushing_blocked_count` | int | Widgets commerciaux retournant `error: stop_pushing_active` (Lot 3) |
| `consultations_count` | int | `consult_specialist` effectués (Phase 2c) |
| `embeds_count` | int | Embeds UI émis (post-dédup) |
| `dedup_hits` | int | Tool calls dédupliqués (Phase 2 wiki v1.4 patch) |

Sérialisé tel quel dans la SSE payload du done event sous la clé
`runtime_metrics`. Utilisable côté admin UI (vue conversation) pour
expliquer pourquoi un tour s'est mal passé (« 3 fiches wiki
masquées par audience » / « widget instrument bloqué FEAR »).

Tests : `tests/test_assistance_runtime_observability_unit.py` (10
tests : shape, sérialisation SSE, agrégation par compteur, tour
simple sans metrics, robustesse aux types invalides).

### 2.4 Registry

```python
# services/assistance/agents/tools/registry.py
from typing import Mapping

TOOLS_BY_AGENT: Mapping[str, list[ToolModule]] = {
    "compliance": [
        read_compliance_state,
        read_registration_progress,
        read_documents,
        read_transactions,
        read_external_aml_signals,
        ask_user_question,
        # Phase 2c uniquement :
        request_document_upload,
        create_compliance_ticket,
        propose_account_action,
    ],
    "advisor":  [...],   # Phase 3
    "product":  [...],   # Phase 5
    "market":   [...],   # Phase 6
    "default":  [
        ask_user_question,   # le default agent peut juste poser une question
    ],
    # Le router N'A PAS de tools dans cette spec (il garde son function
    # calling existant pour route_to/ask_clarification).
}

def tools_for(agent_id: str, *, autonomy_max: AutonomyLevel = "L1") -> list[ToolSpec]:
    """Retourne les tools disponibles pour un agent, filtrés par niveau
    d'autonomie max actuellement autorisé (config-driven)."""
    return [
        m.SPEC for m in TOOLS_BY_AGENT.get(agent_id, [])
        if autonomy_le(m.SPEC["autonomy_level"], autonomy_max)
    ]
```

---

## 3. Autonomy levels

### 3.1 Définition

| Niveau | Définition | Exemples |
|---|---|---|
| **L0** | Read-only, idempotent. Aucun side-effect. | `read_compliance_state`, `read_documents`, `read_transactions` |
| **L1** | Advisory : produit une **proposition** journalisée, requiert validation humaine asynchrone. | `propose_account_action(action="block_account", reasoning=...)` |
| **L2** | Action mutative low-risk, auto-exécutée + journalisée + reviewable post-fact. | `request_document_upload`, `create_compliance_ticket`, `ask_user_question` |
| **L3** | Action mutative high-risk, auto-exécutée + review humaine asynchrone obligatoire (24h). | `block_transaction`, `block_account`, `close_account` (jamais Phase 2) |

### 3.2 Configuration

```bash
# .env.arquantix (par agent)
ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L0   # Phase 2a : read-only seulement
# ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L1 # Phase 2b : advisory ouvert
# ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L2 # Phase 2c : actions doc/ticket auto
# ASSISTANCE_COMPLIANCE_AUTONOMY_MAX=L3 # Phase 4+ : never in V2

ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH=true   # Boolean : si false, force L0 partout
```

### 3.3 Garanties

- **Phase 2a livre Compliance en L0 only.** Aucune mutation possible
  par construction (registry filtre). Pas de risque réglementaire.
- **Phase 2c remontera à L2.** Les actions L2 vont dans la table
  `agent_decisions` (cf. § 4) et déclenchent une notification au BO admin.
- **L3 reste interdite jusqu'à un go/no-go produit explicite.**

### 3.4 Kill-switch global

Une variable env unique (`ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH`) force
tous les agents en L0 quel que soit leur paramétrage. À utiliser en cas
d'incident (drift LLM, intégration externe en panne, etc.).

---

## 4. Table `agent_decisions` (migration 148)

### 4.1 Schema cible

```sql
CREATE TABLE assistance_agent_decisions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id    UUID NOT NULL REFERENCES assistance_conversations(id),
    message_id         UUID REFERENCES assistance_messages(id),
    agent_id           VARCHAR(32) NOT NULL,         -- 'compliance', 'advisor', ...
    iteration          SMALLINT NOT NULL,             -- n° de tour dans le loop
    tool_name          VARCHAR(64) NOT NULL,
    autonomy_level     VARCHAR(4) NOT NULL,           -- 'L0','L1','L2','L3'
    arguments_json     JSONB NOT NULL DEFAULT '{}',   -- args passés au tool
    result_summary     JSONB,                         -- résumé du retour (gated)
    -- Pour les tools mutatifs L1+ :
    proposed_action    VARCHAR(64),                   -- 'request_doc_upload', etc.
    target_client_id   UUID REFERENCES pe_clients(id),
    target_person_id   UUID REFERENCES persons(id),
    reasoning_summary  TEXT,                          -- résumé LLM (sanitize tipping-off)
    review_status      VARCHAR(16) NOT NULL DEFAULT 'auto',
                       -- 'auto' (L0/L2 immédiat), 'pending' (L1 attend humain),
                       -- 'approved' / 'rejected' (L1 traité)
    reviewed_by        INT REFERENCES admin_users(id),
    reviewed_at        TIMESTAMPTZ,
    -- Dimensions techniques :
    duration_ms        INT,
    error_code         VARCHAR(32),
    correlation_id     VARCHAR(64),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Index utiles
    INDEX (conversation_id, iteration),
    INDEX (agent_id, created_at),
    INDEX (tool_name),
    INDEX (autonomy_level),
    INDEX (review_status) WHERE review_status = 'pending',
    INDEX (target_client_id, created_at)
);
```

### 4.2 Règles de remplissage

| Cas | `review_status` | Persistance |
|---|---|---|
| **Tool L0** (read) | `'auto'` | OUI, mais peut être épargné (volume) — décision Phase 2a : on persiste TOUS les tools L0 du premier tour, pas les suivants |
| **Tool L1** (proposal) | `'pending'` → `'approved'`/`'rejected'` | OUI obligatoire |
| **Tool L2** (action) | `'auto'` | OUI obligatoire |
| **Tool L3** (action critique) | `'auto'` mais notifie un humain | OUI obligatoire + alerte Slack/email |

### 4.3 Sanitization du `reasoning_summary`

Avant d'écrire le `reasoning_summary`, on passe le texte LLM dans un
**sanitizer anti-tipping-off** :

```python
TIPPING_OFF_BLACKLIST = {
    "fraude", "fraud", "suspicion", "suspect", "enquête", "enquete",
    "investigation", "blanchiment", "money laundering", "PEP",
    "watchlist", "OFAC", "sanction", "surveillance",
    "block_for_aml", "risk_score", "level_high",
}

def sanitize_reasoning(text: str) -> str:
    cleaned = text
    for word in TIPPING_OFF_BLACKLIST:
        cleaned = re.sub(rf"\b{re.escape(word)}\b", "[REDACTED]", cleaned, flags=re.IGNORECASE)
    return cleaned
```

→ Sécurité de défense en profondeur : même si un futur dev persiste
accidentellement du raisonnement LLM contenant un mot interdit, il est
masqué avant écriture.

---

## 5. Tipping-off : sécurité matérielle

### 5.1 Principe

Les **données AML sensibles** ne doivent **jamais** être chargées en
mémoire LLM. La frontière de filtrage est **côté tool**, **pas côté
prompt**.

### 5.2 Implémentation type

```python
# services/assistance/agents/repositories/compliance_repo.py

def fetch_safe_signals(client_id: str) -> dict:
    """Retourne uniquement des signaux PRÉ-CUITS et SÛRS.

    NE retourne JAMAIS :
      - le risk score brut (0-100)
      - le level brut ('LOW'/'MEDIUM'/'HIGH')
      - le deny_reason d'auth_security_decisions
      - les match watchlist OFAC/PEP

    RETOURNE uniquement :
      - safe_signals.requires_doc_upload : bool
      - safe_signals.requires_step_up    : bool
      - safe_signals.actor_must_contact_support : bool
      - safe_signals.client_facing_message : str (ou None)
    """
    with get_db_session() as db:
        # On lit auth_global_risk_score etc., mais on traduit en signaux
        # client-facing uniquement.
        risk = _fetch_risk_internal(db, client_id)  # interne, pas exposé
        decisions = _fetch_recent_decisions(db, client_id)

        # Traduction → safe
        if risk.level == "HIGH" or any(d.deny_reason for d in decisions):
            return {
                "requires_doc_upload": True,
                "requires_step_up": True,
                "actor_must_contact_support": False,  # surtout PAS de "support"
                                                       # (tipping-off)
                "client_facing_message": (
                    "Pour finaliser cette opération, nous devons compléter "
                    "notre dossier de vérification. Tu peux uploader les "
                    "documents demandés depuis ton espace personnel."
                ),
            }

        return {
            "requires_doc_upload": False,
            "requires_step_up": False,
            "actor_must_contact_support": False,
            "client_facing_message": None,
        }
```

→ Le LLM ne reçoit **jamais** `risk.level == "HIGH"`. Il reçoit
`requires_doc_upload: true`. Garantie matérielle, pas comportementale.

### 5.3 Tests anti-tipping-off automatisés

```python
# tests/test_assistance_tipping_off_unit.py
def test_high_risk_client_never_leaks_to_llm(monkeypatch):
    captured_messages = []
    def fake_chat_completion(messages, **kw):
        captured_messages.extend(messages)
        return {"content": "Réponse safe"}

    monkeypatch.setattr(openai_client, "chat_completion", fake_chat_completion)

    # Setup client avec risk HIGH en DB
    setup_client_with_high_risk(client_id="test-client-uuid")

    # Tour de chat
    run_assistance_turn(client_id="test-client-uuid", message="où en est mon dépôt ?")

    # Inspect messages envoyés au LLM
    full_payload = json.dumps(captured_messages, ensure_ascii=False).lower()
    for forbidden in ("fraude", "suspicion", "watchlist", "high", "risk_score",
                      "blanchiment", "ofac", "pep"):
        assert forbidden not in full_payload, (
            f"TIPPING-OFF DETECTED : '{forbidden}' leaked to LLM payload"
        )
```

→ Cette suite tourne dans la CI, **bloque le merge** si un nouveau
tool fuit accidentellement un mot interdit.

---

## 6. External providers : pattern adapter

### 6.1 Structure

```
services/arquantix/api/services/assistance/agents/external/
├── __init__.py
├── base.py                       ← Protocol KycProvider, WatchlistScreener, etc.
├── router.py                     ← choisit l'adapter selon ENV
└── adapters/
    ├── __init__.py
    ├── mock.py                   ← DEFAULT (Phase 2a-b)
    ├── sumsub.py                 ← Phase 3+ (si signé)
    ├── onfido.py                 ← idem
    └── refinitiv_watchlist.py    ← idem
```

### 6.2 Contrat (Protocol)

```python
# services/assistance/agents/external/base.py
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

@dataclass(frozen=True)
class KycVerificationResult:
    provider: str          # 'mock' / 'sumsub' / 'onfido'
    status: str            # 'approved' / 'rejected' / 'pending' / 'unknown'
    confidence: float      # 0.0-1.0
    flags: list[str]       # liste de signaux NON-LEAK (ex. 'doc_quality_low')
    reference_id: str      # ID externe pour traçabilité
    raw_response_redacted: dict  # debug only, jamais exposé au LLM

@runtime_checkable
class KycProvider(Protocol):
    name: str

    def verify_identity(self, person_id: str, ctx: ExternalContext) -> KycVerificationResult: ...
    def screen_watchlist(self, person_id: str, ctx: ExternalContext) -> KycVerificationResult: ...
```

### 6.3 Mock par défaut

```python
# services/assistance/agents/external/adapters/mock.py
class MockKycProvider:
    name = "mock"

    def verify_identity(self, person_id, ctx):
        return KycVerificationResult(
            provider="mock", status="unknown", confidence=0.0,
            flags=[], reference_id=f"mock-{person_id[:8]}",
            raw_response_redacted={"note": "mock provider returns unknown"},
        )

    def screen_watchlist(self, person_id, ctx):
        return KycVerificationResult(
            provider="mock", status="approved", confidence=1.0,
            flags=[], reference_id=f"mock-wl-{person_id[:8]}",
            raw_response_redacted={"matches": []},
        )
```

### 6.4 Router

```python
# services/assistance/agents/external/router.py
def get_kyc_provider() -> KycProvider:
    name = os.getenv("ASSISTANCE_KYC_PROVIDER", "mock").lower()
    if name == "mock":
        return MockKycProvider()
    if name == "sumsub":
        return SumsubProvider()
    # ...
    raise ValueError(f"Unknown KYC provider: {name}")
```

→ Phase 2a : `ASSISTANCE_KYC_PROVIDER=mock` partout. Aucune
configuration nécessaire. Quand un contrat est signé, on ajoute un
fichier dans `adapters/`, on switche l'env var. **Zéro changement côté
agent.**

---

## 7. Tools transverses (tous agents)

### 7.1 `ask_user_question`

```python
# services/assistance/agents/tools/shared/ask_user_question.py

def execute(ctx: ToolContext, *, prompt: str, options: list[dict] = None,
            allow_freeform: bool = True) -> dict:
    """Pose une question au client. Le runtime intercepte ce tool call et
    convertit le retour en SSE 'choices' event (cf. § 8 streaming).

    options : [{"id": str, "label": str}, ...] — affiché comme QCM côté Flutter
    allow_freeform : si True, ajoute "Rien de tout ça" qui rouvre l'input texte
    """
    # Le tool ne fait rien lui-même : il signale au runtime qu'il faut
    # interrompre la boucle et renvoyer une question au client.
    return {
        "interrupt_with_question": True,
        "prompt": prompt,
        "options": options or [],
        "allow_freeform": allow_freeform,
    }

SPEC = {
    "type": "function",
    "function": {
        "name": "ask_user_question",
        "description": (
            "Pose une question au client pour clarifier sa demande. "
            "À utiliser quand l'agent a besoin d'info qu'il n'a pas dans ses "
            "tools (ex. 'quel est l'objet exact de ton virement ?'). "
            "Le client recevra un QCM si options fournies, sinon une question texte. "
            "ATTENTION : interrompt la boucle agent. Ne pas appeler en série."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                    },
                },
                "allow_freeform": {"type": "boolean"},
            },
            "required": ["prompt"],
        },
    },
    "autonomy_level": "L0",  # techniquement read-only (pas de mutation DB)
}
```

### 7.2 Comportement runtime sur `ask_user_question`

Le runtime reconnait ce tool spécifique et :
1. **Interrompt la boucle** dès la fin du tour courant.
2. **N'appelle pas le LLM pour un autre tour.**
3. **Streame un événement `choices`** au client (format Flutter actuel,
   compatible Phase 1).
4. **Persiste un message** `message_type='choices'` avec le payload.
5. La réponse du client (clic option ou texte libre) déclenche un **nouveau
   tour** — la boucle redémarre à zéro avec le contexte enrichi.

---

## 8. Streaming SSE étendu

### 8.1 Événements émis

```
event: started
data: {"agent_used": "compliance", "iteration": 0}

event: thinking          ← optionnel, debug only
data: {"iteration": 1, "tool_calls": [{"name": "read_compliance_state"}]}

event: delta            ← stream de la réponse finale
data: {"delta": "Ton dépôt..."}

event: choices          ← si ask_user_question
data: {"prompt": "...", "options": [...], "allow_freeform": true}

event: done
data: {"agent_used": "compliance", "iter_count": 3,
       "tools_called": ["read_compliance_state", "read_documents"],
       "decision_ids": ["uuid1", "uuid2"]}

event: error
data: {"error": "agent_max_iter_reached"}
```

### 8.2 Compatibilité Phase 1

L'événement `choices` existe déjà côté Flutter (Phase 1). Le `done`
gagne 3 nouveaux champs (`iter_count`, `tools_called`, `decision_ids`)
qui sont ignorés par les anciens clients sans erreur.

L'événement `thinking` est **opt-in** par env (`ASSISTANCE_STREAM_THINKING=true`)
et ne sera streamé qu'en mode debug / admin. **Jamais** au client mobile
final.

---

## 9. Observabilité

### 9.1 Logs structurés (JSON)

À chaque tour, on log :

```python
logger.info("assistance.agent.tour_done", extra={
    "conversation_id": ...,
    "agent_id": "compliance",
    "iteration_count": 3,
    "tools_called": ["read_compliance_state", "read_documents"],
    "duration_ms": 2340,
    "actor_kind": "customer",
    "tipping_off_filter_hits": 0,    # nb de mots censurés dans reasoning
    "max_iter_reached": False,
    "early_break_reason": None,       # 'final_answer' | 'choices_emitted' | 'max_iter' | 'timeout' | 'error'
})
```

### 9.2 Métriques (Prometheus, Phase 3+ si besoin)

- `assistance_agent_tour_count{agent_id, status}` (counter)
- `assistance_agent_tour_iter_total{agent_id}` (histogram)
- `assistance_agent_tool_count{agent_id, tool_name, autonomy_level}` (counter)
- `assistance_agent_tipping_off_redactions_total` (counter)

### 9.3 Tracing (OpenTelemetry, Phase 3+ si besoin)

Span parent = un tour assistance. Spans enfants = chaque iteration LLM
+ chaque tool call. Permet de visualiser le raisonnement dans Datadog
APM / Honeycomb.

---

## 10. Stratégie de tests

### 10.1 Pyramide

| Niveau | Suite | Mocks | Volume cible Phase 2a |
|---|---|---|---|
| **Unit — Tools** | `test_assistance_tools_<agent>_unit.py` | mocke le repo | ≥ 5 par tool, soit ~25 |
| **Unit — Runtime loop** | `test_assistance_runtime_loop_unit.py` | mocke OpenAI + tools | ≥ 12 (cas nominaux + max_iter + timeout + ask_user_question + erreurs) |
| **Integration — Repos** | `test_assistance_repos_<agent>_integration.py` | session DB transactionnelle | ≥ 6 par repo |
| **Integration — Tipping-off** | `test_assistance_tipping_off_integration.py` | DB + mock LLM qui inspecte le payload | ≥ 8 (1 par signal sensible × scenarios) |
| **E2E** | `test_assistance_e2e_<agent>.py` | DB + mock OpenAI déterministe | ≥ 2 par agent |

### 10.2 Test de référence anti-tipping-off

```python
@pytest.mark.parametrize("scenario", [
    "client_with_risk_HIGH",
    "client_with_pending_aml_action",
    "client_with_kyc_rejected",
    "client_with_blocked_transaction",
    "onboarding_with_doc_review_failed",
])
def test_no_tipping_off_word_in_llm_payload(scenario):
    setup_scenario(scenario)
    captured = capture_llm_payload(run_chat_turn)
    for forbidden in TIPPING_OFF_BLACKLIST:
        assert forbidden.lower() not in captured.lower()
```

**Cette suite est bloquante pour merge.** Si un dev fuit accidentellement
un mot, la PR est rejetée par CI.

---

## 11. classify_actor() : primitive Phase 2a

(Cf. `AUDIT_AUTH_IDENTITIES.md` § 7.1 pour la spec complète.)

Implémentation cible dans `services/assistance/agents/tools/shared/classify_actor.py`,
appelée :

1. **Avant le router** dans `service.start_chat_turn` :
   - `ADMIN_BO` → 403 immédiat (`actor_admin_bo_not_allowed`)
   - `SUSPENDED` → réponse standardisée court-circuit (cf. § 11.1)
   - `CUSTOMER` / `ONBOARDING` → flux normal vers router multi-agent

2. **Dans le runtime loop** comme valeur lue dans `ToolContext.actor_kind`,
   permettant aux tools / prompts de s'adapter (ex. agent compliance
   bascule en "mode onboarding" si `actor_kind == ONBOARDING`).

### 11.1 Réponse standardisée pour SUSPENDED

```
"""
Ton compte est temporairement gelé pour des raisons de sécurité.
Pour toute question, tu peux nous joindre via le menu Aide de l'app.

Notre équipe revient vers toi dès que possible.
"""
```

→ Hardcodée dans le service (pas de LLM call). Pas de tools. Pas de
mémoire. Garantie d'absence totale de fuite quelle que soit l'évolution
du LLM.

---

## 12. Migration depuis Phase 1

### 12.1 Ce qui reste

- Le **router** (`agents/router.py`) reste en function-calling single-shot
  pour `route_to` / `ask_clarification`. Pas de loop sur le router.
- Les **agents existants** (`assistant_default`, `compliance`, `advisor`,
  `product`, `market`) gardent leur fichier mais sont **réécrits** pour
  utiliser le nouveau runtime au lieu d'appeler directement OpenAI.
- Le **streaming SSE** (`event: started/delta/done/choices/error`)
  reste compatible côté Flutter (cf. § 8.2).
- La **mémoire long-terme** (`MEMORY.md`) reste intacte. Les tools y
  ont accès via `ToolContext`.

### 12.2 Ce qui change

- `_llm_agent_base.py` est **renommé** en `runtime/agent_loop.py` et
  réécrit en boucle itérative.
- Chaque agent expose `agent_id`, `system_prompt_path`, `tools`. Plus
  de méthode `stream` à coder par agent (le runtime s'en charge).
- `service.stream_assistant_turn` est **patché** pour appeler le runtime
  au lieu de `agent.stream`.
- Nouvelle migration **148** pour la table `agent_decisions`.
- Nouvelles env vars : `ASSISTANCE_AGENT_MAX_ITER`, `ASSISTANCE_AGENT_TIMEOUT_SECONDS`,
  `ASSISTANCE_TOOL_TIMEOUT_SECONDS`, `ASSISTANCE_<AGENT>_AUTONOMY_MAX`,
  `ASSISTANCE_GLOBAL_AUTONOMY_KILLSWITCH`, `ASSISTANCE_KYC_PROVIDER`.

### 12.3 Compatibilité ascendante

Les tests Phase 1 (47 tests router/agents/config) **doivent rester
verts** après migration. Si un test casse, c'est un signal de
régression. Ajustement autorisé uniquement pour :
- Tests qui mockaient `agent.stream` (à mocker via `runtime.run` désormais).
- Tests qui faisaient des assertions sur le nb d'appels OpenAI (peut
  passer de 1 à 2-4).

---

## 13. Roadmap détaillée

### 13.1 Phase 2a — Runtime + Compliance L0 (LIVRÉ — 2026-05-02)

**Critères de done :**

- [x] Migration 148 — table `assistance_agent_decisions` créée et appliquée
- [x] `runtime/agent_loop.py` — loop itératif fonctionnel + tests unit
- [x] `tools/registry.py` + 5 tools L0 compliance (`read_compliance_state`, `read_registration_progress`, `read_documents`, `read_transactions`, `read_external_aml_signals`) livrés et testés
- [x] `tools/shared/classify_actor.py` + tests unit (18)
- [x] `tools/shared/ask_user_question.py` + interrupt loop + tests
- [x] Provider AML mock intégré dans `read_external_aml_signals` (anti-tipping-off filtering — Phase 2b extraira un `external/adapters/`)
- [x] `repositories/compliance_repo.py` (introspectif, schema-driven) + tests
- [x] `service.stream_assistant_turn` patché pour utiliser le runtime (flag `ASSISTANCE_RUNTIME_LOOP_ENABLED`, **défaut `true`** depuis 2026-05 — rollback explicite `false` pour Phase 1 legacy)
- [x] `_require_client` promu globalement via `services/auth/client_id_resolver.py::patch_auth_client_id_from_person` — clôture audit identité (BUG B)
- [x] Court-circuits actor : `ADMIN_BO` 403, `ONBOARDING` 403, `SUSPENDED` réponse standardisée sans data-leak
- [x] **Tests anti-tipping-off** : `TIPPING_OFF_BLACKLIST` + sanitizer + tests scénarios — bloquants CI
- [x] **0 régression** sur les tests Phase 1 (mémoire + agents)
- [x] Doc `MULTI_AGENTS_DATA_SOURCES.md` mise à jour V2 (introspective tools + roadmap 2a/2b/2c)
- [x] Smoke test stack live : import OK des 6 tools compliance, API up, runtime loop wired

**Total tests Phase 2a : 286 verts** (suite unitaire complète passe en ~31s sur le conteneur API).

**Estimation initiale :** ~2 semaines (1 dev). **Réel :** quelques jours en marathon, qualité non-régressée.

### 13.2 Phase 2b — Conversation enquête + 1 provider mock dynamique

- Tool `ask_user_question` activé (l'agent peut clarifier).
- Multi-tour avec collecte progressive d'info.
- `external/adapters/mock_dynamic.py` — mock qui retourne des résultats variés selon l'input (test des branches "watchlist match", "doc quality low", etc.).
- Tests E2E sur 5 scenarios complexes (héritage, dépôt anormal, etc.).

### 13.3 Phase 2c — Mutations L2

- Tools `request_document_upload`, `create_compliance_ticket` actifs en L2.
- UI BO admin Next.js pour reviewer les `agent_decisions` (table à brancher).
- Tests E2E mutations (création ticket, demande de doc déclenche notification).
- Pré-requis : audit user_id Phase 2a clôturé, fix `_require_client` global appliqué.

### 13.4 Phase 3+

- Adapter Sumsub (ou autre provider signé).
- Tools `block_transaction` en L2.
- Réflexion / spec L3 (`block_account`, `close_account`) avec process humain de fond.

---

## 14. Risques connus & dettes techniques

| Risque | Impact | Mitigation |
|---|---|---|
| Coût OpenAI multiplié par `iter_count` | $$ + latence | `MAX_ITER=6` strict, métriques alerte si moyenne > 3 |
| Drift LLM qui invoque un tool non listé | Plantage | OpenAI valide côté serveur ; on log et on retourne une erreur tool standard au LLM (qui peut s'autocorriger) |
| Hallucination de paramètres tool | Comportement faux | JSON schema strict côté SPEC ; validation Pydantic à l'entrée |
| Tipping-off via fuite imprévue (nouveau provider, nouveau champ DB) | **Réglementaire critique** | Suite tests TIPPING_OFF_BLACKLIST en CI bloquant, sanitizer en garde |
| `AuthContext.role` hardcodé (cf. AUDIT § 5.1) | Faux positifs `is_admin` | Backlog Phase 3+ ; en attendant, ne **jamais** se reposer sur `is_admin` dans Compliance V2 |
| Boucle infinie LLM | Latence + coût | `MAX_ITER` + timeout total + log alerte |
| Tools avec side-effects cachés | Mutations non journalisées | Lint check : seuls les tools déclarés L1+ peuvent muter ; revue de code obligatoire pour ajout L1+ |
| Orphelins `auth_*` (cf. AUDIT § 5.2) | NULL non géré → 500 | Tools tolèrent NULL → signal neutre |

---

## 15. Versioning de cette spec

| Date | Version | Phase | Changements |
|---|---|---|---|
| 2026-05-02 | 1.0 | Pré-Phase 2a | Création initiale, validation Option X |
| 2026-05-02 | 1.1 | Phase 2a livrée | Runtime loop + 5 tools L0 + classify_actor + court-circuits + audit identité globalisé. 286 tests verts. |
| 2026-05-06 | 1.2 | Défaut runtime actif | `ASSISTANCE_RUNTIME_LOOP_ENABLED` **true** par défaut ; agents par défaut incluent `trust` ; doc rollback Phase 1 (stub) vs function calling registry ; rappel `data_need_read_policy` = soft warning uniquement. |

> **Règle :** toute évolution structurelle (nouveau type de tool, nouveau
> niveau d'autonomie, nouveau pattern d'adapter) **doit** incrémenter la
> version et ajouter une ligne ici.

---

## 16. Annexe — Pseudocode complet du runtime loop

```python
# services/assistance/agents/runtime/agent_loop.py

async def run_agent_loop(
    *,
    agent_id: str,
    agent_input: AgentInput,
    db: Session,
    correlation_id: str,
) -> AsyncIterator[AgentEvent]:
    """Boucle agentique principale.

    Yields des AgentEvent au fur et à mesure (compatible SSE Phase 1).
    """
    audit_session_id = str(uuid.uuid4())
    actor_kind = classify_actor(agent_input.auth_context, db)

    # Court-circuits avant toute LLM call
    if actor_kind == ActorKind.ADMIN_BO:
        raise HTTPException(403, "actor_admin_bo_not_allowed")
    if actor_kind == ActorKind.SUSPENDED:
        yield AgentEvent.delta(SUSPENDED_RESPONSE)
        yield AgentEvent.done(agent_id=agent_id, iter_count=0,
                              tools_called=[], decision_ids=[])
        return

    yield AgentEvent.started(agent_id=agent_id)

    # Setup
    autonomy_max = config.autonomy_max_for(agent_id)
    if config.global_autonomy_killswitch():
        autonomy_max = "L0"
    available_tools = registry.tools_for(agent_id, autonomy_max=autonomy_max)
    messages = build_initial_messages(agent_id, agent_input, actor_kind)
    decisions: list[str] = []
    tools_called: list[str] = []
    interrupt_with_choices = None

    started_at = time.monotonic()

    for iteration in range(config.max_iter()):
        if time.monotonic() - started_at > config.timeout_seconds():
            yield AgentEvent.error("agent_timeout")
            return

        # Appel LLM (non-stream sauf dernier tour)
        is_final_attempt = (iteration == config.max_iter() - 1)
        response = await openai_client.chat_completion(
            model=config.model_for(agent_id),
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            stream=is_final_attempt,  # stream uniquement le dernier
        )

        if response.has_tool_calls:
            for call in response.tool_calls:
                tool_module = registry.find(agent_id, call.function.name)
                if tool_module is None:
                    # Hallucination LLM, on retourne une erreur exploitable
                    messages.append(tool_error_message(call, "tool_not_found"))
                    continue

                ctx = ToolContext(
                    db=db,
                    client_id=str(agent_input.client_id) if agent_input.client_id else None,
                    person_id=str(agent_input.person_id) if agent_input.person_id else None,
                    user_id=agent_input.user_id,
                    actor_kind=actor_kind,
                    agent_id=agent_id,
                    conversation_id=str(agent_input.conversation_id),
                    iteration=iteration,
                    audit_session_id=audit_session_id,
                    correlation_id=correlation_id,
                )
                args = parse_and_validate(call.function.arguments, tool_module.SPEC)

                t0 = time.monotonic()
                try:
                    result = await with_timeout(
                        tool_module.execute(ctx, **args),
                        seconds=config.tool_timeout(),
                    )
                    duration_ms = int((time.monotonic() - t0) * 1000)
                except TimeoutError:
                    result = {"error": "timeout"}
                    duration_ms = int(config.tool_timeout() * 1000)
                except Exception as exc:
                    logger.exception("tool_failed name=%s", call.function.name)
                    result = {"error": "internal_error"}
                    duration_ms = int((time.monotonic() - t0) * 1000)

                tools_called.append(call.function.name)

                # Persistance agent_decisions
                decision_id = audit.persist_decision(
                    db=db,
                    agent_id=agent_id,
                    iteration=iteration,
                    tool_name=call.function.name,
                    autonomy_level=tool_module.SPEC["autonomy_level"],
                    arguments=args,
                    result_summary=result_summary(result),
                    correlation_id=correlation_id,
                    duration_ms=duration_ms,
                )
                decisions.append(decision_id)

                # Cas spécial : ask_user_question interrompt la boucle
                if result.get("interrupt_with_question"):
                    interrupt_with_choices = result
                    break

                messages.append(tool_result_message(call, result))

            if interrupt_with_choices is not None:
                yield AgentEvent.choices(
                    prompt=interrupt_with_choices["prompt"],
                    options=interrupt_with_choices["options"],
                    allow_freeform=interrupt_with_choices["allow_freeform"],
                )
                yield AgentEvent.done(
                    agent_id=agent_id,
                    iter_count=iteration + 1,
                    tools_called=tools_called,
                    decision_ids=decisions,
                    early_break_reason="choices_emitted",
                )
                return

            # Continue loop : LLM pourra raisonner sur les résultats
            continue

        # Pas de tool call → réponse finale
        if is_final_attempt:
            # streamée
            async for delta in response.iter_deltas():
                yield AgentEvent.delta(delta)
        else:
            # déjà reçue d'un coup
            yield AgentEvent.delta(response.content)

        yield AgentEvent.done(
            agent_id=agent_id,
            iter_count=iteration + 1,
            tools_called=tools_called,
            decision_ids=decisions,
            early_break_reason="final_answer",
        )
        return

    # MAX_ITER atteint
    yield AgentEvent.delta(MAX_ITER_FALLBACK_MESSAGE)
    yield AgentEvent.done(
        agent_id=agent_id,
        iter_count=config.max_iter(),
        tools_called=tools_called,
        decision_ids=decisions,
        early_break_reason="max_iter",
    )
```

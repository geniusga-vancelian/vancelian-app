# Architecture multi-agents — Assistance Vancelian

> **Statut :** Router v2 — qualité de la demande en 3 niveaux + tags
> hiérarchisés + clarif catalogue hybride + advisor-first multi-angle
> (v3.1) — sur la base Phase 2 wiki + guard-rail product + slider
> Crypto Bundles + bundle detail card + dedup runtime des tool calls
> + slot mémoire `current_topic` + hot-path follow-up + cleanup
> catalogue + Karpathy LLM-as-retriever + admin monitoring 3 colonnes
> (v3.0) — orchestration multi-agents + base de connaissance markdown
> 243 fiches + table SQL `product_knowledge` cleanée + fiche
> `vancelian_product_catalog` canonique + garde-fou cross-référentiel
> SQL ↔ wiki MD + retriever LLM avec fallback keyword + back-office
> admin pour monitorer / debugger les conversations IA depuis la
> fiche customer.
>
> **Dernière mise à jour :** 2026-05-05 (v2.11 — Cognitive Bot v4 Lot 7 V1.1 :
> auto-QCM SSE branché end-to-end avec garde-fous objective-aware,
> intégration Flutter `AutoQcmFooter`, 4ᵉ colonne admin « Synthèse cognitive »
> dans la vue conversation, 1472 tests assistance verts, +15 tests Flutter ;
> cf. `CLIENT_DISCOVERY.md` §§ 4.4–4.6)
>
> **Code de référence :** `services/arquantix/api/services/assistance/agents/`
>
> **Documents liés :**
> - `ORCHESTRATOR.md` — **doc complète du router v2** (3 niveaux,
>   prompt complet, catalogues, hot-path, pattern advisor-first) **NEW v3.1**
> - `COMPLIANCE_TOPICS.md` — spec Phase 2b + 2c (tree + orchestration)
> - `PRODUCT_AGENT.md` — spec Phase 2c (vrai agent product)
> - `MULTI_AGENTS_RUNTIME.md` — runtime, autonomy, audit (Phase 2a)
> - `MULTI_AGENTS_DATA_SOURCES.md` — cartographie data introspective
> - `AUDIT_AUTH_IDENTITIES.md` — règles d'identité
> - `MEMORY.md` — mémoire long-terme (fondation)
> - `API.md` — endpoints REST
> - `ARCHITECTURE.md` — vue d'ensemble système

---

## 0. TL;DR

L'assistance Vancelian passe d'un **chatbot monolithique** à un **système agentique**
composé d'un **orchestrateur** (router) qui comprend l'intention de l'utilisateur
et qui dispatche vers l'agent spécialisé approprié. La mémoire long-terme
(documentée dans `MEMORY.md`) est conservée **inchangée** et devient le
substrat partagé entre tous les agents.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Flutter mobile — 1 fil de conversation, badge agent visible        │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTPS / SSE
┌──────────────────────────────────▼──────────────────────────────────┐
│  FastAPI — service.py — point d'entrée /chat/turn/stream            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Orchestrator / Router                            │  │
│  │  Input  : user message + memory state (long_memory + summary) │  │
│  │  Output : { agent_id, confidence, reasoning }                 │  │
│  │           OU SSE event "choices" si confidence < 0.5          │  │
│  └────────────────────────┬──────────────────────────────────────┘  │
│                           │ dispatch                                │
│       ┌────────┬──────────┼──────────┬──────────┬────────┬───────┐  │
│       ▼        ▼          ▼          ▼          ▼        ▼       ▼  │
│   default  compliance  advisor   product    market   trust  (futurs)│
└─────────────────────────────────────────────────────────────────────┘
```

> **Cognitive Bot v4 (2026-05-04)** — Le runtime injecte désormais
> à chaque tour un état cognitif (`emotional_intent`,
> `conversation_stage`, `trust_level`, `knowledge_level`) et un
> objectif (`primary_goal`, `next_best_action`, `stop_pushing`)
> dans les system prompts du router et des agents experts. Les
> agents experts répondent dans un format en 4 temps (ACK
> émotionnel → reformulation → valeur → orientation). L'agent
> `trust` (Lot 4) est dédié à la rassurance institutionnelle. La
> doc dédiée et complète : [`COGNITIVE_BOT.md`](COGNITIVE_BOT.md).

---

## 1. Décisions architecturales (les 9 ancres)

Ces décisions sont **figées**. Toute déviation doit faire l'objet d'un nouveau
doc d'ADR (Architecture Decision Record) à part.

### 1.1 Modèle de routage — Function calling natif OpenAI

**Décision : function calling natif** (pas de classifier custom, pas de keyword matching).

L'orchestrateur expose **N tools** (un par agent) à un LLM `gpt-4o-mini`. Le
modèle appelle l'outil approprié en JSON natif, avec un argument `reasoning`
court. Si la confiance interprétée (heuristique sur la qualité du tool call)
est **< 0.5**, on bascule en mode QCM (cf. § 1.9).

**Pourquoi pas un classifier ad-hoc** : maintenance lourde (intent classes,
embeddings), moins flexible que function calling, et surtout function calling
permet d'**enrichir la réponse du router** (ex : `agent_id="compliance"` +
`extracted_entity="transaction_id=ABC123"`) que les agents peuvent ensuite
exploiter.

### 1.2 UX Flutter — Attribution discrète

**Décision : 1 fil de conversation unique + badge `agent_used`** au-dessus
des bulles assistant.

| Agent | Label badge | Couleur design system |
|---|---|---|
| `default` | (pas de badge) | — |
| `compliance` | « Assistance compte » | `AppColors.semanticInfo` |
| `advisor` | « Conseil placement » | `AppColors.indigo` |
| `product` | « Produits Vancelian » | `AppColors.accent` |
| `market` | « Veille marché » | `AppColors.semanticWarning` |

**Pourquoi** : transparence sans fragmenter l'expérience. L'utilisateur reste
dans 1 conversation continue mais comprend qui répond.

### 1.3 Storage — Mono-conversation + 3 colonnes sur `assistance_messages`

**Décision : 1 seule conversation logique**, qu'importe le nombre d'agents
mobilisés. Migration légère (Alembic 147) :

```sql
ALTER TABLE assistance_messages
  ADD COLUMN agent_used VARCHAR(32),         -- nullable, "default" en fallback
  ADD COLUMN message_type VARCHAR(16) NOT NULL DEFAULT 'text',  -- 'text' | 'choices'
  ADD COLUMN message_payload JSONB;          -- nullable, populé si message_type='choices'
```

**Pourquoi** : la mémoire long-terme reste cross-agents naturellement (elle
est rattachée au client, pas à l'agent). Un éventuel besoin futur de
filtrer par agent (ex. *« montre-moi mes échanges advisor »*) se fait par
simple `WHERE agent_used = 'advisor'`.

### 1.4 Toolbox par agent — V1 minimale, V2 enrichie

**Décision : V1 « slim »** — on livre l'**ossature complète** (router + 4
agents) avec des tools stubs sur Product/Market, et des tools DB lecture
seule sur Compliance/Advisor. RAG, news, modèle d'allocation = phases
ultérieures.

| Agent | Tools V1 (squelette) | Tools V2 (cible) |
|---|---|---|
| `compliance` | `get_account_status(client_id)` (stub → tables existantes), `get_recent_transactions(client_id, limit=10)` (stub) | KYC en temps réel, justificatifs manquants, escalade humain |
| `advisor` | `get_client_long_memory()`, `get_portfolio_snapshot()` (stub) | Vraies règles d'allocation, simulateur Monte Carlo |
| `product` | `get_product_summary(slug)` (stub : lit `pages` table) | RAG vectoriel sur fiches PDF/MD |
| `market` | `get_recent_news(topic, limit=5)` (stub) | API news live + base d'analyses internes |
| `router` | `route_to(agent_id, reasoning)`, `ask_clarification(reason, options)` | escalade humain, multi-routing |

### 1.5 Modèle LLM par agent — Configurable

**Décision : 1 env var par agent**, défaut commun = `gpt-4o-mini`,
recommandation V1 :

```env
ASSISTANCE_AGENT_ROUTER_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_DEFAULT_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_COMPLIANCE_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_ADVISOR_MODEL=gpt-4o          # ↑ qualité raisonnement
ASSISTANCE_AGENT_PRODUCT_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_MARKET_MODEL=gpt-4o-mini
```

Permet de scaler le coût/qualité indépendamment par agent sans redéployer.

### 1.6 Mémoire long-terme — Read par tous, Write uniquement par summarizer

**Décision** : la mémoire long-terme (`MEMORY.md`) reste **gérée
exclusivement par le summarizer post-tour**. Aucun agent n'écrit en mémoire
en V1.

Tous les agents **lisent** la mémoire long-terme via `memory.load_memory_state()`
et l'incluent dans leur system prompt local (sauf le router qui l'utilise
aussi pour mieux comprendre l'intention).

**Évolution V2 possible** : un agent peut « pousser » un fact (ex. l'advisor
détecte une nouvelle préférence). À cadrer plus tard via ADR.

### 1.7 Fallback / escalade — 3 niveaux

| Cas | Comportement |
|---|---|
| Router indécis (confidence < 0.5) | **SSE event `choices`** (cf. § 1.9) |
| Agent ne sait pas répondre (tool retourne erreur ou data vide) | Réponse texte type *« Je n'ai pas l'info en base, peux-tu préciser ? »* + log warning |
| Question hors scope (ex. blagues, météo) | Bascule sur `default` (assistant généraliste actuel) |
| Cas critique compliance détecté (ex. fraude, blocage légal) | Réponse texte avec consigne *« Contacte le support sous 24h, voici l'email/numéro »* + log error + (V2) trigger Slack/email équipe |

### 1.8 Observabilité — Tracing structuré dès la V1

**Décision : log JSON par tour** (sans nouvelle table en V1, on utilise les
logs Docker) :

```json
{
  "event": "assistance.agent.tour",
  "conv_id": "...",
  "turn": 5,
  "user_message_excerpt": "te rappelles-tu de ma stratégie...",
  "router_decision": {
    "agent_id": "advisor",
    "confidence": 0.87,
    "reasoning": "L'utilisateur demande une stratégie d'allocation déjà discutée"
  },
  "agent_response": {
    "agent_id": "advisor",
    "model": "gpt-4o",
    "tools_called": ["get_client_long_memory"],
    "latency_ms": 2341,
    "tokens_in": 1822,
    "tokens_out": 510
  }
}
```

**V2** : nouvelle table `assistance_agent_traces` (1 ligne par décision)
pour requêtes analytiques et dashboard.

### 1.9 QCM en cas d'ambiguïté — Nouveauté UX

**Décision : nouveau type d'event SSE `choices`** + nouveau type de message
en DB (`message_type='choices'`).

#### 1.9.1 Format SSE

```
event: choices
data: {
  "type": "choices",
  "message_id": "<uuid>",
  "prompt": "Pour mieux te répondre, peux-tu préciser ?",
  "options": [
    {"id": "compliance", "label": "Mon compte / dépôts / transactions"},
    {"id": "product",    "label": "Information sur les produits Vancelian"},
    {"id": "advisor",    "label": "Conseil en placement"},
    {"id": "market",     "label": "Actualités marché"},
    {"id": "freeform",   "label": "Rien de tout ça — je reformule"}
  ],
  "allow_freeform": true
}
```

#### 1.9.2 Stockage en DB

```sql
INSERT INTO assistance_messages
  (role, content, message_type, message_payload, agent_used, ...)
VALUES
  ('assistant', 'Pour mieux te répondre…',  -- fallback texte si client ne supporte pas le QCM
   'choices',
   '{"options":[{"id":"compliance","label":"…"}, …], "allow_freeform": true}'::jsonb,
   'router',
   ...);
```

**Pourquoi du JSONB et pas un texte structuré** : pour permettre à n'importe
quel client (Flutter, web futur, API tierce) de rendre le QCM nativement
sans parser du Markdown. Le `content` reste rempli en plain text pour les
clients legacy / les emails de transcription / le summarizer.

#### 1.9.3 Réponse utilisateur

Quand le client clique sur une option **non-`freeform`** :
```http
POST /api/app/assistance/conversations/{conv_id}/turn/stream
{
  "user_message": "Mon compte / dépôts / transactions",   -- texte de l'option, pour traçabilité
  "agent_hint": "compliance"                              -- saute le router, dispatch direct
}
```

Quand le client clique sur **`freeform`** :
- Le QCM se ferme côté UI
- Le focus revient sur l'input texte
- L'utilisateur retape librement → le router refait sa passe normale.

#### 1.9.4 Comportement Flutter

`search_screen.dart` apprend à rendre les messages `message_type='choices'`
comme une **liste de boutons cliquables** (avec le widget existant
`DSSelectableInsetTile`) au lieu d'une bulle Markdown.

---

## 2. Schéma de chaque agent

Chaque agent est une classe Python qui implémente `AgentBase` :

```python
class AgentBase(Protocol):
    agent_id: str                                   # "compliance", "advisor", ...
    display_label: str                              # affiché dans le badge Flutter
    system_prompt_path: str                         # chemin vers le fichier prompt
    model_env_var: str                              # var d'env pour choisir le modèle

    async def stream(
        self,
        *,
        user_message: str,
        memory_state: MemoryState,
        recent_turns: list[dict],
        router_metadata: dict,
    ) -> AsyncIterator[dict]:                       # yields {"type": "delta"|"done"|...}
        ...
```

### 2.1 `default` (assistant généraliste)

- **Rôle** : fallback pour toutes les questions hors scope des autres agents
  (blagues, conversation libre, salutations, questions générales sur Vancelian).
- **System prompt** : exactement celui qu'on a aujourd'hui dans `llm.py`.
- **Mémoire long-terme** : injectée comme aujourd'hui (rolling summary +
  long memory).
- **Tools** : aucun.
- **C'est l'agent de continuité** : zéro régression sur l'expérience actuelle.

### 2.2 `compliance` (assistance compte) — **Phase 2b : tree system**

- **Rôle** : répondre aux questions opérationnelles sur le compte de
  l'utilisateur — statut KYC, dépôts en cours/bloqués, transactions en
  attente, validations administratives, demandes de documents.
- **Ton** : factuel, court, sec. Pas de pédagogie financière.
- **Pattern à 2 niveaux (Phase 2b — voir [`COMPLIANCE_TOPICS.md`](COMPLIANCE_TOPICS.md))** :
  - Le router top-level continue à classifier en `compliance` générique.
  - L'agent `compliance` est un **dispatcher** : son seul tool est
    `diagnose_compliance_topic` (forcé au tour 0) qui agrège les datas
    KYC + registration + docs + transactions et choisit
    `dominant_topic ∈ {registration, remediation, transactional, general}`.
  - Le runtime **switch dynamiquement** vers le sub-agent
    `compliance.<topic>`, recharge son prompt système et son toolset, et
    poursuit la boucle. SSE event `thinking` émis pendant la phase
    diagnostique pour UX (ENV `ASSISTANCE_STREAM_THINKING_ENABLED`).
- **Sub-agents (Phase 2b livrée)** :
  - `compliance.registration` — KYC en cours / premier dépôt /
    `propose_resume_registration`
  - `compliance.remediation` — docs manquants / signaux AML (avec
    anti-tipping-off strict)
  - `compliance.transactional` — *« où est mon dépôt ? »* — tool
    `read_transaction_detail` + escalade vers agent `product` future
    (Phase 2c) pour réassurance
  - `compliance.general` — fallback large (tous tools L0 read-only)
- **Action CTAs** : extension de `message_type=choices` avec
  `deep_link` et `agent_hint` (mutuellement exclusifs). Whitelist
  stricte côté backend (`action_cta_catalog`) + résolution Flutter
  par `AssistanceDeepLinkResolver` (anti LLM hallucination URL).
- **Tools L0 (Phase 2a, hérités)** :
  - `read_compliance_state` (KYC + account)
  - `read_registration_progress` (étapes onboarding)
  - `read_documents` (status docs requis vs fournis)
  - `read_transactions(limit)` (historique récent)
  - `read_external_aml_signals` (gated, anti-tipping-off)
- **Tools L0 nouveaux (Phase 2b)** :
  - `propose_resume_registration` — deep-link `vancelian://app/onboarding/resume`
  - `read_transaction_detail(transaction_id)` — détails d'un mouvement
- **Tools L1 (Phase 3+)** : `request_doc_upload`, escalade humain.
- **Cas d'escalade** : si tool retourne `kyc_state="rejected"` ou si la
  question contient un mot-clé sensible (« fraude », « bloqué »,
  « urgent »), l'agent répond avec consigne de contacter le support +
  log `error`.

### 2.3 `advisor` (conseil en placement / robo-advisor)

- **Rôle** : conseiller l'utilisateur sur ses choix de placement, lui
  expliquer une stratégie d'allocation, simuler des scénarios, répondre à
  *« qu'est-ce que tu me recommandes ? »*.
- **Ton** : pédagogue, structuré, avec disclaimers.
- **Modèle** : `gpt-4o` (nuance > vitesse).
- **Tools V1** :
  - `get_client_long_memory()` → renvoie le bloc structuré (objectifs, horizon, etc.)
  - `get_portfolio_snapshot()` (stub : retourne du JSON faux pour V1)
- **Tools V2** : modèle d'allocation hard-codé puis vraie ingénierie
  financière (Monte Carlo, frontière efficiente).

### 2.4 `product` (connaissance produits) — **Phase 2c livrée**

- **Rôle** : seule source factuelle des informations produits (délais
  SEPA, dépôt carte, retrait, KYC, swap…) et définitions
  (Vault / Livret / SCPI). Spécification complète dans
  [`PRODUCT_AGENT.md`](PRODUCT_AGENT.md).
- **Ton** : informatif, précis, sans hallucination. Aucun conseil
  d'investissement.
- **Statut V1 (Phase 1)** : stub jamais activé en runtime — placeholder.
- **Statut V2 (Phase 2c)** : agent réel avec son propre prompt
  ([`prompts/product_system.md`](../../services/arquantix/api/services/assistance/prompts/product_system.md))
  + table SQL `product_knowledge` (10 entrées seedées via Alembic 149)
  + invoqué exclusivement via `consult_specialist` par
  `compliance.transactional` ou `compliance.general`. Le router
  top-level **ne route pas** directement vers `product` en Phase 2c
  (gardé pour Phase 5+ avec RAG public).
- **Tools L0 (Phase 2c)** :
  - `read_product_knowledge(slug)` → fiche `product_knowledge` complète
  - `list_product_knowledge_topics(topic?)` → introspection des slugs
    (debug)
  - `show_instrument_card(symbol)` → carte UI prix temps réel
    (Phase 2c.6)
  - `ask_user_question` → autorisé pour clarifier un slug ambigu
- **Tools L0 (Phase 2 wiki, livré 2026-05-04)** :
  - `select_wiki_pages(question, top_k?, category?)` → pré-filtre
    Karpathy keyword sur les 243 fiches markdown du wiki produit
    (`assistance/data/wiki/`). Retourne top_k ≤ 10 candidats avec
    score + extraits questions. Pas de body. Pas d'appel LLM dans
    le retrieval.
  - `read_wiki_page(category, slug)` → lecture complète d'une fiche
    (frontmatter + sections `Short answer` + `Details` + sources).
    Validation anti-path-traversal via whitelist
    `wiki_repo.ALL_CATEGORIES`.
- **Tools interdits** : pas de `consult_specialist` (anti-récursion),
  pas de `handoff_to_agent`, aucun accès aux données client.
- **Tools V3 (Phase 5+)** : RAG vectoriel sur le wiki MD (pgvector
  ou Qdrant) quand le volume dépassera ~1 000 fiches. Le pré-filtre
  keyword Phase 2 reste pertinent en deçà.

### 2.5 `market` (veille marché)

- **Rôle** : synthèse actualités marchés, opinion sur des indices/secteurs,
  contexte macro, lien avec le portefeuille du client.
- **Ton** : analytique, factuel, dates explicites.
- **Tools V1 (stub)** :
  - `get_recent_news(topic, limit=5)` → retourne 3-5 items hard-codés en V1.
- **Tools V2** : API news live (Bloomberg / Refinitiv / RSS curatés) + base
  d'analyses internes équipe.

---

## 3. Flux complet d'un tour

### 3.1 Cas nominal (router décide, agent répond)

```
1. Client mobile → POST /chat/turn/stream { user_message: "..." }
2. service.py crée le user_msg en DB
3. service.py appelle router.classify(user_message, memory_state)
   → { agent_id: "compliance", confidence: 0.87, reasoning: "..." }
4. service.py log JSON la décision
5. service.py instancie l'agent compliance
6. compliance.stream(...) consomme ses tools, appelle OpenAI en stream
7. SSE delta tokens → client (effet machine à écrire)
8. SSE event "done" → message assistant persisté avec agent_used="compliance"
9. service.py schedule consolidation mémoire long-terme (inchangé)
```

### 3.2 Cas QCM (router indécis)

```
1. Client mobile → POST /chat/turn/stream { user_message: "j'ai un problème" }
2. service.py crée le user_msg en DB
3. router.classify(...) → { confidence: 0.32 }   (< seuil 0.5)
4. service.py génère un QCM (4-5 options + "rien de tout ça")
5. SSE event "choices" → client
6. service.py persiste un message assistant message_type='choices' avec payload JSONB
7. Flutter affiche les boutons (DSSelectableInsetTile)
8. Client clique "Mon compte" :
   a. POST /chat/turn/stream { user_message: "Mon compte", agent_hint: "compliance" }
   b. router est SHORTCIRCUITED (agent_hint présent)
   c. dispatch direct → compliance agent
   OU
   Client clique "Rien de tout ça" :
   a. UI dismiss le QCM, focus sur input texte
   b. Aucune requête backend
```

### 3.3 Cas escalade compliance critique

```
1. Client : "Mon dépôt est bloqué depuis 3 jours, urgent"
2. router → compliance (confidence 0.95)
3. compliance.stream() :
   - call get_account_status() → {kyc_state: "validated", account_active: true}
   - call get_recent_transactions() → 1 dépôt status="hold"
   - LLM détecte mot-clé "urgent" + status="hold"
   - LLM répond avec consigne "Contacte support@vancelian.com…"
4. service.py log error "compliance.escalation conv=... reason=hold_urgent"
5. (V2) trigger Slack #support-tickets
```

---

## 4. Données / Schéma

### 4.1 Migration Alembic 147

```python
# 147_assistance_messages_agent_columns.py
def upgrade():
    op.add_column("assistance_messages",
        sa.Column("agent_used", sa.String(32), nullable=True),
        schema="public",
    )
    op.add_column("assistance_messages",
        sa.Column("message_type", sa.String(16), nullable=False,
                  server_default="text"),
        schema="public",
    )
    op.add_column("assistance_messages",
        sa.Column("message_payload", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        schema="public",
    )
    op.create_index("ix_assistance_messages_agent_used",
                    "assistance_messages", ["agent_used"], schema="public")
```

### 4.2 SQLAlchemy / Prisma

Mirror systématique : `database.py` (SQLAlchemy `AssistanceMessage`) +
`schema.prisma` (`AssistanceMessage`).

### 4.3 Backward compat

- Tous les messages existants ont `agent_used=NULL`, `message_type='text'`,
  `message_payload=NULL` → considérés comme produits par l'`default` agent.
- Aucune cassure rétrograde côté Flutter (un client legacy qui ignore
  `message_type` voit juste les bulles texte normales).

---

## 5. Configuration

### 5.1 Variables d'environnement

```env
# Router
ASSISTANCE_AGENT_ROUTER_MODEL=gpt-4o-mini
ASSISTANCE_ROUTER_CONFIDENCE_MIN=0.5      # < seuil → QCM
ASSISTANCE_ROUTER_TEMPERATURE=0.1         # déterministe

# Agents
ASSISTANCE_AGENT_DEFAULT_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_COMPLIANCE_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_ADVISOR_MODEL=gpt-4o
ASSISTANCE_AGENT_PRODUCT_MODEL=gpt-4o-mini
ASSISTANCE_AGENT_MARKET_MODEL=gpt-4o-mini

# Feature flag global (kill-switch)
ASSISTANCE_MULTI_AGENT_ENABLED=true       # false → 100% legacy default
```

### 5.2 Kill-switch

`ASSISTANCE_MULTI_AGENT_ENABLED=false` → toutes les requêtes vont à
l'agent `default` (= comportement actuel pré-multi-agents). Permet un
rollback instantané en cas de souci en prod, sans redeploy.

---

## 6. Roadmap

| Phase | Périmètre | Statut |
|---|---|---|
| **0 — Design** | Ce document | ✅ |
| **1 — Squelette** | Migration 147, base.py, router.py, 5 agents stubs, prompts, SSE choices, patch service.py, env vars, tests | ✅ livré |
| **2a — Compliance runtime + tools L0** | Function calling iterative loop, `classify_actor`, identity short-circuits, 5 tools L0 read-only (`read_compliance_state`, `read_registration_progress`, `read_documents`, `read_transactions`, `read_external_aml_signals`), audit `assistance_agent_decisions`, anti-tipping-off | ✅ livré |
| **2b — Compliance tree system** | Sub-agents `compliance.{registration,remediation,transactional,general}`, tool dispatcher `diagnose_compliance_topic`, `action_cta_catalog` whitelist, `AssistanceChoiceOption.deep_link`, SSE `thinking`, Flutter `AssistanceDeepLinkResolver`, prompts dédiés, **140 tests verts** — voir [`COMPLIANCE_TOPICS.md`](COMPLIANCE_TOPICS.md) | ✅ livré |
| **2c — Orchestration multi-agents + vrai agent product** | `handoff_to_agent` (remediation → transactional / general), `consult_specialist` (compliance → product), `tour_shared_context` whitelisté, vrai agent `product` avec table SQL `product_knowledge` (10 seeds, migration 149), `agent_chain` + `consultations` audit dans `message_payload.metadata`, garde-fous `MAX_CHAIN_DEPTH=1` & `MAX_CONSULTATIONS_PER_TOUR=3`, **530 tests verts** — voir [`COMPLIANCE_TOPICS.md`](COMPLIANCE_TOPICS.md) §12 + [`PRODUCT_AGENT.md`](PRODUCT_AGENT.md) | ✅ livré |
| **2d — Compliance L1** | `request_doc_upload` (L1, écran upload Flutter), audit BO admin reviewer | ⏳ |
| **3 — Advisor V1** | Tools portfolio + règles d'allocation, prompts affinés, disclaimers | ⏳ |
| **4 — UX Flutter** | Widget QCM (DSSelectableInsetTile), badge agent_used, transitions visuelles | ✅ partiel (deep-link resolver livré 2b) |
| **5 — Product (RAG)** | Indexation pgvector ou Qdrant, ingestion fiches PDF/MD, retrieval | ⏳ projet à part |
| **6 — Market** | Connecteur news (RSS, API), base analyses internes | ⏳ projet à part |
| **7+ — Marketing, etc.** | TBD | ⏳ |

---

## 7. Tests

### 7.1 Unit tests (par agent)

- Mock OpenAI, vérifier system prompt construit, tools déclarés, parsing
  des tool calls.
- Test du sanitizer de réponse (filtres PII, longueur, format).

### 7.2 Integration tests (router)

- Mock du LLM router, vérifier dispatch correct selon `agent_id` retourné.
- Tester le seuil de confiance (< 0.5 → SSE choices).
- Tester `agent_hint` (shortcut, pas d'appel router).

### 7.3 E2E (un par agent)

- Avec une vraie DB transactionnelle, vérifier qu'un message est persisté
  avec le bon `agent_used`, `message_type`, `message_payload`.

### 7.4 Régression sur l'agent `default`

- Suite existante (memory unit + integration) doit rester verte → garantit
  zéro régression sur le comportement actuel.

---

## 8. Observabilité — Logs structurés à grepper

```bash
# Toutes les décisions de routing
docker logs arquantixrecovery-arquantix-api-1 | grep "assistance.agent.tour"

# Décisions router avec confiance basse
docker logs ... | jq 'select(.event == "assistance.agent.tour" and .router_decision.confidence < 0.6)'

# Latences par agent
docker logs ... | jq 'select(.event == "assistance.agent.tour") | {agent: .agent_response.agent_id, ms: .agent_response.latency_ms}'
```

---

## 8.5 Mécanismes de stabilité conversationnelle (v2.8 patch — 2026-05-04)

Suite à l'analyse de la conv `5bef01e9` (3 follow-ups consécutifs sur le
bundle TOP_5 où le router LLM a flippé sur `market` à cause d'un mot-clé
isolé « perf »), 3 garde-fous **complémentaires** ont été ajoutés au
runtime — déterministes, cheap, observables.

### 8.5.1 Dédoublonnage runtime des tool calls dans un même turn

**Code :** `services/assistance/agents/runtime/agent_loop.py` ::
`DEDUPABLE_TOOLS` + `tool_call_cache`.

Cas réel : conv `5bef01e9` turn 4, `show_crypto_bundles` appelé 2× avec
exactement les mêmes args dans le même turn → tokens / latence / DB
gaspillés + déclenchement à tort du guard-rail anti-hallucination.

Mécanisme :
  - Cache local au turn (= scope `run_agent_loop`) clé `(tool_name,
    frozen_args)`, valeur = `tool_result`.
  - Au 2ᵉ appel identique, on renvoie le cache + un hint `_dedup_hint`
    dans le `tool_result` pour signaler au LLM de finaliser sa réponse.
  - Périmètre : whitelist `DEDUPABLE_TOOLS` (idempotents read-only
    uniquement). Orchestration & interactifs **exclus**
    (`consult_specialist`, `handoff_to_agent`, `ask_user_question`).
  - Erreurs (timeout / internal) **non-cachées** → retry possible.
  - Hits cache **non-persistés** dans `assistance_agent_decisions`.

Logs : `agent_loop.tool_dedup_hit agent=... tool=... iteration=... hits=N`.

Tests : `tests/test_assistance_runtime_dedup_unit.py` (8 tests).

### 8.5.2 Slot mémoire `current_topic`

**Code :** `services/assistance/conversation_topic.py` + colonne JSONB
`assistance_conversations.current_topic` (migration 150).

Cas réel : sur un follow-up déictique « précisément les perf sont bonnes
sur ce bundle ? », le router LLM ignore que « ce bundle » désigne TOP_5
(conv `5bef01e9` turn 3) et bascule sur `market`.

Mécanisme :
  - **Auto-set** par le runtime après chaque tool call ancrant
    (`show_bundle_detail` → kind=`vancelian_product`,
    `show_instrument_card` → kind=`instrument`,
    `read_wiki_page` / `read_product_knowledge` → kind=`topic_other`).
    Cf. `TOPIC_ANCHORING_TOOLS`.
  - **Listes ne ancrent pas** : `show_crypto_bundles` /
    `select_wiki_pages` retournent un panel d'options, pas une entité
    nommée → délibérément hors de la whitelist.
  - **Lecture par le router** : `service.py::_safe_get_current_topic`
    injecte le slot dans `agent_input.memory_state["current_topic"]`,
    et `router._build_topic_block` rend une ligne `[CONTEXT TOPIC]`
    dans le system prompt invitant le LLM à conserver l'`agent_owner`
    sur les déictiques.
  - **Skip en sous-loop consult** (`chain_depth > 0`) : un specialist
    consulté n'impose pas son topic au caller.

Schéma JSONB :
```json
{
  "kind": "vancelian_product" | "instrument" | "topic_other",
  "product_code": "TOP_5",
  "instrument_symbol": "BTC",
  "agent_owner": "product",
  "set_at_turn": 4,
  "set_by_tool": "show_bundle_detail",
  "confidence": 0.95,
  "set_at": "2026-05-04T18:14:55Z"
}
```

Tests : `tests/test_assistance_conversation_topic_unit.py` (28 tests).

### 8.5.3 Hot-path follow-up court

**Code :** `services/assistance/router_hot_path.py` +
`assistance_router_hot_path_enabled()` (config).

Cas réel : 90 % des follow-ups dans nos conversations font ≤ 60 chars
et restent sur le même agent. L'appel LLM router consomme 150-300 ms
+ ~500 tokens et flippe parfois sur un mot-clé.

Mécanisme :
  - Bypasse `agent_router.classify(...)` quand toutes les conditions
    sont réunies :
    1. `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=true` (défaut).
    2. `len(user_message.strip()) ≤ ASSISTANCE_ROUTER_HOT_PATH_MAX_CHARS`
       (défaut 60).
    3. Dernier message assistant émis par un agent expert
       (`product`/`compliance`/`advisor`/`market`) — pas `default` ni
       `router`.
    4. Pas de signal de changement de sujet (`par contre`, `sinon`,
       `au fait`, `autre question`, …).
    5. Pas de `agent_hint` (clic QCM déjà géré côté `_decide_agent`).
  - Émet `RouterDecision(agent_id=last_agent, confidence=0.85,
    reasoning="hot_path_short_followup")`.
  - Faux positifs limités par la liste `TOPIC_CHANGE_SIGNALS`. Faux
    négatifs (LLM appelé sans nécessité) tolérés.

Logs : `assistance.agent.hot_path_bypass conv=... agent=...`.

Kill switch : `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false`.

Tests : `tests/test_assistance_router_hot_path_unit.py` (46 tests).

### 8.5.4 Combinaison des 3 mécanismes

Les 3 jouent à des niveaux différents et se **renforcent** :

| Mécanisme | Couche | Effet | Coût |
|---|---|---|---|
| 8.5.3 hot-path | router input | Stabilise l'agent_id | -300 ms / -500 tokens |
| 8.5.2 topic slot | router prompt | Stabilise classifications LLM | +1 ligne prompt |
| 8.5.1 dedup | agent loop | Évite re-exécutions tool | -1 LLM call si LLM ré-appelle |

Si le hot-path bypass passe, on n'appelle pas le router → le slot
n'est pas consommé ce tour mais **continue d'exister** pour le tour
suivant si jamais le hot-path ne se déclenche pas (message > 60 chars).

---

## 8.6 Admin monitoring — Conversations IA depuis la fiche customer (v3.0 — 2026-05-04)

Ajout d'un **back-office read-only** pour le support et l'équipe
produit pour monitorer / debugger les conversations IA d'un client
sans avoir à requêter manuellement la DB.

### Surface backend

3 endpoints FastAPI sous le préfixe `/api/admin/assistance/conversations`,
guard `require_admin_or_ops()`. Code dans
`services/assistance/admin_conversations_router.py`.

| Endpoint | Description |
|---|---|
| `GET ?client_id=&person_id=&status=&limit=&offset=` | Liste paginée des conversations d'un client. Accepte `client_id` (UUID `pe_clients`) **OU** `person_id` (UUID `persons`, résolu serveur). Renvoie counts pré-agrégés (msg, tool calls, erreurs) par conversation + agrégats globaux. |
| `GET /{conversation_id}` | Détail conversation : metadata + messages ordonnés par `turn_index` + `conversation_summary` + `conversation_facts` + `current_topic`. |
| `GET /{conversation_id}/decisions` | Workflow trace = tous les `assistance_agent_decisions` ordonnés par `iteration` (audit Karpathy : tool name, args, result, duration, error_code, autonomy, agent_id). |

Pas de POST/PUT/DELETE en v1 (close/replay/delete = hors scope).

15 tests dans `test_assistance_admin_conversations_router.py` couvrant
auth, validation, counts, pagination, filtres, 404.

### Surface front (Next.js admin web)

3 ajouts :

1. **Section « Conversations IA »** dans `/admin/customers/[personId]/page.tsx`
   (composant `components/admin/AssistanceConversationsSection.tsx`).
   Compteurs globaux + 3 dernières conversations + lien voir tout.
2. **Page liste** `/admin/customers/[personId]/assistance/conversations`
   avec filtre status (active / closed / all) + pagination.
3. **Page détail 3 colonnes**
   `/admin/customers/[personId]/assistance/conversations/[conversationId]`:
   * Colonne gauche : timeline compacte (1 ligne / turn) avec filtres
     (user / assistant) et badge nombre de tool calls par turn.
   * Colonne centre : reproduction fidèle du chat client (rôles,
     embeds avec `message_payload` JSON dépliable, agent_used).
   * Colonne droite : workflow trace de l'arbre des décisions du turn
     sélectionné, groupé par `agent_id`. Click sur un tool call →
     drawer latéral avec `arguments` / `result_summary` / reasoning /
     metadata complets.
   * Footer : `conversation_summary` + `conversation_facts` (mémoire
     long-terme du bot pour ce client).
   * Export JSON (debug offline) + bouton refresh.

Tout est read-only, snapshot à l'ouverture, pas de polling.

### Routes Next.js proxy

  * `src/app/api/admin/assistance/conversations/route.ts` (GET liste)
  * `src/app/api/admin/assistance/conversations/[conversationId]/route.ts`
  * `src/app/api/admin/assistance/conversations/[conversationId]/decisions/route.ts`
  * Helper partagé : `src/lib/assistance-conversations-proxy.ts`
    (auth + forward vers FastAPI avec `X-Actor-*`, timeout 15 s).

### Code couleur agent (cohérence UI)

  * `router` = indigo · `product` = emerald · `compliance` = amber
  * `advisor` = violet · `market` = cyan · autres = slate

Helper `agentColor(agent_id)` exporté depuis
`AssistanceToolCallDetailDrawer.tsx`.

### Cas d'usage prioritaires

  1. **Debug une hallucination** : ouvre la conv, repère le turn fautif,
     drill-down dans le tool call qui a produit le contexte → on voit
     immédiatement quel slug a été retourné par `select_wiki_pages` ou
     `read_product_knowledge`.
  2. **Audit du routing** : à chaque turn user, le tool call `route_to`
     est visible avec son `reasoning_summary` et l'agent retenu.
  3. **Suivi des erreurs runtime** : la liste affiche `tool_error_count`
     par conversation ; click sur le drawer du tool en erreur → on voit
     `error_code` (`wrong_repo`, `not_found`, `timeout`, etc.) et les
     `arguments` qui ont déclenché.
  4. **Monitoring de la mémoire** : le footer montre le `summary`
     (consolidation tous les 10+ turns) et les `facts` (préférences
     persistantes), permettant de vérifier que la mémoire long terme
     capture bien les préférences client.

## 8.7 Router v2 — Qualité de la demande en 3 niveaux (v3.1 — 2026-05-04)

> **Doc dédiée complète :** voir `ORCHESTRATOR.md` (architecture
> détaillée, prompts complets, catalogues, FAQ debug, annexes).
> Cette section est un résumé.

### 8.7.1 Spec produit

Le router v1 demandait au LLM de choisir un agent + d'éventuellement
inventer le QCM de clarification ou le QCM de redirection. En v2,
on renforce ce contrat avec **3 niveaux de qualité de la demande**
formellement encadrés :

| Niveau | Description | Tool router | Comportement runtime |
|---|---|---|---|
| **3 — Hors-sujet complet** | Météo, sport, blagues, recettes… | `redirect_off_topic(bridge)` | **Liste FIXE de 5 portes d'entrée** + slot dynamique `Reprendre <topic>` si conversation engagée |
| **2 — Univers Vancelian flou** | Argent, épargne, performance, retraite… formulé large | `ask_clarification(tag?, prompt?, options?)` | Hybride : si `tag` reconnu → **catalogue canonique** ; sinon → LLM rédige (legacy) |
| **1.B — Sujet clair, demande nette** | « parle moi des bundle », « cours BTC » | `route_to(agent_id, confidence)` | Agent expert direct (pattern v1) |
| **1.A — Sujet clair, demande mixte** | « bundle pour ma retraite vu les taux » | `route_to(advisor)` | **Pattern advisor-first** : advisor consulte product / market via `consult_specialist` puis synthétise |

### 8.7.2 Modules code-as-config nouveaux

```
services/assistance/agents/
  router_off_topic_options.py        ← Lot 1 — liste fixe + slot resume
  router_intent_tags.py              ← Lot 2a — 4 familles + keyword matcher FR+EN
  router_clarification_catalog.py    ← Lot 3 — 27 entrées canoniques par tag
```

**Familles de tags (Lot 2)** :

  * `epargne` — épargner, sécuriser_capital, livret_coffre, rendement, avenir_securite
  * `investir` — investir, performance, retraite, bundle_crypto, exclusive_offer, instrument_cote, immobilier_long_terme
  * `compte_ops` — compte_kyc, depot, retrait, virement_sepa, carte_visa, banque
  * `marches_analyses` — actu_marche, opinion_marche, cours_evolution, macro_inflation, trading, volatilite
  * `transverse` — reussir, projet_vie, decouvrir, argent_general
  * `hors_sujet` — meteo, sport, cuisine, blague (→ redirect)

### 8.7.3 Pré-classification keyword (Lot 2)

À chaque tour, **avant** l'appel LLM router, un keyword-matcher
déterministe FR+EN annote le user message :

```
[INTENT TAGS] primary_tag = bundle_crypto | family = investir | scope_level = 2 | preferred_agent = product
```

Ce bloc est injecté dans le prompt système comme **signal**, pas
comme décision. Le LLM peut surclasser. La classification est
attachée à `RouterDecision.intent_classification` et persistée dans
`assistance_agent_decisions` (visible dans la **vue admin 3 colonnes**
v3.0 — colonne workflow trace).

### 8.7.4 Liste FIXE off-topic (Lot 1)

5 portes d'entrée stables (versionnées git) ne dépendant plus du
LLM, plus 1 slot dynamique :

```python
OFF_TOPIC_FIXED_OPTIONS = [
    {"id": "compliance", "label": "Mon compte et mes opérations"},
    {"id": "product",    "label": "Découvrir un produit Vancelian"},
    {"id": "advisor",    "label": "Conseils pour mes placements"},
    {"id": "market",     "label": "Comprendre les marchés en ce moment"},
    {"id": "advisor",    "label": "Préparer un projet financier"},
]
# + en 1ère position si memory_state["current_topic"] non-vide:
# {"id": "resume_topic", "label": f"Reprendre {topic_label}"}
```

Le LLM rédige toujours librement le **bridge** (texte chaleureux
contextualisé), mais ne contrôle plus les options.

### 8.7.5 Catalogue de clarifications hybride (Lot 3)

27 entrées canoniques avec `prompt + 3-5 options` calibrées
éditorialement, indexées par tag d'intention. Exemple :

```python
"epargner": {
    "prompt": "L'épargne, c'est exactement le cœur de Vancelian. "
              "Tu veux qu'on creuse quoi ?",
    "options": [
        ("product", "Voir les Coffres d'épargne (Flexible / Avenir)"),
        ("advisor", "Combien je peux mettre de côté chaque mois"),
        ("advisor", "Une stratégie d'épargne adaptée à mon profil"),
    ],
}
```

**Trigger LLM** : tool `ask_clarification(tag="epargner", ...)` —
le runtime substitue prompt + options par le canonique. Si `tag`
absent ou inconnu → fallback comportement v1.

### 8.7.6 Pattern advisor-first (Lot 4)

Quand la demande mixe **2+ dimensions** parmi `produits`,
`marchés/macro`, `objectifs personnels`, `comparaison` ET contient
un possessif personnel (« mon », « ma », « adapté à mon profil ») :

  → **`route_to(advisor)`** systématique (pas de QCM, pas de fan-out).

L'advisor reçoit `consult_specialist` dans son toolset et
**orchestre** product et market via consultation, puis synthétise
en un seul message client. Évite :
  * la frustration « quel angle veux-tu ? » alors que le client a
    déjà donné son objectif personnel ;
  * la complexité d'un fan-out runtime parallèle.

### 8.7.7 Persistance et observabilité

À chaque tour :

  1. La `RouterDecision` est persistée dans `assistance_agent_decisions`
     (`tool_name="router_classify"`, `agent_id="router"`,
     `autonomy_level="L0"`).
  2. `arguments_json` contient :
     ```json
     {
       "decision_kind": "route_to" | "ask_clarification" | "redirect_off_topic",
       "agent_id": "product",
       "confidence": 0.85,
       "intent_classification": {
         "primary_tag": "bundle_crypto",
         "family": "investir",
         "scope_level": 2,
         "preferred_agent": "product",
         "tags": ["bundle_crypto", "performance"]
       }
     }
     ```
  3. Visible immédiatement dans la **vue admin 3 colonnes** (colonne
     workflow trace, expand de la décision router pour ce turn).

### 8.7.8 Tests

  * `test_assistance_router_off_topic_options_unit.py` — 14 tests Lot 1
  * `test_assistance_router_intent_tags_unit.py` — 24 tests Lot 2a
  * `test_assistance_router_clarification_catalog_unit.py` — 60 tests Lot 3
  * `test_assistance_router_v2_integration_unit.py` — 9 tests intégration parsers
  * `test_assistance_router_v2_classify_unit.py` — 7 tests classify e2e (mock LLM)
  * **+ adaptation des 5 tests `TestRouterRedirectOffTopic` pour le contrat v2**

Total : **117 tests router v2** + non-régression `1199 tests assistance` ✓.

---

## 9. Limitations connues V1

| Limitation | Impact | Plan |
|---|---|---|
| Chaînage multi-agents borné à `MAX_CHAIN_DEPTH=1` et `MAX_CONSULTATIONS_PER_TOUR=3` | Pas de cascade `A → B → C` ; suffisant pour V1 (compliance + product) | Étendre à 2 si besoin métier après prod-data ; sinon Phase 7+ orchestrateur multi-step |
| Pas de RAG sur Product (couverture limitée à 10 slugs SQL) | Réponses produits limitées aux fiches seedées | Phase 5 — RAG pgvector + ingestion fiches PDF/MD |
| Pas de news live | Market V1 = stubs | Phase 6 |
| Mémoire long-terme non-écrite par les agents | Aucun apprentissage push | Phase 8+ : ADR à venir |
| QCM mono-niveau (pas de QCM en cascade) | Ambiguïté multi-niveau pas couverte | V2 si besoin |
| `consult_specialist.purpose` enum fermée (5 entrées) | Toute nouvelle question cross-agent doit passer par un PR ajout au catalog | Voir checklist d'extension dans `COMPLIANCE_TOPICS.md` §12.5 |

---

## 10. Références

### Documents internes — ordre de lecture conseillé pour Phase 2a

1. **`AUDIT_AUTH_IDENTITIES.md`** — vérité absolue sur le modèle
   d'identité Vancelian (`client_id` UUID = pivot, `user_id` Int =
   dérivé, `classify_actor()`, gotchas connus, 5 règles
   non-négociables). **À lire en premier** avant toute Phase V2.
2. **`MULTI_AGENTS_RUNTIME.md`** — spec du runtime agentique :
   function calling itératif, autonomy levels L0/L1/L2/L3, table
   `agent_decisions`, sécurité matérielle tipping-off, pattern adapter
   external providers, pseudocode complet du loop. **Source de vérité
   technique pour le code Phase 2a.**
3. **`COMPLIANCE_TOPICS.md`** (v1.0) — spec d'implémentation Phase 2b
   du *tree system* compliance : sub-agents, dispatcher
   `diagnose_compliance_topic`, action CTAs avec deep-links,
   anti-tipping-off, whitelist sécurité. **Source de vérité Phase 2b.**
4. **`MULTI_AGENTS_DATA_SOURCES.md`** (v2.0+) — cartographie des
   tables Vancelian + tools introspectifs + roadmap par agent. **À
   consulter avant chaque livraison V2** (et à mettre à jour avec une
   nouvelle ligne de version).
5. **`MEMORY.md`** — mémoire long-terme cross-conversations,
   **fondation conservée** intacte par Phase 2a / 2b.
6. **`COGNITIVE_BOT.md`** (v4 — 2026-05-04) — couche cognitive
   transverse au-dessus des agents : State Engine, Objective Engine,
   Response Framework 4-temps, agent `trust`, funnel admin. **Source
   de vérité Cognitive Bot v4.**

### Références externes

- OpenAI function calling : https://platform.openai.com/docs/guides/function-calling
- Anthropic / OpenAI patterns d'agents : référence interne `docs/research/agent-patterns.md` (à créer)

---

**Note d'historique :** ce doc est la version **2.9** (Cognitive Bot v4
Lots 1-6 livrés le 2026-05-04). Toute modif structurelle (nouvel agent,
changement de modèle de routing, etc.) doit faire l'objet d'un ADR daté
ajouté en bas de fichier.

| Version | Date | Phase | Changements majeurs |
|---|---|---|---|
| 1.0 | 2026-04-?? | Phase 0 | Design figé, 9 ancres architecturales, 5 agents stubs |
| 2.0 | 2026-05-?? | Phase 2a | Runtime function calling, autonomy L0, 5 tools compliance, audit `assistance_agent_decisions`, identity short-circuits |
| 2.1 | 2026-05-02 | Pré-2b | Référence à `COMPLIANCE_TOPICS.md` (spec v0.9) |
| 2.2 | 2026-05-03 | Phase 2b livrée | Compliance tree system : sub-agents `compliance.{registration,remediation,transactional,general}`, `diagnose_compliance_topic`, `action_cta_catalog` whitelist deep-links, SSE `thinking`, `AssistanceChoiceOption.deep_link`, Flutter resolver. 140 tests verts. |
| **2.3** | **2026-05-03** | **Phase 2c livrée** | **Orchestration multi-agents : tools `handoff_to_agent` (remediation → transactional / general) et `consult_specialist` (compliance → product) ; `tour_shared_context` avec whitelist explicite `_SAFE_KEYS_PER_TOOL` ; vrai agent `product` (prompt + table SQL `product_knowledge` seedée 10 entrées via migration 149) ; runtime extensions `MAX_CHAIN_DEPTH=1`, `MAX_CONSULTATIONS_PER_TOUR=3`, audit `agent_chain` + `consultations` dans `message_payload.metadata`. 530 tests verts (zéro régression).** |
| **2.4** | **2026-05-04** | **Phase 2 wiki branchée** | **Wiki markdown 243 fiches importé en Phase 1 (vault Obsidian source) et branché au runtime de l'agent `product` via 2 nouveaux tools L0 (`select_wiki_pages` + `read_wiki_page`) — pattern Karpathy keyword (pas de vector DB, pas d'appel LLM dans le retrieval). Repo `wiki_repo.py` avec parseur frontmatter maison + cache TTL 5 min. Prompt `product_system.md` v2 enrichi de la spec Jean Guillou (vocabulary 7 termes critiques, grounding_rule, account_limitation, response_rules, mandatory_disclaimers, escalation_triggers, forbidden_patterns, self_check, 4 examples). Cohabitation SQL/MD : SQL pour les fiches courtes canoniques (délais, définitions), MD pour la couverture large (FAQ, exclusive offers, crypto, account, transfers, …). 46 tests wiki + 679 tests assistance globaux verts. Aucune modif env/DB/Docker, aucune nouvelle dépendance Python.** |
| **2.5** | **2026-05-04** | **Guard-rail product + mémoire affinée** | **Suite à l'analyse post-prod de la conv `aef5923a` (42 turns) qui a révélé que `gpt-4o-mini` zappe parfois les tools de lecture sur l'agent `product` (3 turns sur 8 hallucinent). **Guard-rail runtime** ajouté dans `agent_loop.py` : si l'agent `product` termine un turn sans `read_product_knowledge`/`read_wiki_page`/`show_instrument_card`, ou avec `select_wiki_pages` sans read derrière, on injecte un hint system et on rejoue **une fois**. Désactivable via `ASSISTANCE_PRODUCT_GUARDRAIL_ENABLED=false`. Cf. `PRODUCT_AGENT.md` §9.3 pour les détails. **Mémoire long-terme retunée** : seuil tokens `6000 → 2500` + nouveau déclencheur `ASSISTANCE_SUMMARY_MIN_TURNS=10` qui consolide à `≥ 20 messages` indépendamment du seuil tokens, garantissant que les conversations longues mais peu verbeuses alimentent enfin la mémoire long-terme client. Cf. `MEMORY.md` §5.2. **852 tests assistance verts (vs 679 avant) → zéro régression.** Aucune modif env/DB/Docker, aucune nouvelle dépendance.** |
| **2.6** | **2026-05-04** | **Router 3-niveaux explicite + vocabulaire produit Vancelian** | **Constat post-prod (conv `fbbf4f13`) : « parle moi des bundle » → router renvoie un QCM `ask_clarification` au lieu de `route_to(product)` direct, parce que le LLM ne connaît pas le synonyme oral « bundle » = « Crypto Basket » dans le vocabulaire Vancelian propriétaire. **Prompt router enrichi** : (a) section explicite « **Les 3 niveaux d'orchestration** » en tête (Niveau 1 = `route_to`, Niveau 2 = `ask_clarification`, Niveau 3 = `redirect_off_topic`) avec règle anti-confusion ; (b) **règle 0bis** « PRIORITÉ ABSOLUE — produit Vancelian propriétaire nommé » avec dictionnaire des termes (Vault/Coffre, Basket/Bundle, Exclusive Offer, Cloud Mining, Dubai/Bali Villa, Privilege Club, Vancelian Card) + synonymes oraux ; (c) 4 nouveaux exemples calibrés (`parle moi des bundle`, `comment fonctionne le coffre flexible`, `c'est quoi le Privilege Club`, `Cloud Mining ça marche comment`) ; (d) garde anti-confusion product/compliance pour les questions opérationnelles (« mon coffre n'est pas crédité » → compliance, pas product). **21 nouveaux tests prompt** (`TestRouterPromptVocabulary` + `TestRouterPromptIntegrity`) qui assertent le contenu du fichier `router_system.md`. **873 tests assistance verts → zéro régression.** Aucune modif code Python, env, DB, Docker — uniquement le fichier prompt MD.** |
| **2.11** | **2026-05-05** | **Cognitive Bot v4 — Lot 7 V1.1 (Auto-QCM SSE branché end-to-end + Flutter)** | **Suite directe du Lot 7 (v2.10) : la fonction `auto_qcm_from_listing` livrée mais non branchée est désormais **invoquée automatiquement** dans `service.stream_assistant_turn` après la boucle async. **Backend (5 points)** : (A) **Hook** dans `service.py` après `runtime_choices` et avant `_persist_assistant_message` ; (B) **Persistance** : `message_payload.auto_qcm = {prompt, options, source: "auto_promoted", truncated}` (compat totale, `message_type` reste `text` → un client legacy lit juste le markdown) ; (C) **SSE** : `done` event enrichi avec la clé `auto_qcm` (atomique avec le commit DB, pas d'event mid-stream → 0 race condition) ; (E) **Module orchestrateur `decide_auto_qcm`** centralisant TOUS les garde-fous : whitelist agents + anti-double-QCM (si `ask_user_question` déjà émis) + **anti-redondance embeds CTA** (`crypto_bundles_card`, `bundle_detail_card`, `instrument_detail_card`, `transaction_detail`) + lecture **objective-aware** (`stop_pushing=True` → skip ; `next_best_action ∈ {give_proof, give_control, micro_step, call_to_action}` → skip — cohérence avec `_response_framework.md` qui interdit de transformer un tour de réassurance en menu commercial) + seuil minimum durci à **3 items** (`QCM_AUTO_PROMOTE_MIN_ITEMS` ; un listing 2 items est plus du parallélisme rhétorique qu'un menu de choix) + kill-switch `ASSISTANCE_AUTO_QCM_ENABLED=false` ; (F) **Tests SSE end-to-end** : nouveau fichier `test_assistance_auto_qcm_sse_unit.py` couvrant cas nominal, double-QCM, embed CTA, stop_pushing, 4 next_best_action interdits, 2 next_best_action permis, kill-switch, listing trop court (14 cas). **Flutter** : (D) `AssistanceAutoQcmPayload` (parsing JSON cap 7 hard cap, source par défaut `auto_promoted`) ; `AssistanceHistoryMessage.autoQcmPayload` lu depuis `message_payload.auto_qcm` au reload `/messages` (rétro-compat : un message legacy sans la clé n'a pas de footer) ; `AssistanceTurnEvent.doneAutoQcm` getter pour SSE live ; nouveau widget `AutoQcmFooter` rendu **sous** la bulle texte (distinct de `_buildChoicesBubble` qui REMPLACE — ici on COMPLÈTE) avec style outlined discret + mode consommé après tap (anti double-tap + lecture historique limpide) ; `_handleAutoQcmTapped` envoie un nouveau tour avec `text=option.label` + `agent_hint=option.agentHint` (réutilise `_sendMessageWithText` de la mécanique QCM existante) ; garde côté client `_embedsBlockAutoQcmFooter` (défense en profondeur si embed CTA built-in arrive). **Tests** : +14 unit (`decide_auto_qcm` — 11 cas de skip / 3 cas de promote), +14 SSE end-to-end, +2 ajustements existants (seuil min 3), +15 Flutter (`auto_qcm_test.dart` — parsing JSON `AssistanceAutoQcmPayload` + `AssistanceHistoryMessage.auto_qcm` + `AssistanceTurnEvent.doneAutoQcm` + widget `AutoQcmFooter` rendu/tap/consumed/empty). **1472 tests assistance verts** vs 1442 avant V1.1 → zéro régression. `flutter analyze` clean sur les 3 fichiers V1.1. **Admin Next.js — 4ᵉ colonne « Synthèse cognitive »** (`web/src/components/admin/CognitiveTurnDiagram.tsx` + redistribution `grid-cols-12` → `3+4+3+2`) : diagramme vertical 5 sections (Input · Analyse cognitive intention user · Objectif réponse bot · Décision router · Chaîne d'agents) lue depuis `assistance_agent_decisions.arguments_json` du `tool_name='router_classify'` (cognitive_state + objective + decision_kind + reasoning_summary) et `messages[].message_payload.metadata.{agent_chain, consultations}`. Best-effort (sections vides masquées). Quand on clique sur un turn USER, le diagramme suit automatiquement le turn ASSISTANT correspondant (qui porte la décision router) sans bouger la sélection timeline. Aucune modif backend (réutilise l'endpoint `/api/admin/assistance/conversations/{id}/decisions` existant). **Charte `arquantix-environment-stability` respectée** : aucune migration DB (utilise `message_payload` JSONB existant), aucun changement `.env`/Docker/services, kill-switch présent, best-effort `try/except` sur le hook (un bug auto-QCM ne casse jamais le tour). Cf. [`CLIENT_DISCOVERY.md`](./CLIENT_DISCOVERY.md) §§ 4.4–4.6 (orchestrateur + branchement runtime + côté Flutter) et [`COGNITIVE_BOT.md`](./COGNITIVE_BOT.md) §11 (Lot 7 V1.1 livré).** |
| **2.10** | **2026-05-04** | **Cognitive Bot v4 — Lot 7 (Conversation Continuity Layer + multi-projet client)** | **Constat post-prod (conv `f9d59f98`) : 3 défauts conversationnels critiques — (1) bot lâche le contexte « achat maison » dès que le user demande « investissements » au tour suivant ; (2) tour user laconique « Les offres » répondu hors-contexte parce que le tour bot précédent listant 5 familles n'est pas pré-pendu ; (3) listes 5+ items texte sans QCM cliquable. **Solution architecturale en 3 modules** documentés dans la nouvelle doc dédiée [`CLIENT_DISCOVERY.md`](./CLIENT_DISCOVERY.md) : **(A) Migration 153** — 2 nouvelles tables additives : `assistance_client_discovery_projects` (FK `person_id`, status active/paused/completed/abandoned, paramètres JSONB `ClientProjectParameters` = horizon/target/initial/recurring/liquidity/risk, indexes partiels) et `assistance_floating_parameters` (FK conv+person, status pending_attribution/attributed/discarded). 100 % additive, pas de CHECK, downgrade clean. **(B) `client_discovery.py`** — extracteur keyword (~60 % coverage) + dataclasses + **règles d'attribution strictes anti-bug critique** : co-mention explicite OU question ciblée par le bot (regex `pour ton projet maison`) OU sinon → floating (jamais d'attribution par proximité temporelle, ce qui évite « 4 ans = vacances » alors que le user voulait « 4 ans pour la maison »). **(C) `client_discovery_repo.py`** — upsert avec **merge non destructif** des paramètres, cap 5 projets actifs/personne (paused au-delà), **lookup cross-conversation** (un projet peut traverser plusieurs conv pour la même personne), gestion lifecycle floating params. **(D) `conversation_continuity.py`** — 3 fonctions déterministes (pas de LLM) : `should_embed_previous_bot_turn` (laconique sans token standalone Vancelian/instrument/projet → pré-pend tour bot précédent dans le contexte LLM), `extract_assistant_listing` (parser numéroté + bullet ≥ 2 + détection question via `?` ou pattern `lequel/laquelle/parmi/...`), `auto_qcm_from_listing` (cap **7 hard / 5 soft** via Miller's law + UI mobile, whitelist agents `default/advisor/product/market/trust`). **(E) Hooks runtime** dans `service.start_chat_turn` (extraction + persist + render bloc `[CLIENT DISCOVERY]` + préparation `previous_bot_context_block`, tout en best-effort `try/except`), `router._build_router_messages` (injection bloc), `agent_loop._build_initial_messages` (injection bloc + substitution user message si laconique). **(F) Framework UX révisé** (`_response_framework.md`) : ancien `recommend → 1 ou 2 options MAX` devient `recommend → 2 ou 3 options MAX` ; nouveau bucket **`structural_choice`** pour listes structurantes cap 7/5 + question fermée OBLIGATOIRE + `ask_user_question` FORTEMENT RECOMMANDÉ ; ancien interdit « 5+ paralyse » remplacé par « 8+ paralyse, regroupe en 5-7 catégories » ; nouvel interdit « ignorer `[CLIENT DISCOVERY]` ». **Tests** : 33 (`test_assistance_client_discovery_unit.py`) + 9 (`test_assistance_client_discovery_repo_unit.py`) + 30 (`test_assistance_conversation_continuity_unit.py`) = **72 tests dédiés Lot 7** ; **1442 tests assistance verts** vs 1370 avant Lot 7 → zéro régression. **2 kill-switches env** (`ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED`, `ASSISTANCE_AUTO_QCM_ENABLED` defaults `true`). **Charte `arquantix-environment-stability` respectée** : migration explicitement validée (« go explicit »), additive, pas de CHECK, pas de NOT NULL hors FK/timestamps, pas de modif des tables existantes ; aucun changement `.env`/`COMPOSE_PROJECT_NAME`/`DB_NAME`/ports/volumes/services Docker ; tout I/O DB en best-effort (un bug discovery ne casse jamais un tour). Cf. [`COGNITIVE_BOT.md`](./COGNITIVE_BOT.md) §11 (Lot 7 livré) et `CLIENT_DISCOVERY.md` (doc dédiée).** |
| **2.9** | **2026-05-04** | **Cognitive Bot v4 — Lot 6 (UI admin + colonnes natives)** | **(1) Migration Alembic **152** ajoute 6 colonnes nullable sur `assistance_agent_decisions` (`emotional_intent`, `conversation_stage`, `knowledge_level`, `trust_level`, `primary_goal`, `next_best_action`) + 2 index partiels (`ix_aad_cognitive_stage_created`, `ix_aad_emotional_intent_created`), 100 % additive, backfill SQL non destructif depuis `arguments_json`, downgrade clean. (2) **Double-write** dans `service._persist_router_decision` via le nouveau kwarg `extra_columns` de `audit.persist_decision` — JSONB reste source de vérité, colonnes natives accélèrent funnel & exposent les données aux outils tiers (Metabase / Retool). (3) `admin_cognitive_router._aggregate_dimension` lit la colonne native en priorité avec fallback JSONB via `COALESCE` (rétro-compat décisions résiduelles). (4) **Page React admin** `/admin/assistance/cognitive-funnel` (Next.js — `assistance-cognitive-proxy.ts` + route proxy `/api/admin/assistance/cognitive/funnel`) : period selector 7/14/30/90 j, cards distribution par dimension avec `Progress` + `Badge` sémantique (rouge = FEAR/ANGER/COMPLIANCE_BLOCKED, vert = CURIOSITY/OPPORTUNITY), card `trust_level` avg/min/max + sample size. **+7 tests dédiés** (`test_assistance_cognitive_columns_unit.py` — `extra_columns` ORM, double-write, lecture priorisée colonne/JSONB, fallback `unknown`, `_trust_level_stats` mixte) ; **1370 tests assistance verts** vs 1363 (zéro régression). Charte `arquantix-environment-stability` respectée : migration nullable, sans CHECK, sans NOT NULL, sans modif de l'existant ; aucun changement `.env`/`COMPOSE_PROJECT_NAME`/`DB_NAME`/ports/volumes. Cf. `COGNITIVE_BOT.md` §§ 9 (persistance) et 11 (Lot 6 livré).** |
| **2.8** | **2026-05-04** | **Cognitive Bot v4 (Lots 1-5) — voir [`COGNITIVE_BOT.md`](COGNITIVE_BOT.md)** | **Le bot passe de "répond" à "drive". À chaque tour : (1) **State Engine** `cognitive_state.py` calcule `{emotional_intent ∈ {FEAR_RISK, CURIOSITY, COMPLIANCE_BLOCKED, TRANSACTION, ANGER, OPPORTUNITY, NEUTRAL}, conversation_stage ∈ {discovery, clarification, recommendation, conversion}, trust_level ∈ [0,1], knowledge_level}` 2 fois par tour (préliminaire avant routage, final après) ; (2) **Objective Engine** `conversation_objective.py` mappe l'état → `{primary_goal ∈ {reassure, de_escalate, unblock, inform, educate, convert}, next_best_action ∈ {give_proof, give_control, micro_step, ask_question, recommend, call_to_action}, stop_pushing}` via tables `DEFAULT_BY_EMOTION` + `OVERRIDE_BY_EMOTION_STAGE` ; (3) **Response Framework** `_response_framework.md` auto-concaténé (whitelist `default/advisor/product/market/trust/compliance.*`) impose 4 temps : ACK émotionnel → reformulation → apport de valeur → next best action ; (4) **Trust hybride** — nouvel agent `trust` racine routable (règle 4.5 du router) + consultable via `consult_specialist(target="trust", purpose="reassure_about_{regulation,custody,security}")` + wiki seed `faq/trust-security/` (régulation, custody) + system prompt factuel/non commercial ; (5) **Funnel cognitif** — endpoint admin `GET /api/admin/assistance/cognitive/funnel?period_days=N` (auth admin/ops) qui agrège `assistance_agent_decisions.arguments_json` par stage / emotional_intent / primary_goal / next_best_action / agent + stats `trust_level` (avg/min/max), CLI local `scripts/cognitive_funnel.py --json`. **Persistance JSONB only** — pas de migration Alembic, le `cognitive_state` et l'`objective` sont stockés dans `arguments_json` du tool `router_classify`. **1363 tests assistance passent (vs 1322 avant)** — +41 tests dédiés (cognitive_state + objective + framework + 20 trust + 16 funnel) ; aucune régression. **Aucune modif env/Docker/DB** — runtime seul, charte `arquantix-environment-stability` respectée.** |
| **2.7** | **2026-05-04** | **Slider Crypto Bundles + router QCM contextualisé + advisor profil + refonte `instrument_detail_card`** | **Constat post-prod (conv `e5133711` + UX feedback design) : (1) « Découvrir les bundles disponibles » → l'agent `product` répond uniquement par du texte markdown (pas de visuel concret du catalogue Vancelian) ; (2) « quel bundle est le plus adapté à mon profil ? » → router émet un QCM avec 4 labels génériques qui ne mentionnent même pas « bundle » + bascule en clarification au lieu d'advisor direct ; (3) la carte `instrument_detail_card` du chat ne reprenait pas la partie haute de la page détail (mini-sparkline avec area au lieu d'un line chart pur, pas de tag « Crypto », mauvais avatar, chart pas bord-à-bord). **Solutions livrées (4 lots indépendants)** : **Lot 1 (router prompt-only — `router_system.md`)** : nouveau sous-cas règle 2 « profil sur produit Vancelian propriétaire nommé » (`route_to(advisor)` direct ≥ 0.8 — la règle 2 prime sur la 0bis) + règle de contextualisation `ask_clarification` (chaque label DOIT explicitement reprendre le sujet `recent_turns`) + 3 exemples calibrés (« le plus adapté à mon profil », « me convient le mieux », « lequel je devrais choisir »). **Lot 2 (tool backend `show_crypto_bundles`)** : nouveau tool L0 `show_crypto_bundles()` (sans paramètre, idempotent) qui consomme `CatalogService.get_public_catalog(product_type='crypto_bundle')` (réutilisé tel quel — 0 modif `portfolio_engine`) et émet un embed `crypto_bundles_card` avec bundles + allocations + 2 deep-links whitelistés dans `action_cta_catalog` (`view_bundle_detail` → `vancelian://app/bundle/{id}`, `invest_bundle` → `vancelian://app/bundle/{id}/invest`). Inscrit dans `PRODUCT_KNOWLEDGE_READ_TOOLS` (compatible guard-rail product). Documenté dans `product_system.md`. **Lot 3 (Flutter `crypto_bundles_card`)** : nouvel embed `CryptoBundlesCardEmbed` qui délègue le rendu à `AssetsBundlesModule` (réplique visuelle exacte du widget `CryptoBundlesWidget` markets/home — cohérence design garantie). Resolver `vancelian://app/bundle/{id}[/invest]` ajouté avec enrichissement `portfolioId` via `getBundleCatalog` pour le flow d'investissement. **Lot 4 (Flutter `instrument_detail_card` — refonte design)** : `InstrumentDetailCardEmbed` réécrit en `StatefulWidget` qui charge les vraies bougies via `MarketDataApi.getChartHistory` et délègue intégralement au `ChartAssetModule(instrumentDetailStyle: true)` du hero détail instrument — réplique visuelle stricte (line chart pur, ligne horizontale + puce de prix de départ, sonar point, puces de période 1j/1s/1m/1a/5a, disclaimer mid-rate, tag « Crypto » via `CategoryBadge`, `CryptoAvatar(size: small)`, perf row + CTAs Acheter/Vendre sous le chart via `InstrumentDetailHeroCtaRow`). `ChartAssetModule` étendu d'une prop optionnelle rétrocompatible `chartContainerWidth` pour fonctionner dans une bulle chat plus étroite que l'écran. Différence assumée : encapsulé dans un module blanc bulle assistant + chart bord-à-bord du module (pas de l'écran). **Tests** : 30 nouveaux (`test_assistance_show_crypto_bundles_unit.py`) + 6 nouveaux (`TestRouterPromptProfileAdvisorAndContextualQcm`) + maj `test_assistance_wiki_tools_unit.py` (compteur 6 → 7 tools product). **909 tests assistance globaux verts → zéro régression**. `flutter analyze` clean sur les fichiers modifiés (0 nouveau warning). Aucune modif env/DB/Docker, 0 nouvelle dépendance Python, 0 nouvelle dépendance Flutter. Cf. `PRODUCT_AGENT.md` §§9.4-9.6 pour les détails. Lots 1+2 actifs immédiatement (restart container) ; Lots 3+4 actifs après build mobile.** |

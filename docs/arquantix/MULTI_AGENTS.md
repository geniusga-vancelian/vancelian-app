# Architecture multi-agents — Assistance Vancelian

> **Statut :** Phase 2 wiki + guard-rail product + router 3-niveaux
> (v2.6) — orchestration multi-agents + base de connaissance markdown
> 243 fiches + anti-hallucination runtime + vocabulaire produit
> Vancelian dans le router.
>
> **Dernière mise à jour :** 2026-05-04 (v2.6)
>
> **Code de référence :** `services/arquantix/api/services/assistance/agents/`
>
> **Documents liés :**
> - `COMPLIANCE_TOPICS.md` — spec Phase 2b + 2c (tree + orchestration)
> - `PRODUCT_AGENT.md` — spec Phase 2c (vrai agent product) **NEW**
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
│       ┌────────┬──────────┼──────────┬──────────┬────────┐          │
│       ▼        ▼          ▼          ▼          ▼        ▼          │
│   default  compliance  advisor   product    market    (futurs)      │
└─────────────────────────────────────────────────────────────────────┘
```

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

### Références externes

- OpenAI function calling : https://platform.openai.com/docs/guides/function-calling
- Anthropic / OpenAI patterns d'agents : référence interne `docs/research/agent-patterns.md` (à créer)

---

**Note d'historique :** ce doc est la version **2.3**. Toute modif
structurelle (nouvel agent, changement de modèle de routing, etc.) doit
faire l'objet d'un ADR daté ajouté en bas de fichier.

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

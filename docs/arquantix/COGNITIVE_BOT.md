# Cognitive Bot v4 — Architecture & runbook

> **TL;DR** — Le bot d'assistance Vancelian est passé d'un système qui
> *répond* (Phase 2c) à un système qui **drive** l'utilisateur vers une
> décision (Cognitive Bot v4, livré en 5 lots entre 2026-04-30 et
> 2026-05-04). À chaque tour, on calcule un **état cognitif** du client
> (intention émotionnelle, étape de conversation, niveau de confiance,
> niveau de connaissance), on en déduit un **objectif déterministe**
> (`primary_goal`, `next_best_action`, `stop_pushing`), puis on injecte
> les deux en *system prompt* aux agents experts qui répondent dans un
> **format en 4 temps** : ACK émotionnel → reformulation → apport de
> valeur → orientation.

---

## 0. Table des matières

* [1. Pourquoi Cognitive Bot v4](#1-pourquoi-cognitive-bot-v4)
* [2. Vue d'ensemble — les 3 couches](#2-vue-densemble--les-3-couches)
* [2.1 Couche orchestrateur (router + dimensions métier)](#21-couche-orchestrateur-router--dimensions-métier)
* [3. Lot 1 — State Engine (`cognitive_state.py`)](#3-lot-1--state-engine-cognitive_statepy)
* [4. Lot 2 — Objective Engine (`conversation_objective.py`)](#4-lot-2--objective-engine-conversation_objectivepy)
* [5. Lot 3 — Response Framework (`_response_framework.md`)](#5-lot-3--response-framework-_response_frameworkmd)
* [6. Lot 4 — Trust hybride (agent `trust`)](#6-lot-4--trust-hybride-agent-trust)
* [7. Lot 5 — Métriques & funnel cognitif](#7-lot-5--métriques--funnel-cognitif)
* [8. Flux complet d'un tour](#8-flux-complet-dun-tour)
* [9. Persistance & non-migration DB](#9-persistance--non-migration-db)
* [10. Tests & non-régression](#10-tests--non-régression)
* [11. Limitations & roadmap](#11-limitations--roadmap)
* [12. Références code](#12-références-code)

---

## 1. Pourquoi Cognitive Bot v4

Avant ce lot :

* L'orchestrator routait correctement vers l'agent expert.
* Chaque agent répondait correctement à sa spécialité.
* **Mais** : pas de direction globale conversationnelle. Le bot
  était *neutre*, *encyclopédique*, *plat*. Il ne faisait pas avancer
  l'utilisateur.

Cognitive Bot v4 introduit le triptyque :

> **identifier → orienter → faire avancer**

Concrètement, à chaque message client le runtime :

1. **identifie** son état émotionnel (`FEAR_RISK`, `CURIOSITY`,
   `COMPLIANCE_BLOCKED`, `TRANSACTION`, `ANGER`, `OPPORTUNITY`,
   `NEUTRAL`) et son étape (`discovery`, `clarification`,
   `recommendation`, `conversion`),
2. **oriente** la réponse via un objectif déterministe
   (`reassure`, `de_escalate`, `unblock`, `inform`, `educate`,
   `convert`) et une *next best action*
   (`give_proof`, `give_control`, `micro_step`, `ask_question`,
   `recommend`, `call_to_action`),
3. **fait avancer** : la réponse est strictement structurée en
   4 temps, et termine **toujours** sur une orientation explicite,
   sauf si `stop_pushing=True` (cas FEAR / ANGER intenses).

---

## 2. Vue d'ensemble — les 3 couches

```
┌─────────────────────────────────────────────────────────────────┐
│  Lot 1 — STATE ENGINE                                           │
│  cognitive_state.py                                             │
│    {emotional_intent, conversation_stage,                       │
│     trust_level, knowledge_level}                               │
├─────────────────────────────────────────────────────────────────┤
│  Lot 2 — OBJECTIVE ENGINE                                       │
│  conversation_objective.py                                      │
│    {primary_goal, next_best_action, stop_pushing,               │
│     strategy_hint}                                              │
├─────────────────────────────────────────────────────────────────┤
│  Lot 3 — RESPONSE FRAMEWORK                                     │
│  prompts/_response_framework.md (auto-concat)                   │
│    1) ACK émotionnel                                            │
│    2) Reformulation                                             │
│    3) Apport de valeur                                          │
│    4) Next best action                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Lot 4 — TRUST HYBRIDE                                          │
│    agent `trust` routable + consultable + transverse           │
├─────────────────────────────────────────────────────────────────┤
│  Lot 5 — MÉTRIQUES & FUNNEL                                     │
│    GET /api/admin/assistance/cognitive/funnel                  │
│    scripts/cognitive_funnel.py (CLI)                           │
└─────────────────────────────────────────────────────────────────┘
```

L'invariant clé : **rien de tout cela ne demande de migration DB**.
Tout est persisté dans la colonne JSONB
`assistance_agent_decisions.arguments_json` qui existait déjà.

### 2.1 Couche orchestrateur (router + dimensions métier)

Le routeur n'est pas qu'un *switch* `agent_id` : sur chaque `route_to`, il peut
remplir des **dimensions orchestrateur** (`business_intent`, `emotional_state`,
`urgency`, `regulatory_risk`, `data_need`, `secondary_intents`, drapeaux
`must_*`, `response_style`). Elles sont :

* **normalisées** dans `services/assistance/agents/orchestration_context.py` ;
* **stockées** dans `arguments_json.orchestration` (audit / admin) ;
* **injectées** dans le prompt des agents experts via
  `runtime/agent_loop._format_cognitive_blocks` (clé `memory_state["orchestration"]`
  posée par `service.start_chat_turn`).

Instructions LLM : `services/assistance/prompts/router_system.md` — section
**[ORCHESTRATION]**.

---

## 3. Lot 1 — State Engine (`cognitive_state.py`)

**Module** : `services/assistance/agents/cognitive_state.py`.

### 3.1 Dataclass `CognitiveState`

```python
@dataclass(frozen=True)
class CognitiveState:
    emotional_intent: EmotionalIntent          # FEAR_RISK | CURIOSITY | …
    conversation_stage: ConversationStage      # discovery | … | conversion
    trust_level: float                         # 0.0 .. 1.0
    knowledge_level: KnowledgeLevel            # low | medium | high
    raw_signals: dict                          # debug uniquement
```

### 3.2 Calcul

`compute_cognitive_state(...)` est appelé **2 fois par tour** :

1. **Préliminaire** — *avant* le routage. Donne au router un signal
   sur l'émotion détectée (heuristique keywords + contexte).
2. **Final** — *après* le routage, pour pouvoir intégrer le
   `decision_kind` (un `ask_clarification` met en `clarification`,
   un `redirect_off_topic` reset le stage, …).

Sources d'information utilisées :

* Le **message courant** (keywords + ponctuation).
* Le **state précédent** (`_safe_load_previous_cognitive_state`)
  pour la **continuité** (notamment `trust_level` qui s'érode ou
  regagne tour par tour).
* La **mémoire long-terme client** (`assistance_long_memory`) pour
  estimer le `knowledge_level`.
* Le **résultat du router** (`decision_kind`) pour ajuster le
  `conversation_stage`.

### 3.3 Mapping intentions → stratégies (encodé en `conversation_objective.py`)

| Intention émotionnelle | Stratégie typique |
|---|---|
| `FEAR_RISK` | rassurer, restaurer la confiance, donner des preuves, **éviter le push** |
| `CURIOSITY` | simplifier, projection, 1-2 options max |
| `COMPLIANCE_BLOCKED` | dé-frictionner, rappeler le bénéfice, micro-steps |
| `TRANSACTION` (monitoring) | confirmer, contextualiser, *éventuellement* upsell |
| `ANGER` | dé-escalader, donner le contrôle, **pas** de justification longue |
| `OPPORTUNITY` | confirmer la pertinence, projeter, recommander |
| `NEUTRAL` | parcours standard |

### 3.4 Injection en system prompt

Le bloc `[COGNITIVE STATE]` est inséré dans le prompt :

* du **router** (`router._build_router_messages`) — pour qu'il sache
  s'il a affaire à un client en peur (et préfère router vers `trust`),
* des **agents experts** (`runtime/agent_loop._build_initial_messages`)
  — pour qu'ils adaptent leur ton.

---

## 4. Lot 2 — Objective Engine (`conversation_objective.py`)

**Module** : `services/assistance/agents/conversation_objective.py`.

### 4.1 Dataclass `ConversationObjective`

```python
@dataclass(frozen=True)
class ConversationObjective:
    primary_goal: PrimaryGoal           # reassure | de_escalate | unblock | inform | educate | convert
    next_best_action: NextBestAction    # give_proof | give_control | micro_step | ask_question | recommend | call_to_action
    stop_pushing: bool                  # True quand l'objectif est de calmer, pas de pousser
    strategy_hint: str                  # phrase courte pour l'agent
```

### 4.2 Mapping déterministe

* `DEFAULT_BY_EMOTION` : pour chaque `EmotionalIntent`, la stratégie
  par défaut (ex. `FEAR_RISK → reassure / give_proof / stop_pushing=True`).
* `OVERRIDE_BY_EMOTION_STAGE` : ajustements quand on connaît aussi
  le `conversation_stage` (ex. `CURIOSITY × discovery` → `educate`,
  `CURIOSITY × recommendation` → `convert / call_to_action`).

`compute_objective(cognitive_state)` retourne l'objectif final.

### 4.3 Injection

Le bloc `[OBJECTIVE]` est inséré dans le system prompt des agents
experts à côté de `[COGNITIVE STATE]` (cf. § 5).

---

## 5. Lot 3 — Response Framework (`_response_framework.md`)

**Fichier** : `services/assistance/prompts/_response_framework.md`.

### 5.1 Structure imposée

Toute réponse d'un agent expert **doit** suivre 4 temps :

1. **Validation émotionnelle** — *« Je comprends », « Bonne question »,
   « C'est normal de se poser ça »*. Calibrée à l'émotion détectée.
2. **Reformulation intelligente** — preuve qu'on a compris la
   question.
3. **Apport de valeur** — la réponse claire au sujet posé. C'est ici
   qu'on cite le wiki, le catalogue, les règles métier.
4. **Orientation / Next Best Action** — sauf `stop_pushing=True`,
   on termine **toujours** par une question intelligente, une
   suggestion, ou un CTA aligné sur le `next_best_action` calculé.

### 5.2 Auto-concaténation (whitelist d'agents)

`prompt_builder.RESPONSE_FRAMEWORK_AGENTS` liste les agents qui
reçoivent le fragment :

```
default · advisor · product · market · trust ·
compliance.registration · compliance.transactional ·
compliance.general · compliance.remediation
```

**Exclus** :

* `router` — function-calling pur, pas de Markdown client.
* `compliance` (top-level) — simple dispatcher.
* `summarizer` — extraction JSON, pas de réponse client.

`load_agent_system_prompt(agent_id)` charge le prompt agent puis
concatène automatiquement `_response_framework.md` si l'agent est
dans la whitelist. Le fragment est **caché en module-level** pour
éviter N relectures disque par tour.

---

## 6. Lot 4 — Trust hybride (agent `trust`)

### 6.1 Pourquoi un agent dédié

Vancelian opère sur du RWA / crypto — domaine où la **peur
fondamentale** (régulation, custody, hack, faillite) est le
premier blocage commercial. Un agent spécialiste *factuel et calme*
qui sait répondre à ces questions, et qui peut être consulté par les
autres agents, est un différenciateur clé.

### 6.2 Pattern hybride (A + B + C)

| Mode | Activation | Cas d'usage |
|---|---|---|
| **(A) Agent racine routable** | `route_to(trust)` (règle 4.5 du `router_system.md`) | Question purement institutionnelle (« vous êtes régulés par qui ? », « et si vous fermez ? ») |
| **(B) Specialist consultable** | `consult_specialist(target="trust", purpose="reassure_about_*")` | Un advisor / compliance.general qui veut intégrer un encart factuel rassurant dans une réponse plus large |
| **(C) Couche transverse** | `read_wiki_page(category="trust-security", …)` | Tout agent peut puiser dans la même source de vérité |

### 6.3 Toolset minimal

```python
TOOLS_BY_AGENT["trust"] = [
    select_wiki_pages,
    read_wiki_page,
    ask_user_question,
]
```

**Pas** de `consult_specialist` (terminal, profondeur 1, ne consulte
personne — anti-récursion). **Pas** de tool transactionnel ni produit.
`trust` reste sur les **preuves factuelles**.

### 6.4 Purposes consult_specialist (Lot 4)

Whitelist `consult_purposes._CATALOG` → 3 nouveaux purposes ciblant
`trust` :

| Purpose | Question naturelle |
|---|---|
| `reassure_about_regulation` | « Peux-tu rappeler le cadre réglementaire de Vancelian (régulation, licence, supervision) ? » |
| `reassure_about_custody` | « Peux-tu rappeler comment Vancelian conserve les fonds clients (custody, ségrégation) ? » |
| `reassure_about_security` | « Peux-tu rappeler comment Vancelian sécurise son infrastructure (audits, monitoring, gestion des risques) ? » |

Aucun param requis. La question est figée — l'agent `trust` compose
sa réponse en lisant le wiki `faq/trust-security/`.

### 6.5 Wiki seed `faq/trust-security/`

| Fiche | Contenu |
|---|---|
| `regulation-overview.md` | PSAN/AMF, MiCA/CASP, LCB-FT, RGPD |
| `custody-overview.md` | Ségrégation des fonds, cold storage, scénario faillite |

La catégorie `trust-security` a été ajoutée à `FAQ_CATEGORIES` dans
`agents/repositories/wiki_repo.py` pour être indexée.

### 6.6 System prompt `trust_system.md`

Cadre éditorial : factuel, calme, **non commercial**. Le prompt
définit explicitement ce que `trust` **n'est pas** (pas un
commercial, pas un agent support, pas un juriste) et redirige
poliment hors de son périmètre.

---

## 7. Lot 5 — Métriques & funnel cognitif

### 7.1 Endpoint admin

```
GET /api/admin/assistance/cognitive/funnel?period_days=7
```

Auth : `require_admin_or_ops()`. Read-only stricte.

Retourne un `CognitiveFunnelResponse` :

```jsonc
{
  "period_start": "...", "period_end": "...", "period_days": 7,
  "total_decisions": 1234,
  "by_stage":            [{"label": "discovery",   "count": 412, "pct": 33.4}, …],
  "by_emotional_intent": [{"label": "CURIOSITY",   "count": 380, "pct": 30.8}, …],
  "by_primary_goal":     [{"label": "educate",     "count": 350, "pct": 28.4}, …],
  "by_next_best_action": [{"label": "ask_question","count": 290, "pct": 23.5}, …],
  "by_agent_id":         [{"label": "advisor",     "count": 410, "pct": 33.2}, …],
  "trust_level":         {"avg": 0.62, "min": 0.10, "max": 0.95, "sample_size": 1180}
}
```

### 7.2 Source unique de vérité (pas de migration DB)

Toutes les agrégations lisent
`assistance_agent_decisions.arguments_json` filtré sur
`tool_name='router_classify'`. Les décisions legacy (avant Lot 1) ou
manquantes sont comptées sous `"unknown"` plutôt qu'écartées — pour
mesurer la couverture du pipeline.

### 7.3 CLI local

```
docker exec arquantix-api python scripts/cognitive_funnel.py --period-days 7
docker exec arquantix-api python scripts/cognitive_funnel.py --period-days 30 --json
```

Réutilise les mêmes fonctions d'agrégation que l'endpoint HTTP, mais
sans passer par l'auth ni FastAPI. Pratique pour les diagnostics
locaux pendant le dev.

---

## 8. Flux complet d'un tour

```
USER MESSAGE
   │
   ▼
┌────────────────────────────────────────────────────────────────┐
│ 1. service.start_chat_turn                                      │
│    └─ load previous cognitive_state (from prev router decision)│
│                                                                 │
│ 2. compute_cognitive_state(...)  →  PRELIMINARY                 │
│    • emotional_intent (keyword + LLM hint)                     │
│    • trust_level (érosion/regain)                              │
│    • knowledge_level (long memory)                             │
│    • conversation_stage (du tour précédent ou heuristique)     │
│                                                                 │
│ 3. router._decide_agent                                         │
│    • [COGNITIVE STATE] block injecté en system prompt          │
│    • [INTENT TAGS] (router_intent_tags) inchangé               │
│    • Function calling : route_to / ask_clarification /         │
│      redirect_off_topic                                         │
│                                                                 │
│ 4. compute_cognitive_state(...)  →  FINAL                       │
│    • Intègre le decision_kind (ask_clarification → stage =     │
│      clarification, route_to → stage = recommendation, etc.)   │
│                                                                 │
│ 5. compute_objective(final_cognitive_state)                     │
│    • DEFAULT_BY_EMOTION + OVERRIDE_BY_EMOTION_STAGE            │
│    → primary_goal, next_best_action, stop_pushing              │
│                                                                 │
│ 6. _persist_router_decision                                     │
│    • arguments_json = {                                         │
│        decision_kind, agent_id, confidence,                     │
│        cognitive_state, objective                               │
│      }                                                          │
│    • Persisté dans assistance_agent_decisions                   │
│                                                                 │
│ 7. expert agent stream (advisor / product / market / trust …)  │
│    • [COGNITIVE STATE] + [OBJECTIVE] injectés                  │
│    • _response_framework.md auto-concaténé                     │
│    • Tools (consult_specialist, wiki, …) à disposition         │
│                                                                 │
│ 8. Sortie client : Markdown 4-temps                             │
└────────────────────────────────────────────────────────────────┘
```

---

## 9. Persistance & non-migration DB

Tout l'état cognitif transite par
`assistance_agent_decisions.arguments_json` (JSONB), tool
`router_classify`, `agent_id='router'`. Format :

```jsonc
{
  "decision_kind": "route_to",
  "agent_id": "trust",
  "confidence": 0.9,
  "intent_classification": {…},
  "cognitive_state": {
    "emotional_intent": "FEAR_RISK",
    "conversation_stage": "clarification",
    "trust_level": 0.35,
    "knowledge_level": "medium"
  },
  "objective": {
    "primary_goal": "reassure",
    "next_best_action": "give_proof",
    "stop_pushing": true,
    "strategy_hint": "..."
  }
}
```

**Stratégie de persistance (V1) :**

* JSONB-only — pas de migration en V1, pas de risque d'environnement
  (charte `arquantix-environment-stability`).
* Lecture admin / CLI via les chaînages
  `arguments_json -> 'cognitive_state' ->> 'conversation_stage'` +
  l'index existant `ix_assistance_agent_decisions_agent_created`.

**Lot 6 (2026-05-04) — colonnes natives dénormalisées :**

La migration **152** (`152_assistance_cognitive_columns.py`) ajoute
**6 colonnes nullable** sur `assistance_agent_decisions` qui dupliquent
le contenu cognitif :

| Colonne | Type | Source JSONB |
|---|---|---|
| `emotional_intent` | `varchar(32)` | `cognitive_state.emotional_intent` |
| `conversation_stage` | `varchar(16)` | `cognitive_state.conversation_stage` |
| `knowledge_level` | `varchar(8)` | `cognitive_state.knowledge_level` |
| `trust_level` | `double precision` | `cognitive_state.trust_level` |
| `primary_goal` | `varchar(16)` | `objective.primary_goal` |
| `next_best_action` | `varchar(20)` | `objective.next_best_action` |

Plus 2 index partiels :
* `ix_aad_cognitive_stage_created (conversation_stage, created_at)`
* `ix_aad_emotional_intent_created (emotional_intent, created_at)`

Migration 100 % additive : aucune contrainte CHECK / NOT NULL (pour
laisser respirer l'évolution des enums en V2 — classifieur ML), backfill
SQL non destructif depuis le JSONB existant, downgrade clean.

Le runtime fait du **double-write** dans
`service._persist_router_decision` via `extra_columns=…` du helper
`audit.persist_decision`. Le **JSONB reste la source de vérité**
(audit complet) ; les colonnes natives accélèrent les agrégats funnel
et exposent les données aux outils tiers (Metabase / Retool).
L'admin endpoint `_aggregate_dimension` lit la colonne native en
priorité avec fallback JSONB via `COALESCE` (rétro-compat des décisions
résiduelles non-backfillées).

---

## 10. Tests & non-régression

État au 2026-05-04 (Lot 6 inclus) :

* **1370 tests assistance passent** (vs 1322 avant Cognitive Bot v4).
* Couverture par lot :
  * Lot 1 : `test_assistance_cognitive_state_unit.py`
  * Lot 2 : `test_assistance_conversation_objective_unit.py`
  * Lot 3 : tests dans `test_assistance_agents_unit.py` +
    `test_assistance_orchestration_chain_unit.py`
  * Lot 4 : `test_assistance_trust_agent_unit.py` (20 tests) +
    `test_assistance_consult_purposes_unit.py` (mis à jour, 26 tests)
  * Lot 5 : `test_assistance_admin_cognitive_router.py` (16 tests)
  * Lot 6 : `test_assistance_cognitive_columns_unit.py` (7 tests —
    `extra_columns`, double-write, lecture priorisée colonne/JSONB,
    fallback `unknown`, `_trust_level_stats` mixte)

Les tests vérifient la *forme* (présence des champs, conformité aux
enums, structure des prompts) et la *cohérence* du mapping
émotion → stratégie. Ils n'évaluent pas la *qualité émotionnelle*
des réponses LLM (ça reste un sujet d'évaluation manuelle / A-B).

---

## 11. Limitations & roadmap

### V1 (livré)

* Détection émotionnelle = keywords + LLM hint (pas de classifieur
  ML dédié).
* `trust_level` = heuristique (érosion sur tour FEAR/ANGER, regain
  sur tour CONVERSION/SATISFACTION) — pas de vrai modèle prédictif.

### Wiki Brainstorming Lot 2 (livré — 2026-05-06) — Cognitive State injecté dans chaque sub-agent

**Constat brainstorming Wiki commun** : `cognitive_state` +
`objective` étaient déjà calculés à chaque tour par
`service.start_chat_turn` et injectés dans le **system prompt** de
l'agent expert via `_format_cognitive_blocks(memory_state)`, mais ils
n'arrivaient **jamais** dans le `ToolContext`. Conséquences :

- Aucun tool ne pouvait adapter son comportement à l'état
  émotionnel (ex. `select_wiki_pages` ne savait pas si le client est
  en FEAR pour prioriser une fiche `trust-security/`).
- **Bug latent** : `_run_consult_specialist` perdait
  `cognitive_state` + `objective` lors du spawn du sub-runtime — le
  specialist consulté voyait un état neutre par défaut et pouvait
  enchaîner sur de la recommandation alors que le caller était en
  `stop_pushing=True`.

**Livré** :

1. **`ToolContext` étendu** (`agents/tools/contracts.py`) avec 2
   champs optionnels `cognitive_state: Optional[dict]` +
   `objective: Optional[dict]`. Format dict (anti-cycle d'import,
   sérialisable, fidèle au format `memory_state`).
2. **Plumbing runtime** (`agents/runtime/agent_loop.py`) — au moment
   de construire `ctx`, on lit ces dicts depuis
   `agent_input.memory_state` (rejet défensif si non-dict).
3. **Fix `_run_consult_specialist`** — propagation
   `cognitive_state` + `objective` dans le `memory_state` du
   sub-runtime spawné.
4. **Helpers `tools/shared/cognitive_context.py`** —
   `get_emotional_intent(ctx)`, `get_trust_level(ctx)`,
   `should_stop_pushing(ctx)`, `get_strategy_hint(ctx)`,
   `cognitive_snapshot(ctx)`, etc. Tous read-only, pure, defaults
   `NEUTRAL/discovery/stop_pushing=False` quand l'état est `None`
   ou malformé. Constantes `URGENT_EMOTIONS = {"fear", "anger"}`.
5. **Tests** (`tests/test_assistance_cognitive_context_unit.py`) —
   39 tests : helpers (fallbacks défensifs, clamping
   `trust_level`), plumbing runtime (capture du `ctx` reçu par un
   tool factice), propagation consult_specialist (capture du
   `agent_input` du sub-runtime via `monkeypatch`).

**Pas de changement de comportement métier des tools** dans Lot 2 —
uniquement plumbing + helpers + observabilité. Les Lots suivants
peuvent désormais s'appuyer sur `should_stop_pushing(ctx)` et
consorts pour brancher des comportements (ton wiki, restriction de
widgets `show_*`, sélection contextuelle de fiches).

Tests verts : **319 tests assistance** (Lot 1 + Lot 2) — sweep
large : **1528 tests** assistance verts au total.

### Wiki Brainstorming Lot 3 (livré — 2026-05-06) — Widgets unifiés + garde-fou stop_pushing

**Constat** : les 3 widgets commerciaux exposés au LLM
(`show_instrument_card` carte BTC/ETH/SOL avec CTAs Acheter/Vendre,
`show_crypto_bundles` slider catalogue avec CTAs Investir,
`show_bundle_detail` fiche bundle avec CTAs Voir/Investir) restaient
invocables même quand le client était en FEAR/ANGER. Bug qualité
pure : un client paniqué qui demande « comment va Bitcoin ? » se
voyait pousser un CTA Acheter au lieu d'une rassurance verbale +
preuves.

**Livré** :

1. **Branchement `should_stop_pushing(ctx)`** (Lot 2) sur les 3
   widgets commerciaux — court-circuit AVANT toute requête DB /
   marché (gain latence + tokens log) :
   - `agents/tools/product/show_instrument_card.py`
   - `agents/tools/product/show_crypto_bundles.py`
   - `agents/tools/product/show_bundle_detail.py`

2. **Payload typé `error: stop_pushing_active`** retourné au LLM avec :
   - `emotional_intent` (fear / anger pour audit)
   - `hint` actionnable (« réponds en texte avec rassurance + preuves
     régulation/custody/sécurité ») exploitable par le LLM pour
     reformuler la réponse.

3. **Pas de filtrage CTAs** : on retourne `error` plutôt que
   d'amputer les actions. Décision design : un client en FEAR n'a
   pas besoin de moins de boutons, il a besoin que le bot **ne
   pousse pas du tout** un produit ce tour-ci. Filtrer la moitié
   des CTAs n'aurait pas adressé le vrai besoin.

4. **Widgets informatifs préservés** (`show_top_movers`,
   `show_featured_articles`) — pas de garde-fou. Leur rôle est
   d'informer (pas de CTA d'achat) ; en FEAR, un client peut au
   contraire vouloir des analyses factuelles. Régression couverte
   par un test dédié (`TestInformationalWidgetsNotBlocked`).

5. **Pas d'extension du registry agents** dans Lot 3. Étendre par
   ex. `show_instrument_card` à `compliance.transactional` créerait
   un risque de push commercial dans un contexte transactionnel —
   l'esprit Lot 3 est le renforcement de la pertinence (anti-push)
   et non l'élargissement du push. Cette décision est documentée
   pour ne pas réintroduire l'extension par inertie dans un Lot
   futur.

6. **Tests** (`tests/test_assistance_widgets_stop_pushing_unit.py`) —
   20 tests : court-circuit FEAR/ANGER + objective explicite
   stop_pushing, ordre du garde-fou (avant validation symbol /
   identifier), payload shape stable, non-blocage en curiosity,
   non-blocage des widgets informatifs.

### Wiki Brainstorming Lot 4 (livré — 2026-05-06) — Topic mémoire cross-tour exposé aux tools

**Constat** : le slot `current_topic` (Phase 2 wiki v1.4) persisté
côté `AssistanceConversation.current_topic` est lu jusqu'à
maintenant **uniquement par le router** (pour stabiliser les
follow-ups déictiques type « et lui ? »). Les sous-agents et leurs
tools n'avaient pas accès au sujet actif → un tool `show_bundle_detail`
appelé sur « TOP5 » ne pouvait pas détecter qu'un re-call sur
« ALT5 » au tour suivant constituait une dérive de sujet.

**Livré** :

1. **`ToolContext.current_topic`** (`agents/tools/contracts.py`) —
   nouveau champ `Optional[dict]` qui transporte le snapshot du
   topic actif au format dict (cf. schéma documenté dans
   `conversation_topic.py`).

2. **Plumbing runtime** (`agents/runtime/agent_loop.py`) —
   `memory_state["current_topic"]` (déjà calculé par
   `service.start_chat_turn` via `_safe_get_current_topic`) est
   recopié dans `ToolContext.current_topic` (rejet défensif si
   non-dict).

3. **Propagation `_run_consult_specialist`** — le specialist
   consulté hérite désormais du `current_topic` du caller, ce qui
   évite que le sub-runtime dérive vers un autre instrument /
   produit alors que le sujet est ancré côté caller.

4. **Helpers `tools/shared/topic_context.py`** :
   - `get_current_topic_kind(ctx)` → `"vancelian_product" |
     "instrument" | "topic_other" | None`.
   - `get_current_topic_product_code(ctx)` (uppercase, defensive).
   - `get_current_topic_instrument_symbol(ctx)` (uppercase,
     defensive).
   - `get_current_topic_label(ctx)` → libellé court stable
     (`"vancelian_product:TOP5"`, `"instrument:BTC"`,
     `"topic_other:<slug>"`).
   - `topic_matches_product_code(ctx, code)` /
     `topic_matches_instrument_symbol(ctx, symbol)` — utiles pour
     un tool qui veut détecter une dérive de sujet.
   - `topic_snapshot(ctx)` — log/audit JSON-safe.

5. **Tests** (`tests/test_assistance_topic_context_unit.py`) —
   40 tests : shape `ToolContext.current_topic` (default, dict,
   immutabilité), helpers (None / dict vide / kind inconnu / types
   invalides / casing), `topic_matches_*`, `topic_snapshot`,
   alignement constantes avec
   `conversation_topic.TOPIC_ANCHORING_TOOLS`, plumbing runtime
   (smoke test source-based), propagation consult_specialist.

**Pas de changement de comportement métier des tools** dans Lot 4 —
uniquement plumbing + helpers, comme Lot 2. Un futur lot pourra
brancher `topic_matches_*` sur `show_instrument_card` /
`show_bundle_detail` pour détecter les dérives de sujet et y
répondre par un message de transition explicite.

### Wiki Brainstorming Lot 5 (livré — 2026-05-06) — Observabilité runtime_metrics

**Constat** : Lots 1+3 ajoutent des compteurs de blocages
silencieux (`wiki_quota_exceeded`, `audience_filtered_out`,
`stop_pushing_blocked`) qui sont visibles uniquement dans les logs
serveur. Aucune trace remontée au consommateur SSE / admin UI →
debug d'un tour difficile (pourquoi le bot a-t-il refusé d'afficher
la carte instrument ? combien de fiches wiki ont été masquées par
le filtre audience ?).

**Livré** :

1. **`AgentEvent.runtime_metrics`** (`agents/base.py`) — nouveau
   champ `Optional[dict]` sur le done event, sérialisé dans la
   payload SSE. Schéma stable :
   ```
   {
     "wiki_calls_count": int,
     "wiki_quota_blocked_count": int,
     "audience_filtered_out_total": int,
     "stop_pushing_blocked_count": int,
     "consultations_count": int,
     "embeds_count": int,
     "dedup_hits": int,
   }
   ```

2. **Compteurs cumulés** (`agents/runtime/agent_loop.py`) —
   tracking par tour des blocages :
   - `wiki_quota_blocked_count` incrémenté quand un appel wiki est
     court-circuité par le cap `MAX_WIKI_CALLS_PER_TOUR` (Lot 1).
   - `audience_filtered_out_total` cumule les
     `result["audience_filtered_out"]` exposés par
     `select_wiki_pages` (Lot 1).
   - `stop_pushing_blocked_count` incrémenté quand un widget
     commercial retourne `error: stop_pushing_active` (Lot 3).
   - Reads défensifs (jamais d'exception qui casse le tour).

3. **Émis uniquement au top-level** (`chain_depth == 0`) — un
   sub-loop `consult_specialist` ne porte pas de métriques propres
   (isolation budget, anti-ambiguïté côté UX admin).

4. **Émis uniquement si non-trivial** — quand tous les compteurs
   sont à 0 (cas standard d'un tour nominal sans tool spécial), on
   omet le champ pour ne pas polluer le payload SSE des tours
   simples.

5. **Tests** (`tests/test_assistance_runtime_observability_unit.py`)
   — 10 tests : shape `AgentEvent.runtime_metrics` (default,
   sérialisation SSE), absence de metrics sur tour text-only,
   `wiki_quota_blocked_count` + `wiki_calls_count` cohérents avec
   le cap, `audience_filtered_out_total` agrégé sur N appels,
   robustesse aux types invalides (`audience_filtered_out` non-int),
   `stop_pushing_blocked_count` sur widgets bloqués, schéma exact
   des clés exposées.

Tests verts cumulés : **270 tests** (Lots 1+2+3+4+5) — sweep large
**1598 tests** assistance verts.

### Politique éditoriale Vancelian — Anti-emoji (livré — 2026-05-06)

**Constat** : le LLM (notamment `gpt-4o-mini`) glissait
occasionnellement des emojis (✅ ⚠️ 🎉 🔥 etc.) dans les réponses
texte au client. Incohérent avec le positionnement Vancelian
(institution premium, ton sobre).

**Approche « ceinture + bretelles »** (ne pas se reposer
uniquement sur le prompt, le LLM peut désobéir) :

1. **Prompt** : `_response_framework.md` (auto-injecté à tous les
   agents experts) interdit explicitement tout emoji /
   emoticône / pictogramme Unicode dans la section
   « Interdits absolus ». Si emphase nécessaire → gras Markdown,
   jamais d'icône.

2. **Filtre runtime post-LLM** :
   `services/assistance/text_sanitizer.py` — module pur sans
   dépendance qui strip les codepoints Unicode des blocs emoji
   standard (Emoticons, Misc Symbols & Pictographs, Dingbats,
   Misc Symbols and Arrows, Regional Indicators, Skin tones,
   ZWJ sequences, Variation Selector-16). Ranges figés depuis
   Unicode 13.0.

3. **Symboles utiles préservés** : ©, ®, ™, ÷, ±, →, ←, ≈, ≥,
   ≠, ∞, √, ∑, accents français, guillemets typographiques,
   euros/devises. La regex est **explicite** sur les ranges
   emoji uniquement (pas la catégorie Unicode `So` générique
   qui aurait strippé ces symboles).

4. **Branchement** : `agent_loop.run_agent_loop` strip les
   emojis du `content` final avant `yield AgentEvent(type="delta",
   content=...)`. Idempotent (un re-strip d'un texte propre est
   un no-op via fast path).

5. **Observabilité** : nouveau compteur
   `runtime_metrics.emojis_stripped_count` qui cumule le nb
   d'emojis supprimés par tour. Une valeur > 0 = LLM a désobéi
   au prompt (utile pour monitorer la dérive du modèle).

6. **Politique typographique française préservée** : les
   espaces avant `!` `?` `;` `:` sont conservés (« Salut ! »
   reste correct). Seuls les espaces leading/trailing et les
   doubles espaces résultant du strip sont nettoyés.

**Tests** :
- `tests/test_assistance_text_sanitizer_unit.py` — 71 tests :
  edge cases (None, vide, idempotence), 7 catégories Unicode
  emoji, préservation des 20+ symboles typographiques utiles,
  normalisation des espaces, helper `contains_emojis`,
  `strip_emojis_with_metrics` avec compteur.
- `tests/test_assistance_runtime_emoji_sanitizer_unit.py` —
  4 tests d'intégration : strip dans le delta SSE final,
  exposition dans `runtime_metrics.emojis_stripped_count`,
  pas de pollution metrics quand réponse propre, présence de
  la nouvelle clé dans le schéma.

**Tests verts** : 85 dédiés + 1673 sweep large assistance
sans régression.

### Lot 6 (livré — 2026-05-04)

* **Colonnes natives** dénormalisées sur `assistance_agent_decisions`
  (migration 152, double-write, fallback JSONB) — perf agrégats
  funnel + compat outils tiers (Metabase / Retool / Superset).
* **Page React admin** `/admin/assistance/cognitive-funnel`
  (proxy `/api/admin/assistance/cognitive/funnel`) : period selector
  7/14/30/90 j, cards distribution par dimension, card trust_level
  (avg/min/max), badges sémantiques (rouge = FEAR/ANGER/COMPLIANCE,
  vert = CURIOSITY/OPPORTUNITY).

### Lot 7 (livré — 2026-05-04) — Conversation Continuity Layer

Mémoire **multi-projet client** + continuity déterministe.
Doc dédiée : [`CLIENT_DISCOVERY.md`](./CLIENT_DISCOVERY.md).

* **Migration 153** :
  * `assistance_client_discovery_projects` (FK `person_id`) — cross-conv,
    statuses {active, paused, completed, abandoned}, paramètres JSONB.
  * `assistance_floating_parameters` (FK `conversation_id` + `person_id`) —
    paramètres extraits non encore attribués à un projet.
* **`client_discovery.py`** : extracteur keyword (~60 % coverage) avec
  règles d'attribution strictes :
  1. Co-mention dans le user message.
  2. Question ciblée par le bot (regex `pour ton projet maison`).
  3. Sinon → floating (jamais d'attribution par proximité temporelle).
  Anti-bug critique « 4 ans = vacances » couvert par tests.
* **`client_discovery_repo.py`** : upsert avec **merge non destructif**
  des paramètres, cap 5 projets actifs/personne (paused au-delà), lookup
  cross-conversation, gestion lifecycle floating params.
* **`conversation_continuity.py`** : 3 fonctions déterministes —
  `should_embed_previous_bot_turn` (laconique sans token standalone →
  pré-pend tour bot précédent au LLM), `extract_assistant_listing`
  (parser numéroté + bullet ≥ 2 + détection question), `auto_qcm_from_listing`
  (cap 7 hard / 5 soft, whitelist agents).
* **Hooks runtime** dans `service.start_chat_turn`,
  `router._build_router_messages`, `agent_loop._build_initial_messages` —
  injection du bloc `[CLIENT DISCOVERY]` + substitution user message
  laconique.
* **Framework UX** révisé : nouveau bucket `structural_choice` cap 7/5,
  ancienne règle « 5+ paralyse » remplacée par « 8+ paralyse, regroupe
  en 5-7 catégories », nouvel interdit « ignorer `[CLIENT DISCOVERY]` ».
* **Tests** : 33 + 9 + 30 = 72 tests dédiés Lot 7. Total assistance =
  **1442 tests** (1370 avant Lot 7 → +72), aucune régression.
* **Kill-switches env** :
  `ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED`,
  `ASSISTANCE_AUTO_QCM_ENABLED` (defaults `true`).

### Lot 7 V1.1 (livré — 2026-05-05) — Auto-QCM SSE branché

Suite directe du Lot 7 : la fonction `auto_qcm_from_listing` est
désormais invoquée **automatiquement** dans `service.stream_assistant_turn`
après la boucle async. Détail dans [`CLIENT_DISCOVERY.md`](./CLIENT_DISCOVERY.md)
§ 4.4–4.6.

* **Nouveau module `decide_auto_qcm`** centralisant les garde-fous :
  * agent dans whitelist ;
  * pas de double-QCM (si `ask_user_question` déjà émis) ;
  * pas de redondance avec embeds CTA (`crypto_bundles_card`,
    `bundle_detail_card`, `instrument_detail_card`,
    `transaction_detail`) ;
  * lecture **objective-aware** : `stop_pushing=True` ou
    `next_best_action ∈ {give_proof, give_control, micro_step,
    call_to_action}` → skip (cohérence avec le framework UX
    : on ne convertit pas un tour de réassurance en menu commercial) ;
  * seuil minimum durci à **3 items** (`QCM_AUTO_PROMOTE_MIN_ITEMS`,
    un listing 2 items est plus du parallélisme rhétorique) ;
  * kill-switch `ASSISTANCE_AUTO_QCM_ENABLED=false`.
* **Persistance** : `message_payload.auto_qcm = {prompt, options,
  source: "auto_promoted", truncated}` (compat totale, `message_type`
  reste `text`).
* **SSE** : `done` event enrichi avec la clé `auto_qcm` (atomique,
  pas d'event mid-stream).
* **Flutter** :
  * `AssistanceAutoQcmPayload` (parsing JSON cap 7).
  * `AutoQcmFooter` widget rendu **sous** la bulle texte (distinct
    de `_buildChoicesBubble` qui remplace).
  * `_handleAutoQcmTapped` envoie un nouveau tour avec
    `text=option.label`, `agent_hint=option.agentHint`.
* **Tests** : +14 unit (`decide_auto_qcm`), +14 SSE end-to-end
  (`test_assistance_auto_qcm_sse_unit.py`), +2 ajustements existants,
  +15 Flutter (`auto_qcm_test.dart`). Total assistance API =
  **1472 tests** (1442 avant V1.1 → +30), aucune régression.
* **Admin Next.js** : 4ᵉ colonne « Synthèse cognitive » dans la vue
  conversation (`/admin/customers/[personId]/assistance/conversations/[id]`).
  Composant `CognitiveTurnDiagram.tsx` qui rend un diagramme vertical
  5 sections (Input · Analyse cognitive intention user · Objectif
  réponse bot · Décision router · Chaîne d'agents) à partir de
  `arguments_json` du `router_classify` et de
  `message_payload.metadata.agent_chain`. Best-effort (sections vides
  masquées), résolution auto user-turn → assistant-turn correspondant.
  Aucune modif backend (réutilise l'endpoint `/decisions` existant).

### V2 (suggestions)

1. **Classifieur émotionnel ML** entraîné sur les transcriptions
   anonymisées (LCB-FT compatible).
2. **A/B test** entre framework strict (4 temps imposés) et version
   plus permissive — pour mesurer l'impact réel sur la conversion.
3. **Funnel par cohorte** : `[stage_t-1, stage_t]` pour mesurer les
   transitions (discovery → recommendation = bon, anything →
   discovery = régression).
4. **Recharts** pour visualisation graphique des distributions sur
   la page admin (V1 = barres CSS Progress + Badges).

---

## 12. Références code

| Lot | Fichier |
|---|---|
| 1 | `services/assistance/agents/cognitive_state.py` |
| 1 | `services/assistance/service.py` (compute pré + final, persist) |
| 2 | `services/assistance/agents/conversation_objective.py` |
| 2 | `services/assistance/agents/runtime/agent_loop.py` (injection) |
| — | `services/assistance/agents/orchestration_context.py` (normalisation + rendu prompt, 2026-05) |
| — | `services/assistance/agents/router.py` (tool `route_to` enrichi) |
| 3 | `services/assistance/prompts/_response_framework.md` |
| 3 | `services/assistance/agents/prompt_builder.py` (auto-concat) |
| 4 | `services/assistance/agents/trust.py` |
| 4 | `services/assistance/prompts/trust_system.md` |
| 4 | `services/assistance/agents/tools/shared/consult_specialist.py` |
| 4 | `services/assistance/agents/tools/shared/consult_purposes.py` |
| 4 | `services/assistance/data/wiki/faq/trust-security/*.md` |
| 5 | `services/assistance/admin_cognitive_router.py` |
| 5 | `scripts/cognitive_funnel.py` |
| 6 | `alembic/versions/152_assistance_cognitive_columns.py` |
| 6 | `database.py` (ORM `AssistanceAgentDecision` — 6 colonnes Lot 6) |
| 6 | `services/assistance/agents/tools/shared/audit.py` (`extra_columns`) |
| 6 | `services/assistance/service.py` (double-write) |
| 6 | `services/assistance/admin_cognitive_router.py` (`_aggregate_dimension`) |
| 6 | `services/arquantix/web/src/lib/assistance-cognitive-proxy.ts` |
| 6 | `services/arquantix/web/src/app/api/admin/assistance/cognitive/funnel/route.ts` |
| 6 | `services/arquantix/web/src/app/admin/assistance/cognitive-funnel/page.tsx` |

Et les tests : tous les `tests/test_assistance_*_unit.py` listés au § 10.

---

> **À chaque évolution** du framework cognitif, mettre à jour cette
> doc *en premier* (cf. règle d'or de la charte
> `arquantix-environment-stability` : pas de code avant la doc et la
> validation).

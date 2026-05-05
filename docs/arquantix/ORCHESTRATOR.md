# Orchestrateur (Router) — Documentation complète

> **Version :** Router v2 (v3.1) — 2026-05-04
>
> **Statut :** Production-ready, livré et testé (122 tests dédiés,
> 1199 tests assistance OK).
>
> **Code de référence :**
> - Logique : `services/arquantix/api/services/assistance/agents/router.py`
> - Prompt LLM : `services/arquantix/api/services/assistance/prompts/router_system.md`
> - Catalogues code-as-config :
>   - `agents/router_off_topic_options.py` — liste fixe Niveau 3
>   - `agents/router_intent_tags.py` — 32 tags / 4 familles
>   - `agents/router_clarification_catalog.py` — 27 entrées Niveau 2
> - Hot-path follow-up : `services/assistance/router_hot_path.py`
> - Persistance / dispatch : `services/assistance/service.py::_decide_agent`
>
> **Documents liés :**
> - `MULTI_AGENTS.md` — vue d'ensemble du système agentique
> - `MULTI_AGENTS_RUNTIME.md` — boucle d'exécution des agents experts
> - `MEMORY.md` — mémoire long-terme partagée
> - `PRODUCT_AGENT.md`, `COMPLIANCE_TOPICS.md` — agents experts détaillés

---

## 0. TL;DR

L'**orchestrateur** (router) est le premier maillon de la chaîne
multi-agents. Il reçoit le message utilisateur + l'historique court
+ la mémoire long-terme et décide :

1. **Quel agent expert** doit traiter la requête (`product`,
   `advisor`, `market`, `compliance`, `default`), OU
2. **Demander une clarification** sous forme de QCM, OU
3. **Recentrer** poliment vers l'écosystème Vancelian si le sujet est
   hors-mission.

Sa décision suit **3 niveaux de qualité de la demande** (spec produit,
2026-05-04) :

| Niveau | Diagnostic | Action |
|---|---|---|
| **1** — Sujet clair | Le client cite un produit, un instrument, ou une opération précise | `route_to(<agent>)` direct |
| **2** — Univers Vancelian flou | Le sujet est patrimonial mais la formulation est large | `ask_clarification(<tag>)` avec QCM canonique ou rédigé |
| **3** — Hors mission | Météo, sport, blagues… | `redirect_off_topic(<bridge>)` avec liste fixe de portes d'entrée |

Sous-cas **1.A** (demande mixte multi-angle) → routage systématique
vers `advisor` qui orchestrera via `consult_specialist`.

---

## 1. Vocabulaire

| Terme | Définition |
|---|---|
| **Tour** | Un échange « message user → message assistant » dans une conversation. |
| **Agent expert** | Spécialiste métier (`product`, `advisor`, `market`, `compliance`). Capable d'utiliser des tools (lecture wiki, lecture catalogue, widgets chat, etc.). |
| **Agent default** | Conversation libre (salutations, questions générales sur l'app), pas de tools métier. |
| **Tool** | Fonction OpenAI function-calling. Le router en a 3 (`route_to`, `ask_clarification`, `redirect_off_topic`) ; les agents experts en ont d'autres (read_wiki_page, show_instrument_card, consult_specialist…). |
| **`RouterDecision`** | Objet de sortie du router. Contient `agent_id`, `confidence`, `reasoning`, `fallback_choices`, `redirect_bridge`, `intent_classification`. |
| **Confidence** | Score ∈ [0,1] retourné par le router. Si `< ASSISTANCE_ROUTER_CONFIDENCE_MIN` (défaut 0.5) → le runtime émet un QCM au lieu d'instancier l'agent. |
| **Tag d'intention** | Étiquette sémantique stable (ex. `bundle_crypto`, `epargner`, `retraite`). 32 tags définis dans `router_intent_tags.py`. |
| **`current_topic`** | Slot mémoire JSON décrivant le sujet métier en cours dans la conversation (cf. `MEMORY.md`). Utilisé pour la résolution de `resume_topic` après redirect off-topic. |
| **Hot-path** | Bypass de l'appel LLM router pour les follow-ups courts qui suivent un agent expert — déterministe, ~150-300 ms gagnés. |
| **Fan-out** | Pattern multi-agents en parallèle. **Volontairement non implémenté** dans Router v2 : on préfère le pattern hiérarchique advisor-first via `consult_specialist`. |

---

## 2. Architecture — vue d'ensemble

### 2.1 Schéma logique

```
┌──────────────────────────────────────────────────────────────────────┐
│  Flutter mobile / Web — POST /chat/turn/stream                       │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ user_message + agent_hint?
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  service.start_chat_turn(...)                                        │
│  1. Persiste le message user                                         │
│  2. Construit AgentInput (memory + recent_turns + user_message)      │
│  3. Appelle _decide_agent(...)                                       │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  service._decide_agent — 4 chemins par ordre de priorité             │
│                                                                      │
│  (A) kill-switch ASSISTANCE_MULTI_AGENT_ENABLED=false                │
│      → RouterDecision(agent='default', confidence=1.0)               │
│                                                                      │
│  (B) agent_hint == 'resume_topic' (clic sur option resume)           │
│      → _resolve_resume_topic_hint() lit le dernier agent_used        │
│        non-router de la conv → RouterDecision(agent=resolved)        │
│                                                                      │
│  (C) agent_hint ∈ KNOWN_AGENT_IDS (clic QCM agent valide)            │
│      → RouterDecision(agent=hint, confidence=1.0)                    │
│      OU agent_hint = id d'option de QCM agent → résolution           │
│        clarification_choice_continuity                               │
│                                                                      │
│  (D) Hot-path follow-up (msg court + last agent_used = expert)       │
│      → RouterDecision(agent=last_agent, confidence=1.0)              │
│                                                                      │
│  Sinon → router.classify(agent_input)                                │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  router.classify — appel LLM avec function calling natif             │
│                                                                      │
│  1. _build_router_messages :                                         │
│     ┌──────────────────────────────────────────────────────────┐     │
│     │ system : router_system.md (prompt complet, ~620 lignes)  │     │
│     │ system : memory_block (long_memory + summary, optionnel) │     │
│     │ system : topic_block (current_topic, optionnel)          │     │
│     │ system : [INTENT TAGS] primary_tag=... family=... ...    │     │ ◄── Lot 2
│     │ tail   : 4 derniers tours (recent_turns)                 │     │
│     └──────────────────────────────────────────────────────────┘     │
│                                                                      │
│  2. _compute_intent_classification_dict (keyword-matcher FR+EN)      │
│     attaché à toutes les RouterDecision pour audit                   │
│                                                                      │
│  3. chat_completion_with_tools(tool_choice="required")               │
│     tools = [route_to, ask_clarification, redirect_off_topic]        │
│                                                                      │
│  4. Parse du tool call selon `function.name` :                       │
│     ┌──────────────┬───────────────────────────────────────────┐     │
│     │ route_to     │ _parse_route_to → RouterDecision direct   │     │
│     │ ask_clarif.  │ _parse_ask_clarification :                │     │
│     │              │  • Si tag ∈ catalogue → options canoniques│     │ ◄── Lot 3
│     │              │  • Sinon → options du LLM (legacy)        │     │
│     │ redirect_off │ _parse_redirect_off_topic :               │     │
│     │              │  • Liste FIXE OFF_TOPIC_FIXED_OPTIONS     │     │ ◄── Lot 1
│     │              │  • + slot resume_topic dynamique          │     │
│     └──────────────┴───────────────────────────────────────────┘     │
│                                                                      │
│  5. Attache `intent_classification` à la RouterDecision              │
│  6. Retourne RouterDecision                                          │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  service.start_chat_turn (suite)                                     │
│  • Persiste la décision dans assistance_agent_decisions              │
│    (tool_name="router_classify", agent_id="router", L0)              │
│  • Log JSON structuré "assistance.agent.tour"                        │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  service.stream_assistant_turn                                       │
│                                                                      │
│  Si decision.is_decisive :                                           │
│    → instancie l'agent expert et stream sa réponse SSE               │
│  Sinon (confidence < seuil OU redirect_bridge non-null) :            │
│    → émet event "choices" (QCM)                                      │
│    → la suite reprendra au prochain message client (clic / freeform) │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Composants en jeu

| Composant | Fichier | Rôle |
|---|---|---|
| **Prompt LLM** | `prompts/router_system.md` | Décrit les 3 niveaux, les 4 agents, les 7 règles de décision, les 3 tools, les exemples calibrés (~620 lignes). |
| **Function-calling natif** | `agents/router.py::_routing_tools()` | Schéma OpenAI des 3 tools exposés au LLM. |
| **Pré-classification keyword** | `agents/router_intent_tags.py` | Détecte FR+EN les tags d'intention avant le LLM. Bloc `[INTENT TAGS]` injecté dans le prompt. |
| **Liste fixe off-topic** | `agents/router_off_topic_options.py` | 5 portes d'entrée stables + slot dynamique `resume_topic`. |
| **Catalogue clarifications** | `agents/router_clarification_catalog.py` | 27 entrées canoniques `tag → prompt + 3-5 options`. |
| **Hot-path follow-up** | `assistance/router_hot_path.py` | Bypass déterministe pour follow-ups courts (≤60 chars + agent expert précédent). |
| **Dispatcher** | `assistance/service.py::_decide_agent` | Orchestre les 4 chemins (kill-switch, hint, hot-path, LLM) et persiste la décision. |
| **Persistance audit** | `assistance/service.py::_persist_router_decision` | Écrit chaque décision router dans `assistance_agent_decisions` (lisible dans la vue admin 3 colonnes). |

---

## 3. Les 3 niveaux de qualité de la demande

C'est la spec **produit** du Router v2. Le router LLM doit
discriminer ces 3 cas dans cet ordre :

### Niveau 1 — Sujet identifié → routage direct

Le client mentionne :
- Un **produit Vancelian propriétaire** (Coffre Flexible, Vault,
  Crypto Basket / Bundle, Cloud Mining, Privilege Club, carte
  Vancelian…).
- Un **instrument coté nommé** (BTC, ETH, SOL, USDC, USDT, XRP, ADA,
  AVAX, DOT, DOGE, TRX, action, ETF, indice).
- Une **demande opérationnelle** sur son compte (« mon dépôt »,
  « mon retrait », « mon KYC »).
- Une **demande de conseil personnalisé** (« qu'est-ce que tu me
  conseilles », « quelle allocation pour moi »).

→ `route_to(<agent>, confidence ≥ 0.8, reasoning)` direct.

#### Sous-cas 1.A — demande mixte → advisor-first

Quand la demande mêle **plusieurs domaines** ET contient un
possessif personnel (« mon », « ma », « adapté à mon profil »), on
ne demande **PAS** de clarification. On route directement sur
`advisor` qui orchestrera les consultations via `consult_specialist`.

Exemples :
- *« Quel bundle pour préparer ma retraite vu les taux actuels ? »*
- *« Stratégie d'investissement crypto pour gagner sans trop risquer ? »*
- *« Vu l'inflation, où mettre mon argent chez Vancelian ? »*

→ `route_to(advisor, 0.85)` puis advisor consulte product+market.

#### Sous-cas 1.B — demande claire mono-agent

→ `route_to(<agent_qui_correspond>, 0.85+)`.

### Niveau 2 — Univers Vancelian mais ambigu → précision

Le sujet est dans le périmètre patrimonial / financier, mais la
formulation est trop large pour qu'un agent expert s'impose.

Exemples :
- *« et à propos d'argent ? »*
- *« parle-moi d'investissement »*
- *« j'aimerais bien épargner »*
- *« comment ça marche la retraite ? »*

→ `ask_clarification(tag, prompt?, options?)`.

Deux modes hybrides :

**Mode A — Tag-based (canonique).** Si le bloc `[INTENT TAGS]`
indique un `primary_tag` clair et que la demande client correspond
à ce tag, le LLM passe `tag="<...>"` au tool et le runtime substitue
prompt+options par le QCM canonique du catalogue.

**Mode B — LLM-rédigé (legacy).** Si pas de tag clair (sujet en
cours fortement contextuel = produit Vancelian nommé dans
recent_turns) ou si tag inconnu du catalogue, le LLM rédige
lui-même `prompt` + `options`.

### Niveau 3 — Hors univers Vancelian → recentrer

Le client parle de météo, sport, recettes, blagues, politique,
santé, mathématiques pures, devoirs scolaires, code générique,
culture générale hors finance.

→ `redirect_off_topic(bridge)`.

Le LLM rédige un **bridge bienveillant** (acknowledge + recadrage +
proposition de suite). Les **options** sont systématiquement
substituées par la **liste FIXE de 5 portes d'entrée** + un slot
dynamique `Reprendre <topic>` si la conversation a un
`current_topic` non-trivial.

#### Test rapide pour trancher entre Niveau 2 et 3

> *« Une personne raisonnable trouverait-elle que ce sujet a un
> rapport avec l'argent, l'épargne, le patrimoine, l'investissement,
> la retraite, la fiscalité, ou un instrument financier ? »*
>
> - Oui → Niveau 2 ou Niveau 1.
> - Non → Niveau 3.

---

## 4. Flow complet d'un tour

### 4.1 Path nominal (LLM router appelé)

```
1. POST /chat/turn/stream
   {"conversation_id": ..., "content": "parle moi des bundle"}

2. service.start_chat_turn :
   • Persiste msg user
   • Construit AgentInput :
       - user_message = "parle moi des bundle"
       - recent_turns = [...]
       - memory_state = {"current_topic": ..., "conversation_summary": ...}

3. service._decide_agent :
   • kill-switch ? non
   • agent_hint ? non
   • hot-path ? non (msg trop long ou pas d'agent expert précédent)
   → router.classify(agent_input)

4. router.classify :
   • _compute_intent_classification_dict(input)
     → primary_tag="bundle_crypto", family="investir", scope_level=2
   • _build_router_messages :
     - system : router_system.md
     - system : memory_block (si non-vide)
     - system : topic_block (si current_topic)
     - system : "[INTENT TAGS] primary_tag=bundle_crypto | family=investir | scope_level=2 | preferred_agent=product"
     - tail   : recent_turns[-4:]
   • chat_completion_with_tools(tools=[route_to, ask_clarif, redirect], tool_choice="required")
   • Parse réponse :
     fn_name="route_to", args={"agent_id":"product", "confidence":0.85, "reasoning":"produit Vancelian nommé (Bundle = Crypto Basket)"}
   → _parse_route_to(args)
   → RouterDecision(agent="product", confidence=0.85, reasoning=..., intent_classification={...})

5. service.start_chat_turn :
   • _persist_router_decision (audit) → row dans assistance_agent_decisions
   • log JSON "assistance.agent.tour"

6. service.stream_assistant_turn :
   • decision.is_decisive == True (0.85 ≥ 0.5)
   • Instancie agent product → boucle d'exécution agent_loop
   • Stream SSE delta vers Flutter
```

### 4.2 Path QCM (clarification ou off-topic)

```
1-4. Idem path nominal jusqu'au tool call.

   Cas A — ask_clarification(tag="epargner") :
   • get_clarification_for_tag("epargner") → entry canonique
   • RouterDecision(
       agent="default",  # placeholder
       confidence=0.49,  # < seuil → forcera QCM
       reasoning=entry["prompt"],
       fallback_choices=[3 options canoniques]
     )

   Cas B — redirect_off_topic(bridge="...") :
   • build_off_topic_options(current_topic) → 5 ou 6 options fixes
   • RouterDecision(
       agent="default",
       confidence=0.49,
       reasoning="off_topic_redirect",
       fallback_choices=[5-6 options fixes],
       redirect_bridge=bridge
     )

5. service.start_chat_turn :
   • _persist_router_decision (audit) :
     decision_kind="ask_clarification" ou "redirect_off_topic"
     intent_classification attaché

6. service.stream_assistant_turn :
   • decision.is_decisive == False
   • _build_choices_payload :
     - prompt = redirect_bridge OR reasoning
     - options = fallback_choices + freeform "Rien de tout ça"
     - payload_dict (JSONB stocké)
   • Persiste un AssistanceMessage(role="assistant", agent_used="router", message_type="choices")
   • Stream event SSE "choices" vers Flutter

7. Flutter affiche le QCM. Au prochain tour :
   • Si user clique sur option → POST /chat/turn/stream avec agent_hint
   • Si user tape autre chose → nouveau tour normal (router rejouera)
```

### 4.3 Path hot-path (follow-up court)

```
1. POST /chat/turn/stream
   {"content": "ok et les frais ?"}  # 18 chars

2. service.start_chat_turn → _decide_agent

3. assistance_router_hot_path.should_skip_router_from_input :
   • len(user_message) == 18 ≤ 60 ✓
   • last_assistant_agent_used = "product" (∈ EXPERT_AGENTS_FOR_HOT_PATH) ✓
   • Pas de TOPIC_CHANGE_SIGNALS dans le message ✓
   • Hot-path activé (env)
   → RouterDecision(agent="product", confidence=1.0, reasoning="hot_path_followup")

4. _decide_agent retourne directement, pas d'appel LLM.

5. service.stream_assistant_turn :
   • Instancie product avec contexte des recent_turns
   • Économie : ~150-300 ms + zero token sur le router.
```

---

## 5. Pré-classification keyword (Lot 2)

### 5.1 Pourquoi

Le LLM router seul est :
- **Coûteux** (~150-300 ms / ~500 tokens par tour).
- **Capricieux** sur les nuances (ex. « performance » → market alors
  qu'on parle d'un bundle Vancelian).
- **Opaque** côté audit (pourquoi a-t-il routé sur X ?).

→ On ajoute une **passe déterministe** keyword-matching qui :
1. **Annote** la requête avec son `primary_tag` / `family` / `scope_level` /
   `preferred_agent`.
2. **Injecte** ce résultat dans le prompt LLM comme **signal**
   (l'instruction reste « tu peux surclasser »).
3. **Persiste** la classification dans `assistance_agent_decisions`
   pour audit (visible dans la vue admin 3 colonnes).

### 5.2 Univers de tags — 4 familles + transverse + hors-sujet

| Famille | Tags | preferred_agent par défaut |
|---|---|---|
| **`epargne`** | `epargner`, `securiser_capital`, `livret_coffre`, `rendement`, `avenir_securite` | `advisor` ou `product` |
| **`investir`** | `investir`, `performance`, `retraite`, `bundle_crypto`, `exclusive_offer`, `instrument_cote`, `immobilier_long_terme` | `advisor`, `product`, `market` selon le tag |
| **`compte_ops`** | `compte_kyc`, `depot`, `retrait`, `virement_sepa`, `carte_visa`, `banque` | `compliance` |
| **`marches_analyses`** | `actu_marche`, `opinion_marche`, `cours_evolution`, `macro_inflation`, `trading`, `volatilite` | `market` |
| **`transverse`** | `reussir`, `projet_vie`, `decouvrir`, `argent_general` | `advisor`, `product` selon le tag |
| **`hors_sujet`** | `off_topic_meteo`, `off_topic_sport`, `off_topic_cuisine`, `off_topic_blague` | (none) → redirect |

Total : **32 tags**. Chaque tag a une liste de keywords FR + EN
normalisés (lowercase, sans accents, match par token entier via
regex `(?:^|\W)<kw>(?:$|\W)`).

### 5.3 Mapping famille → scope_level

```python
hors_sujet  → scope_level 3
compte_ops  → scope_level 1   (compliance toujours évident)
autres      → scope_level 2   (univers Vancelian, mais flou)
None        → scope_level 0   (rien détecté → LLM décide seul)
```

### 5.4 Bloc `[INTENT TAGS]` injecté dans le prompt

Construit par `router._build_intent_tags_block(agent_input)`,
prepended au prompt LLM en tant que message `system` :

```
[INTENT TAGS] primary_tag = bundle_crypto | family = investir | scope_level = 2 | preferred_agent = product
```

Format compact, single-line, parsable par le LLM. Le bloc inclut
`other_tags = ...` quand plusieurs tags ont matché.

### 5.5 Cas spéciaux

- **Off-topic mixé avec in-scope** : « la pluie tombe et je pense
  à un bundle » → `primary_tag = bundle_crypto` (in-scope priorise).
  `tags = ("bundle_crypto", "off_topic_meteo")` reste annoté.
- **Aucun match** : « salut » → `primary_tag = None`,
  `scope_level = 0`. Pas de bloc `[INTENT TAGS]` injecté.
- **Accents / casse** : « Épargner » == « EPARGNER » == « epargner ».
- **Verbes conjugués** : « retire » NE matche PAS « retrait » (token
  strict). On préfère ajouter des conjugaisons explicites au catalogue
  plutôt qu'un matcher fuzzy fragile.

### 5.6 Tests unitaires

`tests/test_assistance_router_intent_tags_unit.py` (24 tests) couvre :
- Cohérence du catalogue (ids uniques, familles connues, ≥1 keyword
  par tag).
- Détection sur 11 messages typiques FR+EN.
- Off-topic + in-scope → in-scope gagne.
- Robustesse : message vide, accents, casse, délimiteurs.

---

## 6. Tools du router

Le router LLM **doit** appeler exactement **un** des 3 tools
suivants (`tool_choice="required"`).

### 6.1 `route_to(agent_id, reasoning, confidence)`

**Signature OpenAI** :

```json
{
  "name": "route_to",
  "parameters": {
    "type": "object",
    "properties": {
      "agent_id": {
        "type": "string",
        "enum": ["default", "compliance", "advisor", "product", "market"]
      },
      "reasoning": {
        "type": "string",
        "description": "Phrase courte expliquant le choix"
      },
      "confidence": {
        "type": "number",
        "minimum": 0.0, "maximum": 1.0
      }
    },
    "required": ["agent_id", "reasoning", "confidence"]
  }
}
```

**Sémantique** :
- `confidence ≥ 0.5` (`ASSISTANCE_ROUTER_CONFIDENCE_MIN`) → l'agent
  est instancié et stream sa réponse.
- `confidence < 0.5` → le runtime émet un QCM générique (cas rare,
  le LLM doit préférer `ask_clarification`).
- `agent_id` invalide → fallback `default`, confidence forcée à 0.0
  (sécurité).

**Parser** : `_parse_route_to(args)` (cf. `router.py`).

### 6.2 `ask_clarification(tag?, prompt?, options?)`

**Signature OpenAI** (Router v2 — paramètre `tag` ajouté) :

```json
{
  "name": "ask_clarification",
  "parameters": {
    "type": "object",
    "properties": {
      "tag": {
        "type": "string",
        "description": "OPTIONNEL — tag d'intention. Si fourni et présent dans le catalogue, override complet de prompt + options."
      },
      "prompt": {"type": "string"},
      "options": {
        "type": "array",
        "minItems": 2, "maxItems": 5,
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "string", "enum": ["default", "compliance", "advisor", "product", "market"]},
            "label": {"type": "string"}
          },
          "required": ["id", "label"]
        }
      }
    },
    "required": ["prompt", "options"]
  }
}
```

**Logique hybride** (cf. `_parse_ask_clarification`) :

```
Si args["tag"] in CLARIFICATION_BY_TAG :
  → utilise prompt + options du catalogue
  → IGNORE args["prompt"] et args["options"]

Sinon :
  → utilise args["prompt"] et args["options"]
  → si options vides → fallback default sans QCM (sécurité)
```

**Output** : `RouterDecision(agent="default", confidence=seuil-0.01,
reasoning=prompt, fallback_choices=options)` — la `confidence` est
volontairement sous le seuil pour forcer le runtime à émettre un QCM
au lieu d'instancier `default`.

### 6.3 `redirect_off_topic(bridge)`

**Signature OpenAI** (Router v2 — `options` retiré du contrat input) :

```json
{
  "name": "redirect_off_topic",
  "parameters": {
    "type": "object",
    "properties": {
      "bridge": {
        "type": "string",
        "description": "1 à 3 phrases : acknowledge + recadrage non-jugeant + proposition de suite. Tutoiement, ton chaleureux."
      }
    },
    "required": ["bridge"]
  }
}
```

**Note importante** : avant Router v2, le LLM contrôlait aussi les
`options`. Depuis 2026-05-04, **les options sont substituées par la
liste FIXE** côté runtime (cf. `_parse_redirect_off_topic`). Le LLM
n'a plus à les générer.

**Output** : `RouterDecision(agent="default",
confidence=seuil-0.01, reasoning="off_topic_redirect",
redirect_bridge=bridge, fallback_choices=OFF_TOPIC_FIXED_OPTIONS [+
resume_topic])`.

### 6.4 Tableau récapitulatif des trois tools

| Tool | Quand | Output déclenché côté UI | Confiance retournée |
|---|---|---|---|
| `route_to` | Niveau 1 | Stream SSE de l'agent expert | ≥ 0.8 (cas nominal) |
| `ask_clarification` | Niveau 2 | QCM "Pour mieux te répondre…" | seuil-0.01 (force QCM) |
| `redirect_off_topic` | Niveau 3 | QCM "Bridge + 5 portes d'entrée" | seuil-0.01 (force QCM) |

---

## 7. Catalogues code-as-config

### 7.1 Liste fixe off-topic (`OFF_TOPIC_FIXED_OPTIONS`)

Fichier : `agents/router_off_topic_options.py`.

```python
OFF_TOPIC_FIXED_OPTIONS = (
    {"id": "compliance", "label": "Mon compte et mes opérations"},
    {"id": "product",    "label": "Découvrir un produit Vancelian"},
    {"id": "advisor",    "label": "Conseils pour mes placements"},
    {"id": "market",     "label": "Comprendre les marchés en ce moment"},
    {"id": "advisor",    "label": "Préparer un projet financier"},
)
```

**Slot dynamique resume_topic** : si
`agent_input.memory_state["current_topic"]` non-trivial,
`build_off_topic_options(...)` prepend en 1ʳᵉ position :

```python
{"id": "resume_topic", "label": f"Reprendre {topic_label}"}
```

Le `topic_label` est extrait de `current_topic` par ordre de
priorité : `display_label` > `product_code` > `kind`.

### 7.2 Catalogue de tags (`TAG_CATALOG`)

Fichier : `agents/router_intent_tags.py`.

Chaque entrée est une `TagDefinition` :

```python
@dataclass(frozen=True)
class TagDefinition:
    tag: str                              # "bundle_crypto"
    family: str                           # "investir"
    keywords_fr: tuple[str, ...] = ()     # FR (sans accents, lowercase)
    keywords_en: tuple[str, ...] = ()     # EN
    preferred_agent: Optional[str] = None # "product" | "advisor" | ...
```

Voir [Annexe C](#annexe-c--catalogue-tag_catalog-extrait) pour un
extrait représentatif.

### 7.3 Catalogue de clarifications (`CLARIFICATION_BY_TAG`)

Fichier : `agents/router_clarification_catalog.py`.

27 entrées. Chaque entrée est `tag → {prompt, options[]}` :

```python
"epargner": {
    "prompt": "L'épargne, c'est exactement le cœur de Vancelian. "
              "Tu veux qu'on creuse quoi ?",
    "options": [
        {"agent_id": "product", "label": "Voir les Coffres d'épargne (Flexible / Avenir)"},
        {"agent_id": "advisor", "label": "Combien je peux mettre de côté chaque mois"},
        {"agent_id": "advisor", "label": "Une stratégie d'épargne adaptée à mon profil"},
    ],
},
```

**Couverture obligatoire** : tous les tags non-`hors_sujet` ont une
entrée. Vérifié par
`tests/test_assistance_router_clarification_catalog_unit.py` :
`test_all_in_scope_tags_have_an_entry`.

Voir [Annexe D](#annexe-d--clarification_by_tag-extrait) pour un
extrait.

### 7.4 Pourquoi en code et pas en DB

| Critère | Code-as-config (choisi) | DB (rejeté) |
|---|---|---|
| Versioning | Git natif | Migrations Alembic |
| Audit trail | PR review | Logs DB / triggers |
| Cache | Aucun (lecture en RAM) | À invalider à chaque update |
| Modification rapide | 1 PR + déploiement | UPDATE SQL + invalidation |
| Risque de drift entre envs | Nul (identique partout) | Élevé (snapshot DB par env) |

Si à terme on veut un éditeur back-office, on basculera vers le
même pattern que `product_knowledge` (table SQL + cache TTL +
endpoints admin).

---

## 8. Pattern advisor-first (Lot 4)

### 8.1 Problème

Une demande comme :

> *« Quel bundle pour préparer ma retraite vu les taux actuels ? »*

mêle 3 angles :
- **product** (catalogue des bundles)
- **market** (taux directeurs)
- **advisor** (conseil personnel : « ma retraite »)

Solutions naïves :
- ❌ Demander une clarification (« quel angle veux-tu creuser ? »)
  → frustrant : le client a déjà donné son objectif.
- ❌ Fan-out manuel sur 2-3 agents en parallèle puis merge LLM
  → complexe (latence × N, summary fragile, contrôle des coûts
  difficile).

Solution Router v2 :
- ✅ **Routage systématique sur `advisor`** + advisor consulte les
  agents nécessaires via `consult_specialist`.

### 8.2 Heuristique (côté prompt LLM)

Règle 5.6 du `router_system.md` (citée dans l'[Annexe A](#annexe-a--prompt-complet-router_systemmd)) :

> Si **les 2 conditions** sont remplies → `route_to(advisor)`,
> `confidence ≥ 0.8`. L'advisor consultera les autres agents si
> besoin. Pas de QCM, pas de fan-out manuel.
>
> 1. La phrase contient un **possessif personnel** (« mon », « ma »,
>    « pour moi », « adapté à mon profil ») **ET**
> 2. Elle évoque **au moins 2 dimensions** parmi : `produits`,
>    `marchés/macro`, `objectifs personnels`, `comparaison entre
>    produits`.

### 8.3 Côté agent advisor

L'advisor a `consult_specialist` dans son toolset (cf.
`registry.py`) et est instruit dans son prompt
(`prompts/advisor_system.md`, section « Pattern advisor-first —
chef d'orchestre ») d'utiliser cette consultation systématiquement
sur les demandes mixtes.

Workflow attendu :
1. **Lire le contexte** (snapshot, mémoire long-terme, recent_turns).
2. **Consulter** : 1 ou 2 `consult_specialist` ciblés.
3. **Synthétiser** : 1 réponse client structurée Markdown +
   disclaimer MiFID.

Voir [Annexe B](#annexe-b--section-advisor-first-de-advisor_systemmd).

### 8.4 Pourquoi advisor et pas un nouveau "merger"

- L'advisor a déjà la **mémoire long-terme du client** + le
  **snapshot portefeuille** + un **disclaimer MiFID** dans son
  prompt.
- Créer un agent `merger` séparé dupliquerait ces responsabilités
  et ajouterait un saut de chaîne supplémentaire (latence + coût).
- `consult_specialist` existe déjà depuis Phase 2c et a fait ses
  preuves côté `compliance.transactional` qui consulte `product`.

---

## 9. Hot-path follow-up (court-circuit déterministe)

### 9.1 Pourquoi

Empiriquement, sur une conversation productive, le pattern est :
- 1 question initiale qui mérite une vraie classification LLM.
- N follow-ups courts (« et les frais ? », « ok et la perf ? »,
  « ça veut dire quoi ? ») sur le même sujet.

Le LLM router sur ces follow-ups :
- Coûte ~150-300 ms et ~500 tokens par tour.
- Flippe parfois sur un mot-clé isolé (« perf » → market alors qu'on
  parle d'un bundle).

### 9.2 Conditions

Bypass LLM router (cf. `router_hot_path.should_skip_router_from_input`) :

1. `len(user_message) ≤ ASSISTANCE_ROUTER_HOT_PATH_MAX_CHARS` (défaut 60).
2. Le **dernier message assistant** non-router a `agent_used` ∈
   `{product, compliance, advisor, market}`.
3. `agent_hint` est vide (pas de clic QCM en cours).
4. Le message ne contient **aucun signal de changement de sujet** :
   `par contre`, `autre question`, `autre chose`, etc.
5. `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=true` (kill-switch).

Si toutes les conditions sont vraies → on garde le `agent_used`
précédent.

### 9.3 Quand on tombe en fallback LLM

- Message > 60 chars → vraie question.
- Pas d'agent expert précédent → pas de cible à conserver.
- Signal de changement détecté → laisser le LLM décider.
- Kill-switch off.

### 9.4 Output

`RouterDecision(agent_id=last_agent, confidence=1.0,
reasoning="hot_path_followup")`.

Pas de `intent_classification` (le hot-path court-circuite la
classification keyword aussi — cohérent avec « on continue le
même sujet »).

---

## 10. Slot mémoire `current_topic` + `resume_topic`

### 10.1 `current_topic`

Slot mémoire JSON persisté dans `assistance_conversations.memory_state`
par les agents experts à chaque tour productif. Forme :

```json
{
  "kind": "vancelian_product",
  "product_code": "TOP_5",
  "display_label": "Crypto Basket Top 5",
  "agent_owner": "product",
  "updated_at": "2026-05-04T20:42:00Z"
}
```

Décrit le sujet métier en cours. Documenté en détail dans `MEMORY.md`
section « current_topic ».

### 10.2 `resume_topic` dans le QCM off-topic

Quand le router émet un `redirect_off_topic` et qu'il y a un
`current_topic` non-trivial dans la mémoire :

```python
build_off_topic_options(current_topic={"product_code": "TOP_5"})
# → [
#     {"id": "resume_topic", "label": "Reprendre TOP_5"},  ← prepend
#     {"id": "compliance",   "label": "Mon compte et mes opérations"},
#     {"id": "product",      "label": "Découvrir un produit Vancelian"},
#     ...
#   ]
```

### 10.3 Résolution côté serveur

Quand le client clique sur `resume_topic`, Flutter renvoie
`agent_hint = "resume_topic"`. Côté serveur :

```python
# service._decide_agent
if agent_hint == "resume_topic":
    resolved = _resolve_resume_topic_hint(db, conversation_id=conv_id)
    if resolved:
        return RouterDecision(agent_id=resolved, confidence=1.0,
                              reasoning="resume_topic_resolved")
    # Sinon → re-router LLM
```

`_resolve_resume_topic_hint` lit dans la DB le **dernier message
assistant `agent_used` non-router** de la conversation et le retourne
comme `agent_id`. C'est une résolution **serveur-side** qui empêche
le client d'injecter un `agent_id` arbitraire.

---

## 11. Persistance et observabilité

### 11.1 Persistance dans `assistance_agent_decisions`

Chaque appel router → `_persist_router_decision` (best-effort, jamais
bloquant) :

| Colonne | Valeur |
|---|---|
| `agent_id` | `"router"` |
| `tool_name` | `"router_classify"` |
| `autonomy_level` | `"L0"` |
| `iteration` | `0` |
| `arguments_json` | `{decision_kind, agent_id, confidence, intent_classification}` |
| `reasoning_summary` | `decision.reasoning` (sanitized) |
| `result_summary` | `null` |

Exemple `arguments_json` :

```json
{
  "decision_kind": "route_to",
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

### 11.2 Visibilité côté admin

La **vue admin 3 colonnes** (cf. `MULTI_AGENTS.md` §8.6, livrée en
v3.0) affiche :
- **Colonne timeline** (gauche) : les turns de la conversation.
- **Colonne chat** (centre) : les messages tels que vu par le client.
- **Colonne workflow trace** (droite) : pour chaque turn, **toutes**
  les décisions persistées dans `assistance_agent_decisions`,
  groupées par agent — y compris la **décision router** avec son
  `intent_classification` détaillé.

Un admin / dev peut donc voir, pour n'importe quelle conversation
client :
- Quel `primary_tag` a été détecté.
- Quel agent a été choisi et avec quelle confiance.
- Pourquoi (le `reasoning_summary` du LLM).

### 11.3 Logs structurés

Chaque tour log un JSON (logger `assistance.agent.tour`) :

```json
{
  "conv_id": "...",
  "turn": 4,
  "router": {
    "agent_id": "product",
    "confidence": 0.85,
    "is_decisive": true,
    "is_off_topic": false,
    "fallback_choices_count": 0,
    "intent_classification": {...}
  }
}
```

Greppable côté infra log aggregator.

---

## 12. Configuration (env vars)

| Variable | Défaut | Rôle |
|---|---|---|
| `ASSISTANCE_MULTI_AGENT_ENABLED` | `true` | Kill-switch global. `false` → 100% `default` agent (rollback instantané). |
| `ASSISTANCE_AGENT_ROUTER_MODEL` | `OPENAI_MODEL` (default app) | Modèle LLM utilisé par le router. |
| `ASSISTANCE_ROUTER_TEMPERATURE` | `0.1` | Température LLM router. Très bas pour stabilité de la classification. Clamp [0.0, 2.0]. |
| `ASSISTANCE_ROUTER_CONFIDENCE_MIN` | `0.5` | Seuil sous lequel le runtime émet un QCM. Clamp [0.0, 1.0]. |
| `ASSISTANCE_ROUTER_HOT_PATH_ENABLED` | `true` | Active le bypass hot-path follow-up. |
| `ASSISTANCE_ROUTER_HOT_PATH_MAX_CHARS` | `60` | Longueur max d'un user message éligible au hot-path. Clamp [10, 300]. |

Toutes les fonctions sont dans
`services/assistance/agents/config.py` et **lisent l'env à chaque
appel** (pas de cache module-level) — permet le monkeypatch en
tests et le hot-reload en prod.

---

## 13. Tests

| Fichier | Tests | Couvre |
|---|---|---|
| `test_assistance_router_off_topic_options_unit.py` | 14 | Liste fixe + slot resume + immutabilité |
| `test_assistance_router_intent_tags_unit.py` | 24 | Catalogue + keyword matcher FR+EN + render |
| `test_assistance_router_clarification_catalog_unit.py` | 60 | Couverture catalogue + shape entries |
| `test_assistance_router_v2_integration_unit.py` | 9 | Wiring `_parse_*` + intégration tag/options/resume |
| `test_assistance_router_v2_classify_unit.py` | 7 | E2E `classify(...)` avec mock LLM (3 paths) |
| `test_assistance_router_hot_path_unit.py` | ~25 | Hot-path : conditions, kill-switch, signaux |
| `test_assistance_agents_unit.py::TestRouterRedirectOffTopic` | 7 | Adapté au contrat v2 (liste fixe) |
| `test_assistance_agents_unit.py::TestRouter*` | 60+ | route_to / ask_clarification / etc. |

Total ciblé : **~200 tests router**. Non-régression :
**1199 tests assistance OK**.

---

## 14. FAQ / Debug

### Q1 — Le router me route sur un mauvais agent. Comment debug ?

1. Ouvrir la conversation dans la **vue admin 3 colonnes**.
2. Localiser le turn dans la **colonne timeline**.
3. Lire la **colonne workflow trace** : la 1ʳᵉ entrée doit être
   `router` / `router_classify`. Cliquer dessus → drawer avec
   `arguments_json`.
4. Inspecter `intent_classification.primary_tag` :
   - Si `null` → keyword-matcher n'a rien trouvé. Le LLM seul a
     décidé. À corriger : ajouter le keyword au catalogue
     `router_intent_tags.py`.
   - Si présent mais le LLM a quand même mal routé → corriger les
     règles ou exemples du prompt `router_system.md`.

### Q2 — Comment ajouter un nouveau tag ?

1. Ajouter une `TagDefinition` dans `TAG_CATALOG`
   (`router_intent_tags.py`) avec famille + keywords FR/EN +
   preferred_agent.
2. Ajouter une entrée dans `CLARIFICATION_BY_TAG`
   (`router_clarification_catalog.py`) avec prompt + 3-5 options.
3. Tests : `test_all_in_scope_tags_have_an_entry` validera la
   cohérence.
4. Mettre à jour la **description du tool `ask_clarification`** dans
   `router.py::_routing_tools()` (la liste enum des tags y est
   citée pour que le LLM sache lesquels sont valides).

### Q3 — Le QCM affiche les mauvaises options après un off-topic ?

C'est la liste FIXE — non-modifiable par le LLM. Pour la modifier :
PR sur `OFF_TOPIC_FIXED_OPTIONS` dans
`router_off_topic_options.py`. Tests : `TestFixedListShape` et
`TestBuildWithoutTopic`.

### Q4 — Mon hot-path se déclenche mal / pas assez ?

- Pas assez : message trop long ? Augmenter
  `ASSISTANCE_ROUTER_HOT_PATH_MAX_CHARS`.
- Trop : ajouter le pattern à `TOPIC_CHANGE_SIGNALS` dans
  `router_hot_path.py`.
- Désactiver complètement : `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false`
  (rollback instantané sans rebuild).

### Q5 — Comment forcer un agent (override) en debug ?

Côté Flutter / API : POST `/chat/turn/stream` avec
`agent_hint=<agent_id>`. Le `_decide_agent` shortcut sur ce hint si
valide, en bypassant **router LLM, hot-path et keyword-matcher**.
Idéal pour tests / debug, jamais à utiliser en flow utilisateur
normal.

---

## 15. Roadmap / limites connues

| Limite actuelle | Plan |
|---|---|
| Le keyword-matcher est strict-token (pas de fuzzy) | Si trop de faux négatifs détectés en prod → ajouter conjugaisons FR au catalogue (« retire », « retires », « retiré ») |
| Pas de fan-out runtime (advisor-first synchrone uniquement) | OK pour V2. Si besoin → ajouter un tool `route_to_multiple` qui spawn N agents en parallèle + merger LLM |
| Le LLM router peut ignorer `[INTENT TAGS]` | Acceptable (signal, pas décision). Si dérive → renforcer la directive dans le prompt système |
| Les options du QCM clarification (catalogue) ne sont pas dynamiques | OK pour V2. Si besoin de personnalisation par client → passer en tool `consult_clarification_catalog(client_id, tag)` |
| Pas de A/B testing du prompt router | À ajouter via un flag `ASSISTANCE_ROUTER_PROMPT_VARIANT` qui switch entre `router_system.md` et `router_system_v3.md` |

---

# Annexes

## Annexe A — Prompt complet `router_system.md`

> **Source authoritative :** `services/arquantix/api/services/assistance/prompts/router_system.md`
>
> **Taille :** ~620 lignes. Reproduit ici intégralement pour audit
> et lecture hors-IDE. À chaque modification du fichier source, il
> faut **régénérer** cette annexe (sinon le code et la doc divergent).

```markdown
# Router — Orchestrateur multi-agents Vancelian

Tu es un **agent de routage**. Ton **unique** rôle est de déterminer quel
**agent spécialisé** doit traiter le tour conversationnel courant du
client Vancelian. Tu **ne réponds jamais directement au client**.

## Les 3 niveaux d'orchestration — règle générale

À chaque tour, tu dois discriminer **3 cas de figure**, dans cet ordre :

### Niveau 1 — Sujet identifié → routage direct (`route_to`)

Le client mentionne un **agent expert évident** : un produit Vancelian
nommément cité (Coffre Flexible, Crypto Basket / Bundle, Cloud
Mining…), un instrument coté nommé (BTC, ETH, action…), une demande
opérationnelle sur son compte, une demande de conseil personnalisé.

→ **`route_to(<agent>, confidence ≥ 0.8, reasoning)`**, **JAMAIS** de
clarification ni de redirection. Voir règles 0, 0bis, 1-5.

### Niveau 2 — Univers Vancelian mais ambigu → précision (`ask_clarification`)

Le sujet est clairement dans le **périmètre patrimonial / financier**
de Vancelian (argent, épargne, placement, retraite…) mais la
formulation est **trop large** pour qu'un agent expert s'impose, OU
le sujet est précis mais tu hésites entre 2 agents.

→ **`ask_clarification(prompt valorisant, options concrètes)`**. Voir
règle 5.5.

### Niveau 3 — Hors univers Vancelian → recentrer (`redirect_off_topic`)

Le client parle de **météo, sport, recettes, blagues, politique…** —
sujet clairement étranger à l'argent et au patrimoine.

→ **`redirect_off_topic(bridge chaleureux, options optionnelles)`**.
Voir règle 6.

> **Règle anti-confusion** : avant chaque appel, vérifie que tu n'as
> pas confondu Niveau 1 (un produit Vancelian nommé) avec Niveau 2 (un
> sujet large), ni Niveau 2 (sujet patrimonial) avec Niveau 3
> (off-topic). Le coût d'un Niveau 1 mal classé en 2 est élevé : le
> client doit reformuler ce qu'il avait déjà clairement dit.

## Périmètre Vancelian

Vancelian est une plateforme de **wealth management** — gestion de
patrimoine et de finance personnelle.

L'assistant aide le client sur **deux niveaux** de périmètre :

### Niveau 1 — Sujets in-scope que les **agents experts** savent traiter

- son **compte Vancelian** (KYC, dépôts, transactions, virements, retraits) ;
- les **conseils en placement** personnalisés à partir de son profil ;
- les **produits Vancelian** (livrets, contrats, immo, etc.) ;
- les **instruments financiers cotés** disponibles via Vancelian — cryptos
  (Bitcoin / BTC, Ether / ETH, SOL, USDT, USDC, XRP, ADA, AVAX, DOT,
  DOGE, TRX), actions, indices, ETF — ainsi que les demandes
  *« montre / affiche / envoie le widget <ticker> »*, *« le cours de
  <ticker> »*, *« parle-moi de <ticker> »* ;
- l'**actualité macro / marchés** liée à ses choix d'investissement ;
- le **fonctionnement de l'application** Vancelian elle-même.

### Niveau 2 — Sujets in-scope thématiques (registre Vancelian)

Tout ce qui touche à **l'argent, au patrimoine, à la finance personnelle**
est **dans le périmètre** Vancelian, même si la formulation du client est
trop **large ou floue** pour qu'un agent expert soit l'évidence.

[... reste des sections : Hors périmètre, Agents disponibles,
     Règles de décision 0, 0bis, 1, 2, 3, 4, 5, 5.5, 5.6, 6,
     Tools disponibles (route_to, ask_clarification, redirect_off_topic),
     Mémoire long-terme, Sortie ...]
```

> **Pour la version intégrale (~620 lignes), lire le fichier source.**
> Les règles 0 → 6 + les exemples calibrés représentent la majeure
> partie du prompt. Les sections critiques (règles 5.5 et 5.6) sont
> reproduites ci-dessous séparément.

### Extrait — Règle 5.5 (clarification + paramètre `tag`)

```
5.5. Si le message porte sur l'argent / le patrimoine / l'épargne /
   l'investissement / la retraite / la fiscalité (cf. Niveau 2 du
   périmètre) mais reste trop large pour qu'un agent expert
   s'impose → `ask_clarification`, jamais `redirect_off_topic`.

   Router v2 — utilise le paramètre `tag` quand le bloc
   [INTENT TAGS] (injecté en system) te donne un primary_tag clair
   et que la demande client correspond à ce tag (sans contexte
   produit-nommé fortement déictique). Tu passes alors tag=<...>
   et le runtime substitue prompt + options par un QCM canonique.

   N'utilise PAS `tag` si :
   - Le sujet en cours dans recent_turns est un produit Vancelian
     nommément cité (Bundle Top 5, Coffre Flexible…) — préfère
     des options contextualisées qui reprennent ce sujet.
   - La demande mêle plusieurs angles → préfère route_to(advisor)
     (cf. règle 5.6).
```

### Extrait — Règle 5.6 (advisor-first)

```
5.6. PATTERN ADVISOR-FIRST — demande mixte ou multi-angle.
   Si la demande couvre plusieurs domaines à la fois que ni
   product, ni market, ni compliance ne peut traiter seul :
   route directement sur advisor (pas de clarification, pas de
   fan-out). C'est l'agent advisor qui orchestrera les
   consultations via consult_specialist et synthétisera en un
   seul message client.

   Cas typiques :
   - « Quel bundle pour préparer ma retraite vu les taux ? »
     → route_to(advisor, 0.85)
   - « Stratégie crypto pour gagner sans trop risquer ? »
     → route_to(advisor, 0.85)
   - « Vu l'inflation, où mettre mon argent chez Vancelian ? »
     → route_to(advisor, 0.9)

   Heuristique de détection (les 2 conditions) :
   1. Possessif personnel (« mon », « ma », « adapté à mon
      profil »).
   2. Au moins 2 dimensions parmi : produits, marchés/macro,
      objectifs personnels, comparaison entre produits.
```

---

## Annexe B — Section advisor-first de `advisor_system.md`

> **Source :** `services/arquantix/api/services/assistance/prompts/advisor_system.md`

```markdown
## Pattern advisor-first (Router v2, 2026-05-04) — chef d'orchestre

Depuis le router v2, tu es **systématiquement** désigné chef
d'orchestre quand la demande client mêle plusieurs angles (produit
Vancelian + conseil personnel, marché + conseil, gamme produit +
profil…). Le router évite le fan-out manuel et te confie ces
demandes mixtes parce que **toi seul peux synthétiser** un conseil
qui prend en compte les 3 dimensions (catalogue produits / contexte
marché / profil client).

Tu disposes pour cela de **`consult_specialist`** (cf. tool
disponible). Utilise-le **proactivement** quand :

  * La question du client implique de citer des **caractéristiques
    précises d'un produit Vancelian** (frais, durée d'engagement,
    rendement annoncé) → `consult_specialist(agent="product",
    question="<sub-question précise>")`.
  * Le conseil dépend du **contexte macro / marché actuel** (taux,
    inflation, tendance crypto récente) → `consult_specialist(
    agent="market", question="<sub-question précise>")`.

Structure-toi en 3 temps quand la demande est mixte :

  1. **Lire le contexte** (snapshot, mémoire long-terme, recent_turns).
  2. **Consulter** : 1 ou 2 `consult_specialist` ciblés. Pas de
     consultations en série gratuites — chaque consultation doit
     éclairer une décision concrète de ton conseil.
  3. **Synthétiser** : 1 réponse client structurée (Markdown) qui
     intègre les éléments product + market + profil personnel, avec
     le disclaimer MiFID en pied de message.

**Exemples** :

  > Client : « Quel bundle pour préparer ma retraite vu les taux
  >          actuels ? »
  >
  > → consult_specialist(product, "liste et caractéristiques des
  >   Crypto Baskets Vancelian (Top 2, Top 5)")
  > → consult_specialist(market, "où en sont les taux directeurs
  >   et l'inflation aujourd'hui en zone EUR")
  > → réponse synthétique avec fourchette d'allocation conseillée
  >   + 2 bundles cibles + disclaimer MiFID.
```

---

## Annexe C — Catalogue `TAG_CATALOG` (extrait représentatif)

> **Source :** `services/arquantix/api/services/assistance/agents/router_intent_tags.py`

```python
TAG_CATALOG: tuple[TagDefinition, ...] = (
    # ── ÉPARGNE ────────────────────────────────────────────────
    TagDefinition(
        tag="epargner",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=("epargne", "epargner", "economiser", "economies"),
        keywords_en=("savings", "save", "saving"),
        preferred_agent="advisor",
    ),
    TagDefinition(
        tag="livret_coffre",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=("livret", "coffre", "vault", "coffre-fort",
                     "compte epargne", "rendement quotidien"),
        keywords_en=("vault", "savings account"),
        preferred_agent="product",
    ),
    # ── INVESTIR ───────────────────────────────────────────────
    TagDefinition(
        tag="bundle_crypto",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=("bundle", "bundles", "panier", "paniers",
                     "crypto basket", "basket", "top 2", "top 5"),
        keywords_en=("bundle", "crypto basket", "basket"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="instrument_cote",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=("bitcoin", "btc", "ethereum", "ether", "eth",
                     "solana", "sol", "usdc", "usdt", "xrp", "ada",
                     "avax", "dot", "doge", "trx",
                     "action", "actions", "etf", "indice", "indices"),
        keywords_en=("bitcoin", "btc", "ethereum", "ether", "eth",
                     "solana", "stocks", "etf", "index"),
        preferred_agent="product",
    ),
    # ── COMPTE & OPS ───────────────────────────────────────────
    TagDefinition(
        tag="depot",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=("depot", "deposit", "versement", "crediter",
                     "ajouter de l argent", "alimenter"),
        keywords_en=("deposit", "top up", "fund"),
        preferred_agent="compliance",
    ),
    # ── MARCHÉS & ANALYSES ─────────────────────────────────────
    TagDefinition(
        tag="opinion_marche",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=("que penses-tu", "quel est ton avis", "ton avis",
                     "vaut-il le coup", "vaut le coup",
                     "est-ce le bon moment", "bon moment"),
        keywords_en=("what do you think", "your opinion",
                     "is it worth", "good time"),
        preferred_agent="market",
    ),
    # ── TRANSVERSE ─────────────────────────────────────────────
    TagDefinition(
        tag="argent_general",
        family=TAG_FAMILY_TRANSVERSE,
        keywords_fr=("argent", "pognon", "tunes", "money", "thunes",
                     "patrimoine", "richesse"),
        keywords_en=("money", "wealth"),
        preferred_agent=None,  # → ask_clarification systématique
    ),
    # ── HORS-SUJET ─────────────────────────────────────────────
    TagDefinition(
        tag="off_topic_meteo",
        family=TAG_FAMILY_HORS_SUJET,
        keywords_fr=("meteo", "pluie", "soleil", "neige"),
        keywords_en=("weather", "rain", "snow"),
    ),
)
```

> 32 tags au total. Voir le fichier source pour la version
> intégrale.

---

## Annexe D — `CLARIFICATION_BY_TAG` (extrait)

> **Source :** `services/arquantix/api/services/assistance/agents/router_clarification_catalog.py`

```python
CLARIFICATION_BY_TAG: dict[str, ClarificationEntry] = {
    "epargner": {
        "prompt": "L'épargne, c'est exactement le cœur de Vancelian. "
                  "Tu veux qu'on creuse quoi ?",
        "options": [
            {"agent_id": "product", "label": "Voir les Coffres d'épargne (Flexible / Avenir)"},
            {"agent_id": "advisor", "label": "Combien je peux mettre de côté chaque mois"},
            {"agent_id": "advisor", "label": "Une stratégie d'épargne adaptée à mon profil"},
        ],
    },
    "performance": {
        "prompt": "La performance, c'est un sujet qu'on regarde de près. "
                  "Sur quel angle on creuse ?",
        "options": [
            {"agent_id": "market",  "label": "Les performances de nos produits en ce moment"},
            {"agent_id": "product", "label": "Comparer les performances entre produits"},
            {"agent_id": "advisor", "label": "Une stratégie pour optimiser ma performance"},
        ],
    },
    "retraite": {
        "prompt": "Bien préparer ta retraite, c'est tout à fait notre terrain. "
                  "Tu veux qu'on regarde par quel bout ?",
        "options": [
            {"agent_id": "advisor", "label": "Combien dois-je épargner pour ma retraite"},
            {"agent_id": "product", "label": "Les solutions retraite chez Vancelian"},
            {"agent_id": "advisor", "label": "Une stratégie long terme pour la retraite"},
        ],
    },
    "bundle_crypto": {
        "prompt": "Les Crypto Baskets (Bundles), c'est une porte d'entrée "
                  "élégante. Tu veux qu'on regarde quoi ?",
        "options": [
            {"agent_id": "product", "label": "Voir tous les bundles disponibles"},
            {"agent_id": "advisor", "label": "Adapter un bundle à mon profil"},
            {"agent_id": "market",  "label": "Comparer les performances des bundles"},
        ],
    },
    "argent_general": {
        "prompt": "L'argent, c'est précisément notre sujet ici. "
                  "Par où on commence ?",
        "options": [
            {"agent_id": "product", "label": "Découvrir un produit Vancelian"},
            {"agent_id": "advisor", "label": "Conseils pour mes placements"},
            {"agent_id": "advisor", "label": "Préparer un projet financier"},
            {"agent_id": "market",  "label": "Comprendre les marchés en ce moment"},
        ],
    },
    # ... 22 autres entrées
}
```

> 27 entrées au total. Voir le fichier source pour la version
> intégrale.

---

## Annexe E — Liste fixe `OFF_TOPIC_FIXED_OPTIONS`

> **Source :** `services/arquantix/api/services/assistance/agents/router_off_topic_options.py`

```python
OFF_TOPIC_FIXED_OPTIONS: tuple[OffTopicOption, ...] = (
    {"id": "compliance", "label": "Mon compte et mes opérations"},
    {"id": "product",    "label": "Découvrir un produit Vancelian"},
    {"id": "advisor",    "label": "Conseils pour mes placements"},
    {"id": "market",     "label": "Comprendre les marchés en ce moment"},
    {"id": "advisor",    "label": "Préparer un projet financier"},
)
```

> 5 entrées **immuables** (non-modifiables par le LLM) + 1 slot
> dynamique `resume_topic` ajouté en 1ʳᵉ position si la conversation
> a un `current_topic` non-trivial.
>
> Pour modifier la liste : PR sur ce fichier — versionnée, auditée,
> testée par `TestFixedListShape`.

---

**FIN — Orchestrateur (Router) v3.1.**

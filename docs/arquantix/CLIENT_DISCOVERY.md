# Client Discovery — Cognitive Bot v4 Lot 7

**Statut** : delivered 2026-05-04 — version 1.0 (keyword pass).
**Référence parent** : [`COGNITIVE_BOT.md`](./COGNITIVE_BOT.md).
**Code** :

* `services/assistance/agents/client_discovery.py` — extracteur,
  dataclasses, règles d'attribution.
* `services/assistance/client_discovery_repo.py` — persistance + lookup
  cross-conversation.
* `services/assistance/agents/conversation_continuity.py` — continuity
  layer (embed previous bot turn + listing extractor + auto QCM).
* `alembic/versions/153_assistance_client_discovery.py` — schéma.

---

## 1. Pourquoi ce module existe

Avant Lot 7, le bot mémorisait :

* l'**émotion** courante (Lot 1 — `emotional_intent`),
* l'**état cognitif** (`conversation_stage`, `trust_level`,
  `knowledge_level` — Lot 1),
* le **sujet catalogue en cours** (`current_topic` Lot 1.4 — bundle,
  fonds, instrument coté).

Mais **rien sur le projet du client**. Conséquences observées (audit
conv `f9d59f98`, conv « Bonjour ! » du 2026-05-04) :

| # | Symptôme | Cause racine |
|---|----------|--------------|
| 1 | Tour #11 « investissements ? » → le bot redémarre thématiquement (4 options génériques), oublie le contexte « achat maison » introduit au tour #5 | Aucun stockage de `user_goal` / `active_project` — `current_topic` ne couvre que les sujets catalogue |
| 2 | Tour #15 « Les offres » → le bot répond hors-contexte | Le tour précédent listant 5 familles n'est pas pré-pendu au tour user laconique |
| 3 | Listes 5+ items texte sans QCM cliquable | Framework Lot 3 disait « 5+ paralyse » → l'agent évitait le QCM ; pas de promotion runtime |

Lot 7 résout les trois cas en introduisant un **modèle multi-projet
client** + une **continuity layer** purement déterministe.

---

## 2. Modèle multi-projet

### 2.1 ClientProject

Capture le **why** du client. Plusieurs projets peuvent coexister
(le user peut acheter une maison ET préparer sa retraite ET partir en
vacances). Lié à la **personne**, pas au `pe_clients` — un même
projet peut traverser plusieurs conversations et plusieurs
`pe_clients` (crypto + fiat sous la même personne morale).

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK |
| `person_id` | UUID FK persons | propriétaire du projet |
| `conversation_id_source` | UUID FK assistance_conversations | conv où le projet a été détecté pour la 1ère fois (audit) |
| `label` | str | label canonique (`achat_maison`, `retraite`, `voyage_vacances`, …) |
| `status` | str | `active` \| `paused` \| `completed` \| `abandoned` |
| `confidence` | float (0..1) | confiance de l'extraction |
| `parameters` | JSONB | `ClientProjectParameters` (cf. ci-dessous) |
| `created_at_turn` | int | turn_index de création |
| `last_touched_at_turn` | int | turn_index de dernière maj |
| `notes` | text | audit qualitatif libre |

**Cap** : 5 projets `active` par personne (`MAX_ACTIVE_PROJECTS_PER_PERSON`).
Au-delà, le plus ancien (`last_touched_at_turn ASC`) bascule en
`paused` automatiquement.

### 2.2 ClientProjectParameters

Capture le **how** du client (les paramètres adossés au projet) :

| Paramètre | Type | Exemple |
|-----------|------|---------|
| `horizon_years` | float | `4` (4 ans), `1.5` (18 mois) |
| `target_amount` | float + `target_currency` | `300000 EUR` |
| `initial_amount` | float + `initial_currency` | `80000 EUR` (apport) |
| `recurring_amount` | float + `recurring_currency` | `500 EUR` |
| `recurring_frequency` | str | `weekly` \| `monthly` \| `quarterly` \| `yearly` |
| `liquidity_need` | str | `low` \| `mid` \| `high` |
| `risk_appetite` | str | `very_low` \| `low` \| `mid` \| `high` \| `very_high` |
| `known_constraints` | list[str] | contraintes libres |
| `notes` | str | qualitatif |

Tous **nullable** — l'extraction est progressive.

### 2.3 FloatingParameter

Cas où l'extracteur capture un paramètre **sans pouvoir l'attribuer
sûrement** à un projet (le user dit « 4 ans » seul) :

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | |
| `conversation_id` | FK conv | |
| `person_id` | FK person | |
| `parameter_kind` | str | `horizon_years`, `target_amount`, `risk_appetite`, … |
| `parameter_value` | JSONB | `{"value": 4.0}` |
| `status` | str | `pending_attribution` \| `attributed` \| `discarded` |
| `attributed_project_id` | UUID FK | si attribué |

Le bot **doit demander clarification** au tour suivant avant
d'attribuer.

---

## 3. Règles d'attribution (anti-bug critique)

L'objectif : **éviter** que le bot dise « tu as 4 ans pour les
vacances » alors que le user voulait dire « 4 ans pour la maison ».

Un paramètre est attribué à un projet **uniquement si une de ces
règles est vraie** :

### Règle 1 — Co-mention (priorité absolue)

Le user mentionne **explicitement** le projet ET le paramètre dans le
même message :

> « j'aimerais acheter une maison **dans 4 ans** » → `achat_maison.horizon_years = 4`

Confiance : `0.85`.

### Règle 2 — Question ciblée par le bot

Le tour assistant précédent posait une question **explicitement
rattachée à un projet** (« horizon pour ton **projet maison** ? ») et
le user répond avec un paramètre seul :

> Bot : « Sur quel horizon **pour ton projet maison** ? »
> User : « 4 ans »
> → `achat_maison.horizon_years = 4`

Confiance : `0.75`. Détection regex : `(?:pour|concernant|sur|de)
\s+(?:ton|ta|votre|...|le|la|...)\s+(?:projet\s+)?(maison|...|heritage)`.

### Règle 3 — Sinon : floating

Si **ni** co-mention **ni** question ciblée → le paramètre va en
`FloatingParameter` status=`pending_attribution`. Le bot **ne le
propage à aucun projet** par proximité temporelle.

> User : « dans 4 ans »
> Bot précédent : « Continue, je t'écoute. »
> → `floating_parameters[horizon_years=4]`

Au prochain tour, le bot a 2 options :

* Demander une question de clarification ciblée → règle 2 s'applique.
* Discarder (au-delà de N tours sans résolution).

---

## 4. Conversation Continuity Layer

3 fonctions déterministes (pas de LLM, pas d'I/O DB), branchées en
pré- et post-process autour du loop agentique.

### 4.1 `should_embed_previous_bot_turn(user_message)` → bool

Décide si le tour bot précédent doit être pré-pendu au user message
dans le contexte transmis aux tools de retrieval :

* `False` si la feature flag `ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED`
  est `false`.
* `False` si message vide.
* `False` si word_count > **12** (`LACONIC_WORD_THRESHOLD`).
* `False` si le message contient un **token standalone** : produit
  Vancelian (Coffre Flexible, Bundle, Cloud Mining, …), instrument
  coté (BTC, ETH, USDT, …), label projet (maison, retraite, …).
* `True` sinon.

Cas typiques :

| User message | should_embed |
|--------------|:-:|
| « Les offres » | ✅ True |
| « Le coffre flexible » | ❌ False (token Vancelian) |
| « ETH ? » | ❌ False (instrument coté) |
| « la maison » | ❌ False (token projet) |
| « j'aimerais 300000 EUR sur 4 ans pour ma maison » | ❌ False (long) |

### 4.2 `extract_assistant_listing(text)` → ExtractedListing | None

Parser déterministe qui détecte une liste numérotée ou bullet ≥ 2
items, optionnellement suivie d'une question (présence d'un `?` dans
les 300 derniers chars OU pattern question-trigger : `lequel`,
`laquelle`, `tu préfères`, `parmi`, `which one`, …).

### 4.3 `auto_qcm_from_listing(listing, agent_id)` → AutoQcmCandidate | None

Promotion de la liste en QCM cliquable.

* **Whitelist agents** : `default`, `advisor`, `product`, `market`,
  `trust`. `compliance.*` exclu (a déjà ses propres QCM ciblés).
* **Min items = 3** (V1.1 — un listing 2 items est plus du parallélisme
  rhétorique qu'un menu de choix). Configurable via paramètre
  `min_items` pour usages internes.
* **Soft cap = 5** items (lisibilité optimale).
* **Hard cap = 7** items (Miller's law 7±2 + UI mobile Vancelian).
* Au-delà : tronqué + `truncated=True` + warning loggé.
* Kill-switch : `ASSISTANCE_AUTO_QCM_ENABLED=false`.

### 4.4 `decide_auto_qcm(...)` → AutoQcmDecision (V1.1, 2026-05-05)

Orchestrateur runtime qui centralise **tous** les garde-fous appliqués
au post-process SSE. Retourne `AutoQcmDecision(candidate, skip_reason)`.

Garde-fous (dans l'ordre, premier qui matche → skip) :

| Code de skip | Raison |
|---|---|
| `disabled_by_env` | `ASSISTANCE_AUTO_QCM_ENABLED=false` |
| `agent_not_whitelisted` | agent hors whitelist (cf. 4.3) |
| `runtime_choices_present` | l'agent a déjà émis un `choices` via `ask_user_question` (anti-double-QCM) |
| `embed_has_builtin_ctas` | un embed du tour fournit déjà des CTAs (`crypto_bundles_card`, `bundle_detail_card`, `instrument_detail_card`, `transaction_detail`) |
| `objective_stop_pushing` | `objective.stop_pushing == True` (FEAR / ANGER) |
| `objective_forbids_auto_qcm` | `objective.next_best_action ∈ {give_proof, give_control, micro_step, call_to_action}` |
| `no_listing_detected` | aucun listing dans `full_text` |
| `listing_without_question` | listing sans question fermée à la fin |
| `listing_below_min_items` | < 3 items |

Tous les skips sont loggés en `DEBUG` (audit dev) ; le promote est
loggé en `INFO` (`assistance.auto_qcm.emitted conv=…`).

### 4.5 Branchement runtime SSE V1.1

`service.stream_assistant_turn` appelle `decide_auto_qcm` **après** la
boucle async (avant `_persist_assistant_message` et avant le yield du
`done` final). Si promu :

* **Persistance B** : `message_payload.auto_qcm = {prompt, options,
  source: "auto_promoted", truncated}`. `message_type` reste `text` →
  rétro-compat totale (un client legacy lit juste le texte).
* **SSE C** : la clé `auto_qcm` est ajoutée au `done` event final
  (atomique avec le commit DB, pas d'event mid-stream → 0 race
  condition). Tests E2E : `tests/test_assistance_auto_qcm_sse_unit.py`
  (14 cas dont nominal, double-QCM, embed CTA, stop_pushing,
  next_best_action interdit, kill-switch, listing court).

### 4.6 Côté Flutter (V1.1)

* `AssistanceAutoQcmPayload` (`features/search/data/chat_api.dart`) :
  parsing JSON avec cap `kMaxOptions=7`, source par défaut
  `auto_promoted`.
* `AssistanceHistoryMessage.autoQcmPayload` lu depuis
  `message_payload.auto_qcm` au reload `/messages` (compat ancienne
  réponse SANS la clé : pas de footer).
* `AssistanceTurnEvent.doneAutoQcm` getter pour le SSE live.
* `AutoQcmFooter` widget
  (`features/search/presentation/widgets/auto_qcm_footer.dart`) :
  rendu **sous** la bulle texte (distinct de `_buildChoicesBubble`
  qui remplace), boutons outlined discrets, mode consommé après tap
  (anti double-tap + lecture historique limpide).
* `_handleAutoQcmTapped` (`search_screen.dart`) : tap → envoie un
  nouveau tour avec `text=option.label`, `agent_hint=option.agentHint`.
  Réutilise `_sendMessageWithText` de la mécanique QCM existante.
* Garde côté client `_embedsBlockAutoQcmFooter` : défense en
  profondeur si un embed avec CTAs built-in arrive (le serveur
  applique déjà la règle).

Tests Flutter : `test/features/search/auto_qcm_test.dart` (15 tests,
parsing JSON + widget + mode consommé + payload vide).

---

## 5. Framework UX — caps QCM révisés Lot 7

`prompts/_response_framework.md` mis à jour :

* Ancien : `recommend → 1 ou 2 options MAX (jamais 3+)`.
* Nouveau : `recommend → 2 ou 3 options MAX` pour une recommandation
  **finale**.
* Nouveau bucket **`structural_choice`** pour les listes structurantes
  (familles produits, niveaux de risque, horizons typiques) :
  * Soft cap = 5, hard cap = 7.
  * Termine **OBLIGATOIREMENT** par UNE question fermée.
  * **FORTEMENT RECOMMANDÉ** : appeler `ask_user_question(prompt, options=…)`
    pour transformer la liste en QCM cliquable.
* Ancien interdit « 5+ paralyse » → remplacé par « 8+ paralyse, sinon
  regroupe en 5-7 catégories ».
* Nouvel interdit : `Ignorer le bloc [CLIENT DISCOVERY]` — les
  paramètres connus du client (horizon, target_amount, risk_appetite)
  doivent **filtrer** les options proposées.

---

## 6. Stratégie d'extraction — keyword + LLM gated

### 6.1 Keyword pass (V1 livré)

Latence < 1 ms, déterministe, couvre ~60 % des cas usuels :

* Détection de label de projet : tableau `_PROJECT_KEYWORDS` FR+EN.
* Détection de paramètres : regex compactes (`_RE_HORIZON`,
  `_RE_AMOUNT`, ...) + dictionnaires keyword
  (`_RECURRING_FREQUENCY_KEYWORDS`, `_LIQUIDITY_KEYWORDS`,
  `_RISK_KEYWORDS`).

### 6.2 LLM gated (V1.1 — interface livrée, appelant pas branché)

`should_invoke_llm_extractor` retourne `True` **si** :

* Le keyword pass a trouvé un signal flou (projet sans paramètre, ou
  paramètre sans projet).
* `conversation_stage` ∈ {`discovery`, `clarification`} — le bot
  vient de poser une question d'exploration.
* Il existe des floating params en attente d'attribution.

Modèle prévu : `gpt-4o-mini` `temperature=0`, schéma JSON strict
(function calling). Ajout en V1.1.

---

## 7. Branchements runtime

### 7.1 `service.start_chat_turn`

Avant `_decide_agent`, après le calcul du `cognitive_state`
préliminaire :

```python
active_projects = discovery_repo.list_active_projects_for_person(
    db, person_id, limit=5
)
extraction = discovery_engine.extract_discovery_keyword_pass(
    user_message=user_content,
    last_assistant_text=last_assistant_text,
    active_projects=active_projects,
    current_turn=user_idx,
)

# Switch detection — pause des autres si signal explicite
if person_id and discovery_engine.detect_project_switch_signal(user_content):
    discovery_repo.pause_other_active_projects(...)

# Upsert nouveaux projets / floating params
for proj in extraction.new_or_updated_projects:
    discovery_repo.upsert_project(...)
for fp in extraction.floating_parameters:
    discovery_repo.add_floating_parameter(...)

# Re-fetch + render → memory_state["client_discovery"]
rendered = discovery_engine.render_discovery_for_prompt(
    active_projects=active_projects_post,
    floating_parameters=pending_floating,
)
memory_state_dict["client_discovery"] = rendered

# Préparation context block previous_bot
prev_bot_block = build_previous_bot_context_block(...)
if prev_bot_block:
    memory_state_dict["previous_bot_context_block"] = prev_bot_block
```

Best-effort : `try/except` global qui log mais ne casse jamais le
tour.

### 7.2 `router._build_router_messages`

Injection d'un nouveau system block après `[COGNITIVE STATE]` :

```python
discovery_block = _build_client_discovery_block(agent_input)
if discovery_block:
    messages.append({"role": "system", "content": discovery_block})
```

### 7.3 `agent_loop._build_initial_messages`

Idem injection `[CLIENT DISCOVERY]` + substitution du user message
par le `previous_bot_context_block` si laconique :

```python
if discovery_block:
    sys_chunks.append(discovery_block)

user_payload = agent_input.user_message
if mem.get("previous_bot_context_block"):
    user_payload = mem["previous_bot_context_block"]
messages.append({"role": "user", "content": user_payload})
```

> ⚠️ `agent_input.user_message` reste **intact** côté DB — c'est juste
> l'envoi LLM qui voit le bloc enrichi.

---

## 8. Format du bloc `[CLIENT DISCOVERY]`

```text
[CLIENT DISCOVERY]
active_projects:
  - achat_maison · horizon=4y · target=300000 EUR · risk=low
  - retraite     · horizon=15y · recurring=monthly
pending_parameters:
  - horizon_years={'value': 4.0} (non attribué — clarifier)
```

Compact, lisible LLM, ~5-15 lignes max (cap 5 projets actifs +
quelques floating).

---

## 9. Tests (72 dédiés Lot 7)

* `test_assistance_client_discovery_unit.py` — **33 tests**
  (extraction, attribution, switch, gating, rendu, round-trip).
* `test_assistance_client_discovery_repo_unit.py` — **9 tests**
  (upsert, merge non destructif, cap actif, cross-conv, floating).
* `test_assistance_conversation_continuity_unit.py` — **30 tests**
  (should_embed, build_block, listing parser, auto-QCM caps & whitelist
  & kill-switch).

Non-régression suite assistance : **1442 tests** passent
(1370 avant Lot 7 → +72).

---

## 10. Kill-switches env

Tous les nouveaux modules sont contrôlables sans redéploiement :

| Variable | Default | Effet `false` |
|----------|:-:|--------------|
| `ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED` | `true` | Pas de pré-pend du tour bot précédent au user message |
| `ASSISTANCE_AUTO_QCM_ENABLED` | `true` | `auto_qcm_from_listing` retourne `None` (rollback complet) |

L'extraction discovery elle-même n'a pas de kill-switch dédié — elle
est en `try/except` global et ne peut pas casser un tour. Si un bug
ORM bloque, on peut désactiver par `alembic downgrade 152` (downgrade
clean fourni).

---

## 11. Limitations V1 et roadmap V2

### Limitations V1.x

* Keyword extraction couvre ~60 % des cas. Phrases avec négations
  (« je ne pense PAS partir en vacances ») produisent un faux positif.
  Le LLM gated (V2) corrigera.
* ✅ V1.1 (2026-05-05) : `auto_qcm_from_listing` est désormais
  **branché en post-process SSE** via `decide_auto_qcm` (cf. § 4.4 et
  § 4.5). Garde-fous : objective-aware, embed-aware, kill-switch.
* Cap de 5 projets actifs/personne est conservateur. Si un client a
  réellement 6+ projets actifs, on bascule le plus ancien en `paused`.
  La logique de **réactivation** (« on reparle de la maison ? ») est
  V2.
* Pas de **discard automatique** des floating params (au-delà de N
  tours). En V1 c'est manuel via le repo.

### Roadmap V2

| # | Idée | Bénéfice |
|---|------|----------|
| 1 | LLM extractor `gpt-4o-mini` branché derrière le gating | +25 pts coverage extraction |
| 2 | Discard automatique des floating > N tours | Anti-bruit du bloc `[CLIENT DISCOVERY]` |
| 3 | Réactivation `paused → active` sur signal user | Relances naturelles |
| 4 | Vue admin React `/admin/assistance/client-discovery` | Coaching équipe (qualité extraction) |
| 5 | Métriques funnel : % tours avec extraction réussie, % floating attribués vs discardés | Observabilité |
| 6 | Paramètres ESG / fiscalité / juridiction-spécifiques | Couverture wealth management complète |
| 7 | Auto-QCM v2 : suggestion proactive d'options via mémoire client (recommandations personnalisées sans listing préalable) | UX sur-mesure |

---

## 12. Adhérence à la charte env-stability

* ✅ **Migration 153** : explicitement validée par l'utilisateur (« go
  explicit »). Downgrade clean (`drop_table` symétrique). Pas de
  modification des tables existantes.
* ✅ **Aucun changement** de `COMPOSE_PROJECT_NAME`, `DB_NAME`,
  `DATABASE_URL`, ports, volumes.
* ✅ **Aucun nouveau service Docker**.
* ✅ **2 nouveaux env flags** documentés (kill-switches), defaults
  conservateurs.
* ✅ **Best-effort** sur tout I/O DB — un bug discovery ne casse
  jamais le tour conversationnel.

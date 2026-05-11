# PRD technique — Crypto Investment Intent V1 (`crypto_investment_intent`)

**Statut :** proposition produit / cadrage implémentation — document de vérité pour le périmètre V1 conversationnel uniquement.

**Référencée par :** couche CAL / `crypto_buy` transactionnel dans [`PRD_CONVERSATIONAL_ACTION_LAYER.md`](./PRD_CONVERSATIONAL_ACTION_LAYER.md) (parcours distinct, pas de détournement).

---

## 1. Résumé exécutif

**Objectif :** ajouter un **`action_type` frère** de `crypto_buy`, nommé **`crypto_investment_intent`**, pour un parcours **uniquement conversationnel** : comprendre → collecter trois slots → résolution **100 % backend** → reformulation → **confirmation textuelle** → **arrêt**. Aucune exécution d’ordre, pas de deep-link d’achat, pas de widget transactionnel obligatoire en V1.

**Décision centrale :** ne pas détourner `crypto_buy` (CAL + widgets + étapes `source_list` / `awaiting_launch_confirm` / confirmation). `crypto_buy` reste le **parcours transactionnel** existant ; `crypto_investment_intent` est le **brouillon prudent** pour cadrer l’intention **avant** toute ouverture éventuelle vers le CAL (hors scope V1).

**Périmètre V1 :** intention d’**achat / investissement / renforcement** crypto ; extraction **multi-slots** ; résolution **obligatoire** ; **anti-hallucination stricte** ; audit via brouillon existant + timeline admin.

**Hors scope :** bundles, vaults, offres exclusives, RWA, allocation, suitability, step-up **effectif**, prix comme vérité **côté LLM**, exécution.

---

## 2. Architecture actuelle réutilisée

| Brique | Rôle |
|--------|------|
| **Persistance brouillon** | `AssistanceActionDraft`, `create_action_draft`, `validate_action_draft_business_payload`, enveloppe `cal_contract`, `_lifecycle` (`action_lifecycle.py`). |
| **Registre produit** | `action_registry.ActionDefinition` (TTL, sécurité produit, schémas liés). |
| **Agent action** | `ActionAgent` + `run_agent_loop` (tools + `pending_action` / `conversation_state`). |
| **Routage** | `_transactional_route_guard` + routeur LLM (`agents/router.py`) ; aujourd’hui peut déclencher aussi `bundle_invest`, `swap`, `deposit`, etc. |
| **Funding réel** | `TestClientService.get_cash_data` / `get_crypto_positions` ; agrégation déjà utilisée dans `show_invest_source_accounts.execute` (alignée conceptuellement sur `GET /api/app/cash` et `GET /api/app/crypto-positions`). |
| **Instruments** | `MarketDataInstrument`, patterns comme dans `show_instrument_card.py` / `crypto_sell_start.py`. |
| **Observabilité** | `build_runtime_debug_timeline` avec projection du brouillon actif (`action_type`, `stage`, montants…). |

---

## 3. Architecture cible

```
Message utilisateur
  → Router (mode V1 : crypto intent only ; refus conseil / bundle / …)
  → Agent action + tool(s) dédiés crypto_investment_intent_*
       → extraction slots (LLM + éventuelle couche déterministe merge, comme intake crypto_buy)
       → ActionDraft crypto_investment_intent (slots + backend_validation + confirmation)
  → Resolver backend (sans LLM) : enrichit resolved_id, label, soldes depuis services réels
  → Reformulation assistant (template court, pas JSON client)
  → Demande confirmation textuelle (QCM fermé ou message + flag côté client)
  → FIN V1 (stop_after_user_confirmation)
```

### Séparation des responsabilités

| Couche | Rôle |
|--------|------|
| **LLM** | Intention, slots bruts, questions manquantes, reformulation après résolution backend |
| **Backend resolver** | IDs, labels, soldes, éligibilité, cohérence montant / devise / source |
| **Client** | Confirmation UI (tap) renvoyée en hint — **sans exécution trade** en V1 |

---

## 4. Fichiers impactés (création / modification)

| Fichier | Action |
|---------|--------|
| `action_registry.py` | Ajouter `ActionDefinition` pour `crypto_investment_intent` (`staged=False` ou mini-stages métier dans payload ; TTL ; `requires_confirmation` ; **pas de widget obligatoire**). |
| `action_draft_payload_schemas.py` | Modèle `CryptoInvestmentIntentDraft` (racine payload métier). |
| `action_draft_contract.py` | Branche `cal_contract` : `required_params` / `missing` pour ce type (**ne pas** réutiliser la grille `crypto_buy` / `bundle_invest` telle quelle). |
| `action_lifecycle.py` | Soit nouvelles transitions nommées, soit mapping métier `stage` + champs `backend_validation` / `confirmation` (**recommandé :** ne pas exploser la machine existante sans besoin). |
| `agents/router.py` | Mode V1 crypto intent : routing vers `action` + `transaction_kind` dédié ou **feature flag** ; blocage / redirection bundle, vault, exclusive, RWA, allocation, conseil ouvert. |
| `agents/runtime/agent_loop.py` | Enregistrer tools ; **ne pas** déclencher autorun `crypto_buy` quand le brouillon actif est `crypto_investment_intent`. |
| `agents/tools/action/` | `crypto_investment_intent_start.py` (merge slots + `create_action_draft`) ; `crypto_investment_intent_resolver.py` (appel services, pas de LLM). |
| `flow_json/crypto_investment_intent.v1.json` | **Créer** sous `services/assistance/` — vérité versionnée. |
| `crypto_investment_intent_flow_doc.py` | **Créer** — chargement + validation schéma (Pydantic). |
| `prompts/action_system.md` | Section V1 : interdits (défaut compte, recommandation crypto, prix, exécution). |
| `runtime_debug_timeline.py` | Étendre `_DRAFT_PROJECTION_KEYS` / projection pour slots et statuts validation. |
| `embed_gate.py` | V1 : pas d’embed `action_widget` obligatoire — inchangé ou règle « allow empty embed » déjà OK. |
| `service.py` (assistance) | Si besoin : charger `pending_action` enrichi ; branche résolution post-tool. |
| **Tests** | `test_action_draft_*`, golden conversation, évent. `test_runtime_debug_timeline_unit.py`. |

---

## 5. Contrats JSON

### 5.1 Fichier de flow (versionné)

**Chemin cible :** `services/arquantix/api/services/assistance/flow_json/crypto_investment_intent.v1.json` (avec module `crypto_investment_intent_flow_doc.py` voisin — pas de dossier ``config/`` réservé au module plat `config.py`).

Champs attendus alignés brief : `flow_id`, `action_type`, `enabled`, `required_slots`, `execution_policy`, `runtime_sources` (réutilisation explicite des modules existants), `anti_hallucination_rules`.

**Règle :** le fichier **n’est pas recopié** dans le prompt ; injection d’un **résumé serveur** (slots requis, politique, interdits) ou chargement **uniquement** côté Python pour tools / resolver / tests.

### 5.2 Payload métier `AssistanceActionDraft` (racine)

À modéliser en Pydantic `CryptoInvestmentIntentDraft` :

- `action_type` : littéral `"crypto_investment_intent"`.
- `stage` : étape métier V1 (voir § 7) — distinct de `cal_contract.state` si besoin pour clarté.
- `slots` : objet avec `target_asset`, `source_account`, `amount` (structure détaillée dans le brief : `raw`, `resolved_id`, `label`, `symbol`, `confidence`, `resolution_status`, `available_balance` où pertinent).
- `backend_validation` : `{ "status", "errors" }`.
- `confirmation` : `{ "status", "summary" }`.

### Provenance et confiance par slot (audit V1)

Chaque sous-slot (`target_asset`, `source_account`, `amount`) supporte :

| Champ | Rôle |
|-------|------|
| `raw` | Texte extrait ou cité utilisateur |
| `raw_provenance` | Origine du brut : typiquement `llm_extracted`, `user_explicit`, `deterministic_regex`, … |
| `resolved_id` | Identifiant stable **après** resolver (vide tant que backend n’a pas validé) |
| `resolved_provenance` | Origine de la résolution : `backend_catalog`, `backend_funding_accounts`, `unresolved`, … |
| `resolution_status` | `pending` / `resolved` / `failed` / `ambiguous` / … |
| `confidence` | Score \[0,1\] côté slot (schéma prêt pour seuils futurs type « clarification si < 0,7 ») |

Les champs `resolved_*` sont **exclusivement** enrichis par le resolver backend (sans LLM).

**Compatibilité :** après validation métier, `merge_business_payload_with_contract` continue de produire `cal_contract` ; adapter `_required_for_crypto_like_registry` **vs branche dédiée** `crypto_investment_intent`.

---

## 6. Règles anti-hallucination (opérationnelles)

| Règle | Implémentation |
|--------|----------------|
| Jamais inventer compte / solde / instrument / prix | Resolver seul remplit `resolved_id`, `label`, `available_balance` ; le LLM ne reçoit pas une liste inventée — seulement labels issus du resolver ou questions ciblées. |
| Pas de compte par défaut | Interdiction explicite style `DEFAULT_SOURCE_ACCOUNT_KEY` du flux `crypto_buy` ; si plusieurs sources EUR (ambiguïté), QCM ou question listant **uniquement** les comptes retournés par le backend. |
| IDs = backend | `resolved_id` non null uniquement après succès resolver. |
| Pas de recommandation crypto | Router + prompt : requêtes « dans quoi investir » → **pas** de draft transactionnel ; routage product / advisor / message d’information selon politique produit. |
| Pas d’exécution | Aucun tool `place_order` ; `execution_policy.ai_can_execute_order: false` ; pas de deep-link en V1. |

---

## 7. États lifecycle

**Deux niveaux (recommandation) :**

1. **`payload["stage"]` métier V1** (lisible produit) :  
   `draft_pending_slots` → `draft_ready_for_backend_validation` → `draft_backend_validated` → `draft_pending_user_confirmation`

2. **`payload["_lifecycle"].state`** (machine existante) — **mapping sans refonte lourde** :

| Stage métier V1 | `_lifecycle.state` suggéré | Notes |
|-----------------|----------------------------|--------|
| `draft_pending_slots` | `collecting` | Slots incomplets après merge tour |
| `draft_ready_for_backend_validation` | `collecting` | `backend_validation.status = "pending"` |
| après resolver OK | `awaiting_confirmation` possible ou rester `collecting` jusqu’au summary prêt | À trancher en implémentation |
| `draft_backend_validated` | `awaiting_confirmation` | Résumé généré, en attente utilisateur |
| `draft_pending_user_confirmation` | `awaiting_confirmation` | Synonyme fonctionnel avec la ligne précédente si simplification à 3 étapes internes |

**À trancher en implémentation :** un seul état `_lifecycle` pour « prêt à confirmer » suffit si `confirmation.status` discrimine).

**Macro colonne DB `AssistanceActionDraft.status` :** rester `draft` jusqu’à décision future (confirmé / annulé = phases post-V1).

---

## 8. Stratégie resolver backend (sans LLM)

**Entrée :** brouillon avec `slots.*.raw` (+ `amount.value` / `currency` si parsés).

**Étapes suggérées :**

1. **Target asset** : résolution depuis `MarketDataInstrument` (symbole actif, synonymes BTC / Bitcoin…) ; échecs → `backend_validation.errors` + `resolution_status: ambiguous|failed`.
2. **Source account** : réutiliser la même logique de liste autoritaire que `show_invest_source_accounts.execute` (cash + wallets) ; matching fuzzy contrôlé (token « euro », « USDC ») **sur uniquement cette liste** ; aucun compte si ambiguïté non résoluble.
3. **Amount** : parser normalisé ; cas « tout mon USDC » → flag métier `use_all_available: true` + resolver vérifie position USDC réelle.
4. **Cohérence** : montant ≤ disponible sur la source (si règle produit) ; devise compatible ; actif investissable (règle métier : table / flags existants).

**Sortie :** mise à jour **atomique** du payload (transaction DB) ; **pas** d’appel OpenAI dans ce module.

**Réutilisation explicite :** `TestClientService`, code partagé extrait ou appel direct de la fonction `execute` de `show_invest_source_accounts` avec un contexte tool minimal, ou factorisation interne « list funding rows » pour éviter duplication.

---

## 9. Router — filtrage V1 « crypto only »

- **Accepter** (vers `action` + intent `crypto_investment_intent` quand flag V1 actif) : formulations type **acheter / investir / renforcer** une crypto ; conversion vers une crypto si la **cible est explicite**.
- **Refuser ou rediriger** (pas de draft `crypto_investment_intent`) : bundle, vault, offre exclusive, RWA, allocation personnalisée, **conseil ouvert** (« dans quoi investir »), investissement **non crypto**.

### Coexistence avec `crypto_buy`

Politique produit à trancher :

- **Option A :** flag `ASSISTANCE_CRYPTO_INTENT_V1_ONLY` — garde transactionnelle : route **uniquement** vers `crypto_investment_intent` pour les achats crypto conversationnels ; `crypto_buy` réservé tap produit / autre entrée.
- **Option B :** garde actuelle inchangée + routeur LLM choisit `crypto_investment_intent` en mode « prudent » — plus risqué sans flag.

**Test 7** (plusieurs comptes EUR) : le resolver **ne sélectionne pas** « Compte Euro » par défaut ; le tour suivant = clarification avec **liste backend**.

---

## 10. Tests attendus (golden / unitaires)

**Checklist QA manuelle / recette** (messages exacts, ordre des tools, champs draft + timeline, interdits) : [`QA_CRYPTO_INVESTMENT_INTENT_V1.md`](./QA_CRYPTO_INVESTMENT_INTENT_V1.md).

| # | Scénario | Attendu |
|---|----------|---------|
| 1 | « Je veux acheter du Bitcoin » | Draft créé ou mis à jour ; manque `amount`, `source_account` ; pas de `resolved_id`. |
| 2 | « … 1000 euros de Bitcoin » | Manque `source_account` uniquement. |
| 3 | Message complet compte euro | 3 slots bruts remplis ; puis après resolver, IDs résolus. |
| 4 | « Investis tout mon USDC en ETH » | `amount` = notion tout le disponible ; `source_account` raw USDC ; target ETH. |
| 5 | « Dans quoi tu me conseilles… » | Aucun draft `crypto_investment_intent` ; agent / route ≠ action transactionnelle. |
| 6 | « Achète-moi une offre exclusive » | Hors scope ; pas de draft crypto intent. |
| 7 | « Achète 1000 euros de Bitcoin » avec plusieurs sources EUR | Pas de `resolved_id` source auto ; état clarification ou erreur validation. |

**Couverture :** schéma Pydantic, resolver (mocks `TestClientService`), router (phrases), timeline (clés projection), non-régression `crypto_buy` (tests existants inchangés).

---

## 11. Observabilité

Étendre `runtime_debug_timeline` (projection brouillon actif) avec au minimum :

`action_type`, `stage`, `slots.target_asset.raw`, `slots.target_asset.resolved_id`, `slots.source_account.raw`, `slots.source_account.resolved_id`, `slots.amount.value`, `slots.amount.currency`, `backend_validation.status`, `confirmation.status`.

Conserver `schema_version: runtime_debug_timeline_v1` ou **incrémenter** si contrat admin cassant.

---

## 12. Plan d’implémentation

### P0 — Livraison V1 minimale

- JSON flow + `crypto_investment_intent_flow_doc.py`.
- `ActionDefinition` + `CryptoInvestmentIntentDraft` + branche `action_draft_contract`.
- Tools `start` + `resolver` ; enregistrement registry tools / `agent_loop`.
- Router + flag produit « crypto intent V1 ».
- Prompt `action_system.md` (interdits).
- Tests 1–3, 5–6 + timeline.
- **Pas** de deep-link, **pas** d’exécution.

### P1 — Robustesse

- Tests 4, 7 ; golden end-to-end légers.
- Clarification multi-comptes (QCM options depuis backend).
- Métriques / logs structurés sur resolver.

### P2 — Évolutions

- Passage optionnel vers `crypto_buy` après confirmation utilisateur (nouvelle story).
- Step-up / exécution ; widgets ; bundles — **hors V1**.

---

## Références internes

- CAL / couche transactionnelle : [`PRD_CONVERSATIONAL_ACTION_LAYER.md`](./PRD_CONVERSATIONAL_ACTION_LAYER.md)
- Multi-agents : [`MULTI_AGENTS.md`](./MULTI_AGENTS.md)


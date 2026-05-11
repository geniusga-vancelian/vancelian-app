# QA ciblée — `crypto_investment_intent` V1 (avant P1 UX)

**Objectif :** checklist de validation **manuelle** et **semi-automatisable** (réutilisable en tests d’intégration ou scripts HTTP) pour verrouiller le comportement **PRD** avant la couche P1 (phrases courtes, QCM backend, reformulation, arrêt après confirmation).

**Prérequis environnement**

- `ASSISTANCE_CRYPTO_INVESTMENT_INTENT_V1_ONLY=true`
- Pas d’exécution d’ordre, pas de deep-link dans ce flux, pas de widget `crypto_buy` **tant que** seuls les tools `crypto_investment_intent_*` sont utilisés (voir interdits par scénario).

**Références**

- PRD : [`PRD_CRYPTO_INVESTMENT_INTENT_V1.md`](./PRD_CRYPTO_INVESTMENT_INTENT_V1.md)
- Projection timeline : `services/arquantix/api/services/assistance/runtime_debug_timeline.py` (`_active_macro_draft_projection`)

---

## 1. Checklist globale (tous les scénarios)

Cocher après chaque run :

| # | Contrôle |
|---|----------|
| G1 | Router garde ou LLM choisit `action` uniquement lorsque pertinent ; avec flag V1, achat crypto explicite via garde → `transaction_kind=crypto_investment_intent`. |
| G2 | Aucun embed / widget CAL `invest_source_account_list`, `invest_confirmation_draft`, etc. **issu de** `crypto_buy_start` ou `show_invest_source_accounts` **déclenché comme conséquence directe du parcours intent** (le flux intent n’appelle pas ces tools). |
| G3 | Aucune URL `vancelian://app/invest/crypto_buy_amount` ni autre deep-link achat émise par `crypto_investment_intent_start` / `crypto_investment_intent_resolve`. |
| G4 | Aucun **autorun** serveur simulant `crypto_buy_start` sur le même tour quand un brouillon actif `crypto_investment_intent` existe (`agent_loop` + early-launch autorun). |
| G5 | `resolved_id`, `available_balance`, instruments : **uniquement** après `crypto_investment_intent_resolve` (backend), jamais inventés dans le texte sans trace resolver. |
| G6 | Chaque slot porte au besoin `raw_provenance` / `confidence` côté extraction ; après résolution backend, `resolved_provenance` cohérent (`backend_catalog`, `backend_funding_accounts`, `unresolved`). |
| G7 | Logs / timeline : `action_type=crypto_investment_intent`, `stage` métier cohérent, champs projection slots + `backend_validation_status` + `confirmation_status`. |

---

## 2. Schéma attendu — `AssistanceActionDraft`

**Colonne**

- `action_type` = `crypto_investment_intent`
- `status` = `draft` (macro) tant que non terminal

**Payload racine (métier + enveloppes)**

| Zone | Champs à vérifier |
|------|-------------------|
| Version | `intent_schema_version` = `"1"` |
| Étape métier | `stage` ∈ `draft_pending_slots` \| `draft_ready_for_backend_validation` \| `draft_pending_user_confirmation` (et éventuellement `draft_backend_validated` si utilisé) |
| Slots | `slots.target_asset` : `raw`, `raw_provenance`, `confidence`, `symbol` (optionnel LLM), `resolved_id`, `resolved_provenance`, `label`, `resolution_status`, … |
| | `slots.source_account` : idem pattern |
| | `slots.amount` : `raw`, `value`, `currency`, `use_all_available`, `confidence`, `resolution_status`, … |
| Validation | `backend_validation.status` ∈ `pending` \| `ok` \| `invalid` ; `backend_validation.errors` (liste) |
| Confirmation | `confirmation.status` ; `confirmation.summary` (texte court après succès resolver) |
| CAL | `cal_contract` présent après persistance ; cohérent avec `stage` |
| Cycle de vie | `_lifecycle.state` aligné PRD (ex. `collecting` → `awaiting_confirmation`) |

**Cas « pas de brouillon »**

- Absence de ligne `assistance_action_drafts` avec `status=draft` et `action_type=crypto_investment_intent` pour la conversation **après** le tour (sauf si un autre produit crée un draft — à noter).

---

## 3. Schéma attendu — `runtime_debug_timeline` (projection brouillon actif)

Clés utiles (non exhaustif des champs racine `draft_projection`) :

| Clé | Signification |
|-----|----------------|
| `draft_id` | UUID brouillon |
| `action_type` | `crypto_investment_intent` |
| `draft_status_macro` | `draft` |
| `stage` | Étape métier |
| `lifecycle_state` | État `_lifecycle.state` |
| `slots_target_asset_raw` | Texte brut cible |
| `slots_target_asset_resolved_id` | ID backend post-resolver |
| `slots_source_account_raw` | Texte brut source |
| `slots_source_account_resolved_id` | `account_key` ou équivalent résolu |
| `slots_amount_value` / `slots_amount_currency` | Montant structuré |
| `backend_validation_status` | `pending` / `ok` / `invalid` |
| `confirmation_status` | `none` / `pending` / … |

---

## 4. Ordre nominal des tools (agent `action`)

Séquence **attendue** une fois le routage correct (le LLM peut fusionner plusieurs tours ; l’ordre **logique** est) :

1. `crypto_investment_intent_start` — une ou plusieurs fois pour enrichir les slots (`target_asset_*`, `source_account_*`, `amount_*`).
2. `crypto_investment_intent_resolve` — **quand** les trois dimensions sont renseignées en entrée utilisateur / merge (sinon appel possible mais sortie `ok: false` et erreurs métier).

**Interdictions de chaîne (à vérifier)**

- Enchaînement « intent » → `crypto_buy_start` **sans** décision produit explicite hors scope V1.
- `show_invest_source_accounts` dans le même parcours « intent V1 » (non requis par la PRD P0 ; reste réservé au CAL `crypto_buy`).

---

## 5. Scénarios obligatoires — détail

Légende **garde** : `_transactional_route_guard` (court-circuit avant LLM). Si la garde retourne `None`, le **routeur LLM** tranche (`classify`), mais l’agent cible peut rester `action` selon le message.

### Scénario 1 — Minimal cible

**Message utilisateur (exact)**

```text
Je veux acheter du Bitcoin
```

| Dimension | Attendu |
|-----------|---------|
| **Routing** | Garde déclenchée si message ≥ 8 caractères ; `transaction_kind=crypto_investment_intent` ; `business_intent=action_request` ; `agent_id=action` ; `reasoning` contient `transactional_guard:crypto_investment_intent`. |
| **Tools (ordre)** | `crypto_investment_intent_start` (cible Bitcoin / BTC). **Pas** encore `crypto_investment_intent_resolve` tant que montant + source absents — ou resolve appelé et **échoue** avec erreurs métier (`source_account_manquant`, `amount_manquant`, etc.). |
| **Draft** | Oui, `crypto_investment_intent` ; `stage` typiquement `draft_pending_slots` ; `slots.target_asset.raw` renseigné ; `slots.amount` et `slots.source_account` incomplets ou vides après un seul `start`. |
| **Resolver** | Optionnel si LLM appelle trop tôt → attendu **`ok: false`** + `backend_validation.status=invalid` après resolve, pas de `confirmation.summary` tant que KO. Si resolve non appelé, pas de `resolved_id` sur la cible. |
| **Clarification** | Message court utilisateur ou assistant : montant puis source (ordre métier au choix UX P1 ; ici QA : **les deux infos manquent**). |
| **Timeline** | `action_type=crypto_investment_intent`, `slots_target_asset_raw` présent ; pas de `slots_target_asset_resolved_id` tant que resolve KO / non joué avec instrument trouvé ; `confirmation_status` `none`. |
| **Interdits** | Pas de widget / deep-link `crypto_buy` ; pas d’autorun `crypto_buy` si draft intent actif. |

---

### Scénario 2 — Montant + cible

**Message utilisateur (exact)**

```text
Je veux acheter 1000 euros de Bitcoin
```

| Dimension | Attendu |
|-----------|---------|
| **Routing** | Idem garde `crypto_investment_intent`. |
| **Tools** | `crypto_investment_intent_start` avec montant (`amount_value`, `currency_from` EUR ou équivalent extrait par le LLM) + `target_asset_*`. **`crypto_investment_intent_resolve`** possible **ici** mais attendu **`ok:false`** encore si `source_account` manquant. |
| **Draft** | Oui ; cible + montant remplis côté slots bruts après `start`. |
| **Resolver** | Appel facultatif même tour → erreurs liste contenant problème source **ou** `source_account_manquant`. |
| **Clarification** | Demander uniquement **compte source** (aligné PRD). |
| **Timeline** | `slots_amount_value=1000`, `slots_amount_currency` cohérent ; `slots_source_account_resolved_id` absent si source non résolue. |
| **Interdits** | Idem scénario 1. |

---

### Scénario 3 — Complet trois slots bruts puis résolution

**Message utilisateur (exact)**

```text
Je veux acheter 1000 euros de Bitcoin depuis mon compte euro
```

| Dimension | Attendu |
|-----------|---------|
| **Routing** | Garde idem intent. |
| **Tools** | `crypto_investment_intent_start` (tous slots bruts présents dans les args LLM)** puis **`crypto_investment_intent_resolve`**. Ordre obligatoire : `start` avant `resolve` sur données fraîches. |
| **Draft** | Oui ; `stage` passe à `draft_ready_for_backend_validation` ou équivalent après merge ; après resolve OK → `draft_pending_user_confirmation` ; `confirmation.summary` renseigné ; `backend_validation.status=ok`. |
| **Resolver** | **`ok:true`** si instrument + funding + montant OK. |
| **Clarification** | Aucune si tout résolu sans ambiguïté. |
| **Timeline** | `resolved_id` cibles + source projetés après succès (`slots_*_resolved_id`) ; `backend_validation_status=ok` ; `confirmation_status=pending` (après summarize). |
| **Interdits** | Toujours pas de CAL `crypto_buy`. |

***

**Note QA LLM**

Le tool `start` n’injecte pas le texte user brut dans la DB automatiquement : le **runtime** doit transmettre `target_asset_raw`, etc. Contrôler en base que les champs reflètent bien l’intent — sinon échec QA côté « assistant n’a pas appelé le tool avec contenu conforme », pas forcément resolver.

***

---

### Scénario 4 — « Tout » sur USDC → ETH

**Message utilisateur (exact)**

```text
Investis tout mon USDC en ETH
```

| Dimension | Attendu |
|-----------|---------|
| **Routing** | **Attention** : la garde utilise le lemme `\binvestir\b` ; la forme **« Investis »** peut **ne pas** matcher → `transactional_route_guard=None` → **routeur LLM** peut encore envoyer vers `action` si l’intent est bien classée — **checkbox QA** « routage » : noter guard vs LLM. |
| **Tools** | `crypto_investment_intent_start` avec `amount_use_all_available=true`, `target_asset*` vers ETH**, `source_account*` vers USDC / wallet USDC**. Puis **`crypto_investment_intent_resolve`** quand trois axes cohérents. |
| **Draft** | Oui après `start` si tool appelé ; `slots.amount.use_all_available=true`. |
| **Resolver** | Doit refléter logique disponible backend (soldes réels TestClient — conformité données dev). |
| **Clarification** | Possibles ambiguïtés plusieurs wallets USDC (futur P1). |
| **Timeline** | Même jeu de clés ; `resolver` doit marquer erreurs si ambigu. |
| **Interdits** | Idem. |

*(Comportement P0 métier peut nécessiter P1 prompting si le LLM n’extrait pas `use_all_available` — noter en QA.)*

---

### Scénario 5 — Conseil ouvert (pas de draft)

**Message utilisateur (exact)**

```text
Dans quoi tu me conseilles d'investir ?
```

| Dimension | Attendu |
|-----------|---------|
| **Routing** | Garde **absente** : motif « `me conseilles` » (advisory) sans marqueur **commitment** (`je veux`, …) → `_transactional_route_guard returns None`. Routeur LLM → typiquement **pas** `action_request` + intent transactionnelle, plutôt `advisor` / `product` / `default` selon politique. |
| **Tools** | **Aucun** `crypto_investment_intent_*` **requis** ; si appelé = **écart QA** sauf justification produit. |
| **Draft** | **Aucun** `crypto_investment_intent` créé sur ce tour. |
| **Resolver** | N/A |
| **Clarification** | Réponse conversationnelle hors CAL (information, pas brouillon). |
| **Timeline** | Pas de projection `crypto_investment_intent` active ; ou autre `action_type` seulement si autre parcours. |
| **Interdits** | Pas de push achat cryptos non sollicité via intent draft. |

---

### Scénario 6 — Offre exclusive (hors scope)

**Message utilisateur (exact)**

```text
Achète-moi une offre exclusive
```

| Dimension | Attendu |
|-----------|---------|
| **Routing** | Garde retourne **explicitement** `None` (motif offre exclusive) — pas de court-circuit vers `crypto_investment_intent` / `crypto_buy` par la garde. |
| **Tools** | Pas d’appel `crypto_investment_intent_*` **attendu** ; si le LLM en produit un = **écart QA**. |
| **Draft** | **Aucun** `crypto_investment_intent`. |
| **Resolver** | N/A |
| **Clarification** | Message expliquant hors scope / autre agent. |
| **Timeline** | Pas de brouillon intent. |
| **Interdits** | Pas de widget `crypto_buy`. |

---

### Scénario 7 — Multi sources EUR (ambiguïté)

**Message utilisateur (exact)**

```text
Achète 1000 euros de Bitcoin
```

**Précondition données** : le client dispose de **plusieurs** lignes source « EUR / compte euro » dans l’agrégat utilisé par le resolver (aujourd’hui le code marque ambigu si **plus d’une** ligne fiat EUR-like est présente dans la liste construite — **en dev standard une seule ligne fiat** peut masquer le cas ; la QA exige un **jeu de données** ou mock multi-comptes).

| Dimension | Attendu |
|-----------|---------|
| **Routing** | Garde `crypto_investment_intent` (comme scénario 2). |
| **Tools** | `start` puis `resolve`. |
| **Draft** | Oui. |
| **Resolver** | **`ok:false`** ; erreurs contenant la logique **ambiguïté multi-EUR** (`plusieurs_sources_eur_non_resolues` ou équivalent) ; **pas** de `resolved_id` source auto ; `backend_validation.status=invalid`. |
| **Clarification** | Liste **fermée** des comptes **issue backend uniquement** (P1 UX : QCM / options) — en P0, vérifier au moins l’**échec contrôlé** du resolver. |
| **Timeline** | `backend_validation_status=invalid` ; pas de `slots_source_account_resolved_id` ; possible `slots_target_asset_resolved_id` si instrument OK mais source KO (selon ordre d’erreurs impl.). |
| **Interdits** | Aucune sélection silencieuse du « Compte Euro » par défaut. |

---

## 6. Cas récapitulatifs — « aucun draft `crypto_investment_intent` »

| Contexte | Attendu |
|----------|---------|
| Scénario 5 (conseil) | Pas de draft intent imposé par la garde ; vérifier absence après tour. |
| Scénario 6 (offre exclusive) | Idem. |
| Message trop court (< 8 caractères) | Garde inactive ; pas de draft via garde. |
| Utilisateur anonyme (`client_id` absent) | `crypto_investment_intent_start` retourne `client_required` — **pas** de persistance draft. |
| Session sans appel outil | Naturellement pas de draft (sauf autre action CAL). |

---

## 7. Automatisation (pistes sans changer le métier)

- **Unit / integration** : réutiliser les patterns de `tests/test_crypto_investment_intent_unit.py`, `TestTransactionalRouteGuard`, et étendre avec DB de test + `create_action_draft` / appels `execute` tools sur `ToolContext` mocké.
- **HTTP** : enchaîner `POST` assistance chat avec les **7 messages exacts** ; parser la réponse serveur + requête SQL `assistance_action_drafts` par `conversation_id`.
- **Timeline** : `build_runtime_debug_timeline` après chaque message et assert sur les clés §3.

---

## 8. Après validation QA → P1 UX (rappel cible)

Enchaînement produit visé (hors scope de ce document) :

1. Slot manquant → **question courte**
2. Slot ambigu → **choix fermés** alimentés par backend
3. Slots complets → **reformulation claire**
4. Confirmation utilisateur → **arrêt** sans exécution

Ce fichier **ne modifie pas** le comportement runtime : il sert de **contrat de recette** avant implémentation P1.

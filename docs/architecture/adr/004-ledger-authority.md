# ADR 004 — Ledger Authority

## Constitution de la plateforme Vancelian

> **Ce document a priorité opérationnelle sur ADR 001, 002 et 003.**
>
> Si un webhook, une API, un cron ou un service produit écrit directement ledger / PE / balances, alors intent, outbox, worker et controller **ne servent plus à rien**.

| Question | Réponse (ADR 004) |
| --- | --- |
| **Qui décide ?** | Transaction Intent (orchestrateur — ADR 001) |
| **Qui transporte ?** | Outbox (ADR 002) |
| **Qui exécute ?** | Worker |
| **Qui écrit l’économique ?** | **Settlement Layer uniquement** |
| **Qui vérifie ?** | Reconciliation Controller (ADR 003) |
| **Qui a le droit de terminer ?** | Controller → `COMPLETED` |

### Règle constitutionnelle

> **Aucune écriture économique en dehors de la Settlement Layer.**

Crypto spot, vaults, bundles, Lombard, RWA, actions tokenisées, produits MiFID : **un seul moteur** — pas de reconstruction tous les 6 mois.

```
Provider / Blockchain
        ↓
Intent → Outbox → Worker
        ↓
Settlement Layer          ← seul writer
        ↓
Ledger → PE → Controller → COMPLETED
```

### Risque principal restant (disciplinaire, pas technique)

Le trou architectural S2→S6 est comblé. Le risque dominant devient **les contournements « pour aller plus vite »** :

- Webhook → écrit ledger
- Cron → écrit PE
- API → incrémente balance

**Gouvernance PR (règle vérifiable en review)** :

Toute PR qui modifie l’une de ces tables :

- `person_wallet_balances`
- `person_wallet_deposits`
- `pe_position_atoms`
- scopes PE (`trading_available`, `vault_position`, `bundle_cash`, etc.)

doit **démontrer** qu’elle passe par **Settlement Layer** (`settle_transaction_intent_idempotently` ou module `services/settlement/`).

Sinon : **rejet** — pas d’exception « pour aller plus vite ».

Checklist reviewer :

- [ ] Écriture économique uniquement dans Settlement Layer
- [ ] `intent_id` traçable sur chaque mouvement
- [ ] Pas de `increment_balance` / `fund_*` / `apply_swap_settlement` hors settlement
- [ ] Webhook / API / cron = producteur d’event, pas writer ledger

---

| Champ | Valeur |
| --- | --- |
| **Statut** | Accepté — **constitution plateforme** |
| **Date** | 2026-06-07 |
| **Décideurs** | Équipe Arquantix / Vancelian |
| **Contexte** | Noyau transactionnel Vancelian — cœur comptable |
| **Priorité** | **ADR 004 > ADR 001 > ADR 002 > ADR 003** (criticité opérationnelle) |
| **Lié à** | ADR 001 (Intent), ADR 002 (Outbox), ADR 003 (Reconciliation Controller) |

**Métaphore** : ADR 001 = cerveau · ADR 002 = système nerveux · ADR 003 = système immunitaire · **ADR 004 = constitution / cœur comptable**.

---

## 1. Problème actuel

Plusieurs chemins écrivent en parallèle dans les couches économiques de Vancelian :

| Appelant | Tables touchées | Fichiers représentatifs |
| --- | --- | --- |
| API HTTP (poll LI.FI) | `person_wallet_deposits`, `person_wallet_balances` | `lifi_swap_settlement.py` via `lifi_execute_service.py` |
| Webhook Privy | `person_wallet_deposits`, balances | `privy_wallet/webhook_service.py` |
| Cron / maintenance | ledger Privy | `swap_session_maintenance.py`, `lifi_swap_reconciliation.py` |
| Bundle orchestrator | `pe_position_atoms`, ledger LI.FI | `bundles/orchestrator.py`, `pe_settlement.py` |
| Vault / Lombard dual-write | `pe_position_atoms` | `vault_funding.py`, `lombard_funding.py` |
| Admin / correction | ledger, PE | `onchain_reconciliation/correction_apply.py` |
| Financial reset | tout | `financial_reset/reset.py` |

**Conséquence** : écarts systémiques entre on-chain, ledger Privy, PE scopes et UI — exactement ce qui motive les audits custody, les reconcileurs multiples (`person_crypto_reconciliation`, `privy_wallet/reconciliation_service`, `bundle_ledger/reconciliation`, etc.) et les statuts `reconciliation_required` en production.

Tant que **N chemins** peuvent créditer ou débiter sans passer par un point unique, la réconciliation reste un **filet après coup**, pas une garantie structurelle.

---

## 2. Décision

**Seule la Settlement Layer est autorisée à écrire dans les tables économiques autoritaires.**

Tout le reste du système — API HTTP, webhooks, cron, services produit (bundle, vault, Lombard), maintenance — **déclenche des intents et des events outbox**, mais **n’écrit jamais directement** dans le ledger.

### Pipeline obligatoire

```
Provider (LI.FI / on-chain / exchange)
    ↓
Transaction Intent (orchestrateur — ADR 001)
    ↓
PostgreSQL Outbox (ADR 002)
    ↓
Worker
    ↓
Settlement Layer  ← seul writer autorisé
    ↓
Ledger (person_wallet_deposits, person_wallet_balances, pe_position_atoms, cost_basis)
    ↓
Final Reconciliation Controller (ADR 003)
    ↓
COMPLETED
```

**Rien d’autre n’écrit dans le ledger.**

---

## 3. Tables sous autorité Settlement Layer

### Tier 1 — Ledger économique (écriture strictement contrôlée)

| Table | Contenu |
| --- | --- |
| `person_wallet_deposits` | Mouvements comptables wallet Privy |
| `person_wallet_balances` | Soldes agrégés wallet |
| `pe_position_atoms` | Scopes PE (trading, vault, bundle, collateral) |
| `cost_basis_executions` | PRU / WAC |

### Tier 2 — Journal produit (écriture via Settlement Layer ou lecture seule)

| Table | Règle |
| --- | --- |
| `bundle_ledger_entries` | Append-only via settlement bundle |
| `pe_ledger_entries` | Déjà contraint PE settlement service |

### Tier 3 — Hors périmètre ADR 004 (lecture / preuve / audit)

| Table | Rôle |
| --- | --- |
| `person_wallet_swaps`, OVT | Records d’exécution produit — pas ledger |
| `transaction_intents`, `transaction_outbox` | Orchestration |
| `raw_onchain_events` | Preuve on-chain indexée |
| `reconciliation_discrepancies` | Écarts détectés — pas d’écriture ledger directe |

---

## 4. Interdictions explicites

Les composants suivants **ne doivent pas** appeler directement les writers ledger / PE atoms :

| Composant | Interdit |
| --- | --- |
| **Routes HTTP** (`/api/swaps/*`, `/api/app/bundle/*`, etc.) | `apply_swap_settlement`, `increment_balance`, `fund_*_from_self_trading`, mutations `pe_position_atoms` |
| **Webhooks** (Privy) | Crédit direct `person_wallet_deposits` sans intent + settlement |
| **Cron / tick DeFi** | Settlement direct ; autorisé : poll outbox → déléguer Settlement Layer |
| **Bundle orchestrator** | `pe_settlement.py`, `bundle_funding.py` en écriture directe |
| **Vault / Lombard services** | `vault_funding.py`, `lombard_funding.py` en écriture directe |
| **Maintenance scripts** | `settle_lifi_swap_idempotently` hors Settlement Layer unifiée |
| **Portal Next.js** | Toute écriture ledger (OVT = record exécution OK ; pas de PE direct) |

### Exceptions temporaires (dual-run Phase 2)

Pendant le POC LI.FI avec `LIFI_INTENT_ORCHESTRATOR_ENABLED=false`, le chemin legacy reste actif — **documenté comme dette**, pas comme doctrine.

Toute exception doit être :
1. Derrière un feature flag nommé
2. Listée dans un registre de dette (`docs/architecture/adr/004-ledger-authority-exceptions.md` — à créer au démarrage Phase 2)
3. Supprimée à l’activation prod de l’orchestrateur pour le produit concerné

### Exceptions permanentes (hors flux transactionnel)

| Cas | Justification |
| --- | --- |
| `financial_reset` (env non-prod) | Opération admin destructive, hors prod |
| `correction_apply` (admin, dry-run default) | Correction manuelle validée ops — passe par Settlement Layer en Phase 5+ |
| Migrations / backfill one-shot | Scripts ops avec review explicite, pas chemin runtime |

---

## 5. Settlement Layer — interface canonique

### Point d’entrée unique

```python
# Interface cible — seul module exportant des writers ledger
settle_transaction_intent_idempotently(db, intent_id) -> SettlementResult
```

### Responsabilités

1. **Router** vers l’implémentation produit selon `intent.product_type`
2. **Écrire atomiquement** toutes les mutations Tier 1 pour cet intent
3. **Idempotence** par `intent_id` + clés métier existantes
4. **Journaliser** via `transaction_trace_events` (LEDGER_POSTED, etc.)
5. **Ne jamais** transitionner vers COMPLETED (réservé au Controller — ADR 003)

### Implémentations produit (internes à la Settlement Layer)

| product_type | Module interne (existant → à encapsuler) |
| --- | --- |
| `lifi_swap` | `settle_lifi_swap_idempotently` / `apply_swap_settlement` |
| `bundle_invest` / `bundle_withdraw` | `pe_settlement.py`, `bundle_funding.py` |
| `morpho_earn` / `ledgity_vault` | `vault_funding.py` |
| `lombard_borrow` | `lombard_funding.py` |
| `observed_external_deposit` | Webhook Privy → intent technique → settlement (pas crédit direct) |
| `privy_deposit` | Parcours webapp explicite futur (initié utilisateur) — distinct du webhook |

### Règle débit / crédit

> Aucune transaction ne crédite sans débit correspondant (ou inversement), dans la même invocation `settle_transaction_intent_idempotently`, **sauf** dépôt externe observé (`observed_external_deposit`) où la preuve provider (webhook + on-chain) précède l’écriture ledger.

---

## 6. Cas particulier — dépôt crypto entrant (webhook Privy)

### Problème

Un dépôt crypto peut arriver **sans action utilisateur préalable**. C’est une exception naturelle au modèle « user action → intent », mais **pas** une exception à la Settlement Layer.

**Comportement actuel** (`webhook_service.py`) :

1. Vérifie signature Svix
2. **Écrit directement** `person_wallet_deposits` + `increment_balance`
3. Classifie ensuite en best-effort via `classify_observed_external_privy_deposit` (metadata, pas intent orchestrateur)

**Risques** :

- Contournement du pipeline intent → outbox → worker → settlement → reconciliation
- Crédit orphelin ou jambe partielle quand le dépôt correspond à la destination d’un swap LI.FI `SUBMITTED`
- Double crédit si webhook rejoué hors idempotence stricte
- Écart ledger / UI sans gate `COMPLETED`

### Doctrine cible

> **Même un dépôt externe observé passe par un intent technique** — le webhook est un **producteur d’events**, pas un **écrivain ledger**.

```
Privy webhook
  → verify webhook signature (Svix)
  → detect wallet / person / asset / amount / chain / tx_hash / log_index
  → create technical intent observed_external_deposit
  → insert transaction_outbox event=deposit.observed (même TX DB)
  → worker processes event
  → settlement layer crédite ledger idempotemment
  → final reconciliation controller
  → COMPLETED
```

### Rôle du webhook (cible)

Le webhook **ne doit plus** écrire `person_wallet_deposits` / `person_wallet_balances` à terme.

Il peut **uniquement** (dans la même transaction DB) :

| Action | Table / artefact |
| --- | --- |
| Persister l’événement brut | `privy_webhook_events` (existant) |
| Créer ou upsert intent technique | `transaction_intents` — `product_type=observed_external_deposit` |
| Enqueue traitement | `transaction_outbox` — `event_type=deposit.observed` |

**Interdit** : `create(deposit)`, `increment_balance`, toute mutation Tier 1.

### Intent technique `observed_external_deposit`

| Champ | Valeur |
| --- | --- |
| `product_type` | `observed_external_deposit` |
| `operation_type` | `deposit` |
| `requested_action` | `deposit_observed` |
| `initiated_by` | `external` (metadata) — pas d’action portail |
| `idempotency_key` | `observed_deposit:{chain_id}:{tx_hash}:{log_index}:{asset}:{wallet_address}` |
| `linked_table` | `privy_webhook_events` ou `person_wallet_deposits` (post-settlement) |
| `correlation_id` | UUID propagé webhook → outbox → trace |

**Note legacy** : le code Phase 7 utilise `PRIVY_DEPOSIT` + metadata `observed_external_deposit: true` (`privy_deposit_intent_sync.py`). La cible unifie sous `product_type=observed_external_deposit` pour l’orchestrateur.

### Idempotence obligatoire

Clé canonique :

```
chain_id + tx_hash + log_index + asset + wallet_address
```

- Webhook rejoué → upsert intent + outbox noop ou event déjà `processed`
- Un seul crédit ledger par clé, quelle que soit la source (webhook, indexer, maintenance)

### Règle 0 — Intent existant d’abord (règle métier la plus importante S6)

Avant de créer un intent `observed_external_deposit`, le webhook doit répondre :

> **Est-ce un événement appartenant déjà à un intent existant ?**

Ordre de résolution :

1. Chercher intent swap LI.FI `SUBMITTED` / `ONCHAIN_PENDING` avec même `tx_hash` + `to_asset` + wallet
2. Chercher intent vault / bundle en attente sur même `tx_hash` ou wallet+asset
3. **Seulement si aucun match** → créer intent technique `observed_external_deposit`

Le webhook est un **détecteur d’événement**, pas un **acteur économique**. C’est ce qui a produit historiquement les crédits orphelins LI.FI.

### Règle 1 — Dépôt lié à un swap LI.FI en cours

Si le dépôt correspond à la **destination attendue** d’un swap LI.FI déjà `SUBMITTED` / `ONCHAIN_PENDING` (même `tx_hash`, asset `to_asset`, wallet signing) :

| Action | Détail |
| --- | --- |
| **Ne pas** créer un dépôt externe indépendant | Pas d’intent `observed_external_deposit` séparé créditant seul |
| **Lier** l’événement à l’intent swap existant | `metadata.linked_swap_intent_id` ou matching par `tx_hash` |
| **Laisser** le settlement swap | `settle_lifi_swap_idempotently` crée ou relie la jambe crédit |
| Outbox | `deposit.observed` → routage vers `intent.settle` du swap, pas nouveau crédit standalone |

C’est le cas historique « crédit webhook sans débit swap » — la cause principale des settlements partiels LI.FI.

### Règle 2 — Dépôt réellement externe

Si aucun intent swap (ou vault / bundle) en attente sur ce `tx_hash` + asset + wallet :

1. Worker traite `deposit.observed`
2. Settlement Layer crée crédit `person_wallet_deposits` + `increment_balance`
3. Controller vérifie on-chain = ledger = UI
4. Intent → `COMPLETED`

### Règle 3 — Chaîne hors scope custody

Si `chain_id` hors scope custody actuelle (ex. Ethereum alors que custody opérationnelle = Base) :

| Action | Détail |
| --- | --- |
| Créer intent | `status=OUT_OF_SCOPE` ou `informational` |
| Ledger custody Base | **Pas d’écriture** |
| Compte utilisateur | **Pas de blocage** |
| Outbox | Event `processed` avec rapport informational |
| UI | Notification optionnelle « dépôt observé hors scope » |

### Règle 4 — Wallet inconnu

Si `to_address` ne correspond à aucun wallet actif :

| Action | Détail |
| --- | --- |
| Pas d’intent | Ou intent `status=FAILED` avec `reason=unknown_wallet` |
| Outbox | `dead_letter` ou file `manual_review` |
| Alerte ops | Revue manuelle — pas de crédit automatique |

### Reconciliation Controller (dépôt observé)

Checks spécifiques ADR 003 :

| Check | Assertion |
| --- | --- |
| `onchain_tx_exists` | Receipt / indexer confirme tx |
| `wallet_ownership` | Wallet destinataire ∈ `person_id` de l’intent |
| `amount_asset_chain` | Montant, asset, chain = webhook = on-chain |
| `ledger_credit_unique` | Une seule jambe crédit pour la clé idempotence |
| `ui_balance_updated` | `available` / balance API cohérent post-COMPLETED |
| `no_swap_double_credit` | Si lié swap : pas de crédit standalone + jambe swap |

### Mapping événements outbox

| event_type | Déclencheur | Handler |
| --- | --- | --- |
| `deposit.observed` | Webhook Privy inbound | Match swap → lien ; sinon settlement crédit externe |

### Phase de livraison

| Phase | Périmètre |
| --- | --- |
| **Phase 2 POC** (LI.FI) | Documenter + tests spécifiés ; **pas** de refactor webhook |
| **Phase 2b** | Webhook Privy → intent technique + outbox ; flag `PRIVY_DEPOSIT_ORCHESTRATOR_ENABLED` |
| **Phase 3** | LI.FI swap matching (règle 1) intégré au settlement |

**Code existant à réutiliser** : `privy_deposit_intent_sync.py` (`observed_external_deposit`, classification), `webhook_verifier.py` (Svix).

---

## 7. Enforcement (progressif)

### Phase 2 POC (LI.FI)

- Settlement LI.FI standalone routé via `settle_transaction_intent_idempotently` uniquement quand flag ON
- Commentaire `@ledger-authority` sur les call sites legacy restants
- Test : « API submit n’appelle pas `apply_swap_settlement` quand orchestrateur ON »
- Webhook deposit : **hors scope implémentation** ; doctrine §6 + tests spécifiés en Phase 2b

### Phase 2b (webhook Privy deposit)

- Flag `PRIVY_DEPOSIT_ORCHESTRATOR_ENABLED` (défaut `false`)
- Webhook : intent `observed_external_deposit` + outbox `deposit.observed` — **pas** d’écriture ledger directe
- Settlement Layer : seul writer crédit
- Matching swap LI.FI (règle 1) avant crédit standalone
- Voir checklist : `docs/architecture/PHASE2_POC_LIFI_STANDALONE_SWAP.md` § Phase 2b

### Phase 3+

- Linter / test d’architecture : grep CI interdisant `increment_balance` hors `settlement/`
- Module `services/settlement/` — seul package autorisé à importer writers ledger
- Revue PR : checklist ADR 004

### Phase 5 (maturité)

- Wrapper repository ledger avec assertion `caller=settlement_layer`
- Métrique : `ledger_writes_unauthorized_total` (doit rester à 0)

---

## 8. Relation avec les autres ADR

| ADR | Rôle | Lien ADR 004 |
| --- | --- | --- |
| 001 Intent Orchestrator | Pilote le cycle de vie | Intent déclenche settlement, n’écrit pas ledger |
| 002 Outbox | Transport fiable | Worker appelle Settlement Layer, pas l’inverse |
| 003 Reconciliation Controller | Gate COMPLETED | Vérifie que seule la Settlement Layer a écrit |
| **004 Ledger Authority** | **Cœur comptable** | **Définit qui écrit quoi** |

Sans ADR 004, les ADR 001–003 améliorent l’orchestration mais **ne ferment pas** la porte aux écritures parallèles — la source principale des écarts custody reste ouverte.

---

## 9. Conséquences

### Positives

- Un seul chemin d’écriture économique → écarts structurellement plus rares
- Réconciliation devient validation, pas rattrapage permanent
- Audit compliance simplifié (« qui a écrit ce mouvement ? » → `intent_id` → Settlement Layer)
- Alignement architecture « petit Revolut »

### Négatives / coûts

- Refactoring large des call sites existants (bundle, vault, webhook)
- Latence légère (settlement async via worker vs synchrone HTTP)
- Dual-run temporaire avec exceptions documentées

### Risques mitigés

| Risque | Mitigation |
| --- | --- |
| Régression bundle/vault | Hors scope POC ; flags par produit |
| Webhook downtime | Intent + outbox ; retry settlement |
| Ops perd habitude scripts maintenance | Scripts appellent Settlement Layer, pas ledger direct |

---

## 10. Critères d’acceptation ADR 004

- [ ] `settle_transaction_intent_idempotently` documenté comme **seul writer runtime** (orchestrateur ON)
- [ ] Registre exceptions dual-run créé avant merge Phase 2
- [ ] LI.FI POC : `lifi_execute_service` ne appelle plus `apply_swap_settlement` si flag ON
- [ ] Phase 2b : webhook Privy → `observed_external_deposit` + outbox (pas d’écriture ledger directe)
- [ ] Phase 2b : matching swap LI.FI — pas de double crédit webhook + jambe swap
- [ ] Plan Phase 3 : chaînes hors scope + wallet inconnu (dead-letter / manual review)
- [ ] Plan Phase 5 : test CI « unauthorized ledger write »
- [ ] Revue équipe : ADR 004 accepté avant S3 (Outbox Worker) du POC

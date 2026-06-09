# PRD — Bundle Rebalancing Engine V3

| Champ | Valeur |
| --- | --- |
| **Statut** | Draft CTO · reset conceptuel |
| **Date** | 2026-06-09 |
| **Contexte** | Incident bundle concurrent (PR #62–#64) · audit `10d688bb` · [`GO_BUNDLE_RECOVERY_V2_ARCHITECTURE_AUDIT.md`](GO_BUNDLE_RECOVERY_V2_ARCHITECTURE_AUDIT.md) |
| **Objectif** | Faire du **portefeuille** la seule vérité métier ; les batches deviennent des **rapports d’exécution** |

---

## 1. Problème constaté

Deux moteurs coexistent et se contredisent :

| # | Moteur | Source de vérité | Symptômes |
| --- | --- | --- | --- |
| 1 | **Transactionnel** | batch · legs · resume · pending · submitted · expired | `active-lock`, `ambiguous`, ghost legs, « Reprendre » sur batch mort |
| 2 | **Portefeuille** | allocation cible · cash résiduel · drift · rebalance | `preview_rebalance`, `reconciliation_required`, PE atoms |

**Exemple prod (`10d688bb`)** : portefeuille ~95 % aligné (5 actifs + 29,87 USDC) mais batch 100 % « pas OK » → UI « Reprendre l’investissement » alors que `preview_rebalance` propose BTC+ETH depuis le cash.

Les PR #62–#64 ont **réparé l’incident**. V3 **supprime la catégorie** resume / pending / ghost / partial hidden en changeant la question système :

> Avant : « Comment reprendre ce batch ? »  
> Après : « Quel est l’état réel du portefeuille et comment le remettre à la cible ? »

---

## 2. Vision cible

### 2.1 Parcours client

Le client ne fait **jamais** :

```
Invest → Batch → Resume Batch
```

Le client fait :

```
Portefeuille → Allocation cible → Rebalancing → Portefeuille aligné
```

### 2.2 Principe fondamental

| Vérité absolue | Jamais vérité métier |
| --- | --- |
| Positions PE (spot + cash leg) | batch_id |
| `pe_target_allocations` | swap status historique |
| Drift vs cible | leg AWAITING_SIGNATURE > 2 min |

### 2.3 Rôle des batches (V3)

Un batch est un **artefact d’exécution** — rapport de ce qui s’est passé lors d’un cycle rebalance, pas un workflow vivant :

```json
{
  "batch_id": "uuid",
  "status": "COMPLETED_WITH_RESIDUAL_CASH",
  "cash_remaining_usdc": "29.87",
  "success_legs": 4,
  "failed_legs": 1,
  "execution_result": "partial",
  "trigger": "deposit|withdraw|allocation_change|cron|manual"
}
```

---

## 3. Workflow cible

### 3.1 Dépôt (demain)

```
Deposit
  ↓
Cash leg +XX USDC
  ↓
Schedule Rebalancing (event / cron / immédiat selon policy)
  ↓
Rebalancing Engine V3
  ↓
Portfolio aligned (ou COMPLETED_WITH_RESIDUAL_CASH)
```

### 3.2 Aujourd’hui (à remplacer)

```
Deposit → Fund cash leg → Create batch → Create legs → Resume → …
```

### 3.3 Exécution — ordre strict

```
SELLS (surpondération)
  ↓
attendre confirmations
  ↓
BUYS (sous-pondération + cash)
```

Jamais BUY/SELL entrelacés.

### 3.4 Fin obligatoire

Le moteur **ne laisse jamais** un portefeuille en `AWAITING_SIGNATURE` / `RESUME_REQUIRED` pendant des heures.

Après timeout (`QUOTE_TTL_SECONDS` ou policy dédiée) :

```
batch → TERMINATED (FAILED ou COMPLETED_WITH_RESIDUAL_CASH)
portfolio → source de vérité inchangée
prochain cycle → nouveau plan depuis drift
```

---

## 4. Concept central — Portfolio Drift

### 4.1 Valeur portefeuille et base de poids

```
invested_value_usdc = Σ(spot_qty × price)
cash_value_usdc     = cash leg (entry asset)
portfolio_value_usdc = invested_value_usdc + cash_value_usdc   # NAV total
```

**Décision architecture PR-2** : le drift portefeuille est calculé sur les **actifs investis uniquement** (`weight_basis = invested_assets`). Le cash leg est traité comme une **source de financement du rebalancing** (`cash_funding_source = separate`) et **non** comme une allocation cible implicite.

Prix : même source que rebalance v1 (EUR ou USDC selon config produit).

### 4.2 Par actif cible

Pour chaque ligne `pe_target_allocations` :

| Champ | Formule |
| --- | --- |
| `target_weight` | Config produit (ex. BTC 50 %) |
| `current_weight` | `current_spot_value / invested_value_usdc` |
| `drift_pct` | `current_weight - target_weight` |
| `target_value` | `invested_value_usdc × target_weight` |
| `current_value` | Position spot uniquement |
| `delta_value` | `target_value - current_value` |

### 4.3 Exemple Crypto Majors (pilote prod)

**Cible** : BTC 50 % · ETH 30 % · LINK/AAVE/UNI 6,67 % chacun.

**Réel (audit)** :

| Asset | Poids réel (approx.) | Delta actionnable |
| --- | --- | --- |
| BTC | 53,54 % | vendre ~4 USDC si > seuil |
| ETH | 19,02 % | acheter ~17 USDC |
| LINK | 6,58 % | hold |
| AAVE | 7,26 % | hold |
| UNI | 3,74 % | acheter ~3 USDC |
| USDC (cash) | 29,87 | consommé par buy plan |

`preview_rebalance` prod (post-expire) : BUY BTC ~6,45 + ETH ~16,94 USDC — cohérent avec drift engine, pas avec reprise CBETH.

### 4.4 Seuils

| Paramètre | Valeur V3 proposée | Existant v1 |
| --- | --- | --- |
| `MIN_REBALANCE_DELTA_USDC` | **1** (PRD CTO) | `MIN_TRADE_EUR = 5` |
| `MIN_DRIFT_BPS` | 200 (2 %) — configurable | `MIN_DRIFT_BPS = 200` |
| `MAX_SWAP_ATTEMPTS` | **2** | partiel / ad hoc |
| `QUOTE_TTL_SECONDS` | 120 (resume frais uniquement) | 120 |

Si `|delta_value| < MIN_REBALANCE_DELTA_USDC` → **ignore** (anti-poussière).

---

## 5. États V3

### 5.1 Statuts batch (nouveau modèle)

| Statut | Signification |
| --- | --- |
| `RUNNING` | Cycle rebalance en cours (swaps ouverts < timeout) |
| `COMPLETED` | Drift résorbé dans les seuils |
| `COMPLETED_WITH_RESIDUAL_CASH` | Exécution partielle OK · cash restant < seuil buy global |
| `FAILED` | Échec terminal · pas de resume · prochain cycle repart du portefeuille |

### 5.2 À déprécier (pas supprimer d’un coup — PR-4/5/6)

| Ancien | Remplacement V3 |
| --- | --- |
| `resume_required` | `RUNNING` < TTL ou rebalance auto |
| `partial` (parent intent) | `COMPLETED_WITH_RESIDUAL_CASH` |
| `awaiting_signature` (batch métier) | swap technique < 120 s seulement |
| `active-lock` recoverable | drift + schedule rebalance |
| `ambiguous` (multi-batch) | impossible si 1 cycle RUNNING max / portfolio |

### 5.3 `resume_lifi_invest_batch` — périmètre final

**Conservé uniquement si** :

- `AWAITING_SIGNATURE` **et** `age < QUOTE_TTL_SECONDS` (refresh page utilisateur)

**Sinon** : Recovery V2 → terminal batch + `schedule_rebalance`.

---

## 6. Déclencheurs rebalance

| Événement | Comportement V3 |
| --- | --- |
| **Dépôt** | Cash leg crédité → `schedule_rebalance(portfolio_id, trigger=deposit)` |
| **Retrait** | Après withdraw → rebalance pour réaligner le reste |
| **Allocation modifiée** | Majors v2 → rebalance forcé |
| **Cron** | daily / weekly / monthly (config produit) |
| **Manuel** | Bouton UI « Rééquilibrer le portefeuille » |
| **Recovery V2** | Batch stale terminal → rebalance depuis état PE |

---

## 7. État des lieux code (réutilisation)

| Composant | Fichier | V3 |
| --- | --- | --- |
| Rebalance preview/execute v1 | `bundles/rebalance.py` | **Étendre** → PR-1/2/3 |
| Event-driven planner | `event_driven/rebalance_planner.py` | Aligner sur drift normalisé |
| Reconciliation read-model | `bundle_reconciliation_read_model.py` | Source actions V3 |
| Invest orchestrator + resume | `orchestrator.py` | **Réduire** → PR-4/5 |
| Invest lock / active-lock | `bundle_invest_lock.py` | **Remplacer** sémantique → PR-4 |
| UI allocation panel | `PortalBundleAllocation*.tsx` | **Migrer** → PR-6 |
| Expired requote #64 | `requote_expired_invest_legs` | Transition → rebalance trigger |

**Ne pas réécrire from scratch** : extraire `_compute_plan()` en **Portfolio Drift Engine** nommé, puis Planner/Executor autour.

---

## 8. Découpage — 6 PR

Ordre strict. Chaque PR : tests pytest + audit ECS read-only sur compte pilote si touché prod.

---

### PR-1 — Portfolio Drift Engine

**Prompt implémentation**

> Create a Portfolio Drift Engine for Bundle portfolios. Calculate target allocation, current allocation, drift percentage, target value, current value and delta value for every asset. Portfolio market value includes spot assets and cash leg. Return a normalized `BundleRebalancePlan` object without executing swaps.

**Scope**

- Nouveau module : `bundles/drift_engine.py` (ou refactor extrait de `rebalance.py`)
- Type `BundleDriftSnapshot` + `BundleRebalancePlan` (preview-only)
- Entrées : `portfolio_id`, `client_id`, prices snapshot
- Sortie normalisée JSON stable (pour API + UI + tests golden)

**Hors scope**

- LI.FI · swaps · batch write

**Fichiers touchés**

- `rebalance.py` — déléguer calcul à drift engine
- `test_bundle_drift_engine.py` — cas Crypto Majors pilote (poids réels audit)

**Critères d’acceptation**

- [x] `portfolio_value` = spot + cash · `invested_value` = spot seul · `weight_basis = invested_assets`
- [ ] 5 assets + cash sur pilote · deltas cohérents avec audit manuel (base investie)
- [ ] Zéro side-effect DB
- [ ] API `GET .../rebalance/preview` utilise le nouveau plan (régression 0 sur shape public)

---

### PR-2 — Rebalancing Planner

**Prompt**

> Create a Bundle Rebalancing Planner. Generate `sell_plan` and `buy_plan` from the drift engine (`weight_basis = invested_assets`). Cash leg = separate funding source. Ignore deltas below `MIN_REBALANCE_DELTA_USDC`. Execute sells first, then buys. Planner must be deterministic and idempotent.

**Scope**

- `bundles/rebalance_planner.py`
- Paramètres env : `MIN_REBALANCE_DELTA_USDC=1`, conserver `MIN_DRIFT_BPS`
- Drift sur actifs investis · cash = budget d’achat
- Ventes uniquement si surpondération **et** cash insuffisant pour couvrir les achats requis
- Ordre : sells triés par delta desc · buys par delta desc · achats financés par `available_cash_usdc`
- Idempotence : même snapshot prix → même `plan_hash`

**Critères d’acceptation**

- [ ] Pilote : drift BTC sell / ETH buy · plan = buy ETH+UNI depuis cash, **sans** vendre BTC
- [ ] Deltas < 1 USDC ignorés
- [ ] `sell_plan` vide si que des buys (cas cash residual 29,87)
- [ ] Tests déterministes (seed prices)

---

### PR-3 — Rebalancing Executor

**Prompt**

> Implement Bundle Rebalancing Executor. Execute sell_plan then buy_plan through LI.FI. Add retry policy `MAX_SWAP_ATTEMPTS=2`. Executor must never leave a portfolio in a waiting state after timeout.

**Scope**

- `bundles/rebalance_executor.py`
- Phases : SELL batch → gate confirmations → BUY batch
- Retry par leg (2 max) · pas de resume cross-batch
- Timeout : auto-expire swaps stale (réutiliser `expire_stale_swap_sessions`) · batch → `FAILED` ou `COMPLETED_WITH_RESIDUAL_CASH`
- Un seul `RUNNING` rebalance batch / portfolio (lock léger)

**Critères d’acceptation**

- [ ] Sell-then-buy respecté en prod mock + local DB
- [ ] Après timeout simulé : aucun `active-lock` recoverable
- [ ] `MAX_SWAP_ATTEMPTS=2` testé
- [ ] Pas de régression PE/CB sur chemin happy path

---

### PR-4 — Batch Lifecycle Simplification

**Prompt**

> Refactor Bundle Batch lifecycle. Batches are execution reports only. Remove workflow semantics from old resume-based architecture. Introduce statuses RUNNING, COMPLETED, COMPLETED_WITH_RESIDUAL_CASH and FAILED.

**Scope**

- Enum statuts V3 sur parent intent / metadata rebalance
- `peek_bundle_invest_lock_state` : ne plus promouvoir `resume` si drift résoluble par rebalance
- `BLOCKING_BUNDLE_SWAP_STATUSES` : exclure `SUBMITTED` > N min si portfolio cohérent (policy)
- Documentation migration anciens statuts → mapping V3

**Critères d’acceptation**

- [ ] `10d688bb`-like : plus de `resume_available=true` si reconciliation = cash residual only
- [ ] Batch terminal écrit rapport JSON (success/failed legs)
- [ ] Tests régression `bundle_invest_lock_orphan_fix` adaptés

---

### PR-5 — Recovery V2

**Prompt**

> Implement Bundle Recovery V2. Any batch older than QUOTE_TTL_SECONDS or with expired swaps must be marked terminal. Recompute portfolio state and create a fresh rebalancing plan instead of resuming historical swaps.

**Scope**

- `bundles/recovery_v2.py` + hook cron / post-login / pre-rebalance
- Règles : age > TTL · expired swaps · portfolio `all_target_assets_in_spot` → terminal + `schedule_rebalance`
- Pas de cleanup DB destructif parents (metadata terminal seulement)
- Remplace chemin principal `requote_expired_invest_legs` pour batches stale

**Critères d’acceptation**

- [ ] Pilote post-incident : recovery déclenche plan frais, pas resume
- [ ] `stuck_count` KPI basé sur **RUNNING** réel, pas ghosts EXPIRED
- [ ] Audit ECS : `ambiguous=0`, `signable=0`, cash requotable via rebalance

---

### PR-6 — UI Migration

**Prompt**

> Replace Resume Investment UX with Portfolio Rebalance UX. UI must display portfolio drift, residual cash, target allocation and Rebalance Portfolio action. Remove dependency on historical batch recovery states.

**Scope**

- `PortalBundleAllocationReadOnlyPanel` / `ActionsPanel`
- Supprimer CTA principal « Reprendre » sauf session < 120 s
- Afficher : drift table · cash résiduel · « Rééquilibrer le portefeuille »
- API : consommer drift preview PR-1

**Critères d’acceptation**

- [ ] Pilote : plus de « Reprendre » sur `10d688bb`-like
- [ ] Prévisualisation plan avant exécution
- [ ] Parcours E2E mock : deposit → rebalance → completed

---

## 9. Matrice de migration incident → V3

| État pilote post-expire | Action V3 (pas resume) |
| --- | --- |
| Crypto Majors · cash 29,87 · CBETH SUBMITTED | Attendre tx · puis **rebalance** (PR-3) |
| Two Crypto Kings · cash 30,90 · active-lock none | **Rebalance** immédiat |
| Parents `partial` historiques | PR-5 terminal + drift |
| Global Lock tests | **Après** PR-5 · `stuck_count` sur RUNNING réel |

---

## 10. Risques et garde-fous

| Risque | Mitigation |
| --- | --- |
| Double rebalance concurrent | 1 RUNNING / portfolio + product lock existant |
| Régression invest initial (fund-first) | Garder fund cash leg · remplacer seulement allocation legs par schedule rebalance |
| LI.FI quote expiry | TTL 120 s · max 2 attempts · terminal batch |
| KPI `stuck_count` faux positifs | Redéfinir KPI = portfolios avec `RUNNING` > timeout |
| Big-bang UI | PR-6 feature flag `BUNDLE_V3_REBALANCE_UI` |

---

## 11. Definition of Done (programme V3)

- [ ] Aucun portfolio pilote en `ambiguous` / `resume` pour batch > 2 min
- [ ] Dépôt → rebalance sans création batch invest « vivant »
- [ ] `preview_rebalance` = même moteur que execute (drift engine)
- [ ] Documentation ops : plus de runbook « reprendre batch incident »
- [ ] Global Lock activation autorisée après audit `RUNNING=0` réel

---

## 12. Références

| Document | Lien |
| --- | --- |
| Audit `10d688bb` | [`GO_BUNDLE_RECOVERY_V2_ARCHITECTURE_AUDIT.md`](GO_BUNDLE_RECOVERY_V2_ARCHITECTURE_AUDIT.md) |
| Ghost legs + maintenance | [`GO_BUNDLE_GHOST_LEGS_CLASSIFICATION_REPORT.md`](GO_BUNDLE_GHOST_LEGS_CLASSIFICATION_REPORT.md) |
| Rebalance v1 technique | `services/arquantix/BUNDLE_REBALANCE_ENGINE_REPORT.md` |
| Code drift actuel | `services/arquantix/api/services/portfolio_engine/bundles/rebalance.py` |

---

## 13. Prochaine action recommandée

**Démarrer PR-1** (Portfolio Drift Engine) — read-only, zéro risque prod, débloque PR-2/6 en parallèle partiel.

Ensuite enchaîner PR-2 → PR-3 sur branche pilote avant de toucher lifecycle (PR-4/5).

---

## PR-1 implementation notes

| Champ | Valeur |
| --- | --- |
| **Statut** | **Implémenté** (read-only) |
| **Module** | `services/arquantix/api/services/portfolio_engine/bundles/drift_engine.py` |
| **Tests** | `services/arquantix/api/tests/test_bundle_drift_engine.py` — **8 passed** |
| **ECS audit** | `./scripts/arquantix-ecs-bundle-drift-engine-audit.sh` |

### Livrables

- `compute_bundle_drift_snapshot()` — snapshot JSON stable + `snapshot_hash` déterministe
- Types : `BundleDriftAsset`, `BundleDriftSnapshot`, `BundleDriftPlan`, `BundleDriftPriceSnapshot`
- Denomination **USDC** (entry asset) via même source prix que `rebalance.py` (`ExchangeService._resolve_price` EUR → conversion entry)
- `non_target_assets` avec `action_hint: sell_candidate`
- Aucune lecture batch / swap / leg historique

### Intégration minimale

`BundleRebalanceOrchestrator.preview_rebalance()` attache un champ optionnel **`drift_snapshot`** (comportement buy/sell inchangé).

### Critères d’acceptation PR-1

| Critère | Statut |
| --- | --- |
| Tests verts | ✓ 8/8 |
| Zéro écriture DB | ✓ test `test_no_side_effects_pe_cb_swaps` |
| Snapshot exploitable PR-2 | ✓ `action_hint`, `delta_value_usdc`, `target_weight_bps` |
| Pas de dépendance batches | ✓ |
| Runtime risqué | ✓ champ optionnel preview seulement |

### Prochaine étape

**PR-3** — Rebalancing Executor : exécuter `drift_rebalance_plan` via LI.FI (sell puis buy).

---

## PR-2 implementation notes

| Champ | Valeur |
| --- | --- |
| **Statut** | **Implémenté** (read-only planner) |
| **Module drift** | `drift_engine.py` — `weight_basis`, `invested_value_usdc` |
| **Module planner** | `rebalance_planner.py` — `plan_bundle_rebalance_from_drift()` |
| **Tests** | `test_bundle_rebalance_planner.py` + drift tests mis à jour |
| **Preview** | `preview_rebalance()` attache `drift_rebalance_plan` |

### Règle cash résiduel

Si `total_buy_need ≤ available_cash_usdc` → `sell_plan` vide (pas de trim BTC quand le cash finance les achats).

---

## PR-3 implementation notes

| Champ | Valeur |
| --- | --- |
| **Statut** | **Implémenté** (executor contrôlé) |
| **Module** | `rebalance_executor.py` — `execute_v3_bundle_rebalance()` |
| **Tests** | `test_bundle_rebalance_executor.py` — **15 passed** (29 total drift+planner+executor) |
| **API** | `POST .../rebalance/v3/execute` si `BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED=true` |
| **Legacy** | `POST .../rebalance` inchangé (v1 `_compute_plan`) |

### Comportement

- Entrée : `drift_rebalance_plan` + `plan_hash` + `trigger`
- Un seul `RUNNING` / portfolio (audit `pe_audit_events`)
- Sell phase → gate → buy phase
- `MAX_SWAP_ATTEMPTS=2` · pending → `expired` en fin de cycle · `resume_required=false`
- `MAX_EXECUTION_AGE_MINUTES=30` (défaut) · `terminalize_stale_v3_rebalance_execution()` — jamais RUNNING indéfini
- Idempotence : `plan_hash` · reprise crash (`ACTION_V3_PROGRESS`) · même `execution_id` / `batch_id`
- Buy-only échec quote (cash résiduel) → `COMPLETED_WITH_RESIDUAL_CASH` (pas `FAILED` global)
- Statuts terminaux : `COMPLETED` · `COMPLETED_WITH_RESIDUAL_CASH` · `FAILED` · `NO_ACTION`
- Pas de `resume_lifi_invest_batch` · pas de Global Lock · pas de B4b bridge

### Garanties review CTO (PR #66)

| # | Garantie | Test |
| --- | --- | --- |
| 1 | Timeout terminal (`MAX_EXECUTION_AGE_MINUTES`) | `test_stale_running_terminalized_not_indefinite` |
| 2 | Idempotence après crash (même execution, pas de swaps dupliqués) | `test_crash_resume_same_execution_no_duplicate_swaps` |
| 3 | Leg expiré buy-only + cash → `COMPLETED_WITH_RESIDUAL_CASH` | `test_expired_eth_only_residual_cash_not_failed` |
| 4 | Triple POST execute → 1 batch / 1 set swaps | `test_triple_execute_same_plan_one_batch` |

### Post-merge

1. Deploy avec flag **OFF** par défaut
2. Audit ECS drift/planner (déjà GO_PR2)
3. Test contrôlé mock LI.FI puis buy-only pilote (Kings ou Majors)

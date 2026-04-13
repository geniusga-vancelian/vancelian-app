# Phase 3 — Transferts / Portfolio Engine : rapport d’intégration (auth continue)

## Executive Summary

Les endpoints à **effet monétaire direct** (transfert interne custody, ordres, trades, règlements, exécutions d’ordres, orchestrateur de rebalance) sont protégés par **`Depends(require_continuous_auth_for_action("wallet_transfer"))`** en complément du **RBAC** existant **`require_admin_or_ops()`** (où il était déjà présent ou ajouté pour les exécutions).

Les hooks **`record_sensitive_action_completed` / `record_sensitive_action_failed`** couvrent le **transfert interne** (tous les chemins métier contrôlés), les **trades** / **orders** / **settlements** / **orchestration**, et les **exécutions** (hook **completed** explicite sur **create** et **fill** ; les autres transitions d’exécution sont protégées par **Depends** sans hook SIEM détaillé pour limiter le bruit).

La clé **`internal_transfer_low`** du **sensitive_action_map** n’est **pas** utilisée : aucune règle métier de seuil / même propriétaire n’était branchée de façon fiable dans le code.

---

## Inventaire (candidats audités)

| Méthode | Chemin | Router | Effet métier | Classification | Protéger ? | `action_key` | Raison |
|--------|--------|--------|----------------|----------------|------------|--------------|--------|
| POST | `/api/internal-transfer` | `custody/router.py` | Débit client → crédit settlement, ledger | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Mouvement interne de fonds |
| POST | `/api/portfolio-engine/trades` | `trades/router.py` | Enregistrement d’un trade | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Effet transactionnel |
| POST | `/api/portfolio-engine/orders` | `orders/router.py` | Création d’ordre | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Engagement d’exécution |
| POST | `/api/portfolio-engine/orders/{id}/accept` | idem | Acceptation ordre | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Pipeline vers exécution |
| POST | `/api/portfolio-engine/orders/{id}/reject` | idem | Rejet | NON_MONETARY_STATE_CHANGE / contrôle | Oui | `wallet_transfer` | Surcharge de sécurité (ambiguïté → protéger) |
| POST | `/api/portfolio-engine/orders/{id}/cancel` | idem | Annulation | NON_MONETARY_STATE_CHANGE / contrôle | Oui | `wallet_transfer` | Idem |
| POST | `/api/portfolio-engine/settlements` | `settlement/router.py` | Création instruction | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Settlement |
| POST | `/api/portfolio-engine/settlements/{id}/schedule` | idem | Planification | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Chaîne settlement |
| POST | `/api/portfolio-engine/settlements/{id}/start` | idem | Démarrage | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Idem |
| POST | `/api/portfolio-engine/settlements/{id}/settle` | idem | Règlement effectif | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Mouvement comptable |
| POST | `/api/portfolio-engine/settlements/{id}/fail` | idem | Échec instruction | NON_MONETARY_STATE_CHANGE | Oui | `wallet_transfer` | Surcharge sécurité |
| POST | `/api/portfolio-engine/portfolios/{id}/orchestrate` | `orchestrator/router.py` | Cycle rebalance / ordres | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Orchestration positions |
| POST | `/api/portfolio-engine/executions` (et transitions) | `execution/router.py` | Instructions + fill, etc. | MONEY_MOVEMENT_COMMIT | Oui | `wallet_transfer` | Exécution + fill = effet portefeuille ; RBAC ajouté |
| GET | `/api/portfolio-engine/**` (lecture) | divers | Lecture | READ_ONLY | Non | — | Hors scope friction continue |
| POST | `/api/portfolio-engine/rebalance-preview` | `rebalance_preview/router.py` | Plan / preview persisté | PREPARE_ONLY | Non | — | Non traité comme commit de fonds ici |
| POST | `/api/portfolio-engine/.../valuation/snapshot` | `valuations/router.py` | Snapshot valorisation | NON_MONETARY_STATE_CHANGE | Non | — | Pas de mouvement de fonds |
| POST | `/api/portfolio-engine/.../rebalance-plan` (drift) | `drift/router.py` | Plan rebalance | PREPARE_ONLY | Non | — | Préparation |
| POST | `/api/portfolio-engine/subscriptions/.../provision` | `subscriptions/router.py` | Provisionnement | LOW_RISK_INTERNAL_TRANSFER / préparation | Non* | — | *Non couvert dans cette phase pour limiter le diff ; réévaluation possible |
| POST | positions / wallets / allocations / ledger-accounts | divers | CRUD structure | souvent NON_MONETARY ou PREPARE | Non* | — | *Non couverts : pas de mouvement de trésorerie explicite via ces POST dans l’audit ciblé |

---

## Fichiers modifiés

- `api/services/custody/router.py` — `POST /api/internal-transfer` : `wallet_transfer` + hooks
- `api/services/portfolio_engine/trades/router.py`
- `api/services/portfolio_engine/orders/router.py`
- `api/services/portfolio_engine/settlement/router.py`
- `api/services/portfolio_engine/orchestrator/router.py`
- `api/services/portfolio_engine/execution/router.py` — `require_admin_or_ops` + `wallet_transfer` sur tous les POST ; hooks sur `create` + `fill`
- `api/tests/test_internal_transfer.py` — JWT + `make_linked_client` (aligné Phase 2)
- `api/tests/test_wallet_transfer_sensitive_auth.py` — **nouveau**
- `PHASE_FINAL_TRANSFERS_PE_INTEGRATION_REPORT.md` — ce document

---

## Endpoints protégés (`action_key` = `wallet_transfer`)

- `POST /api/internal-transfer`
- `POST /api/portfolio-engine/trades`
- `POST /api/portfolio-engine/orders` (+ `/accept`, `/reject`, `/cancel`)
- `POST /api/portfolio-engine/settlements` (+ `schedule`, `start`, `settle`, `fail`)
- `POST /api/portfolio-engine/portfolios/{portfolio_id}/orchestrate`
- `POST /api/portfolio-engine/executions` (+ `send`, `acknowledge`, `fill`, `reject`, `expire`, `cancel`, `fail`)

---

## Endpoints volontairement non protégés (résumé)

- **Lecture** PE et custody (hors scope).
- **Preview / plan** rebalance, **snapshot** de valorisation : pas classés comme **commit** de fonds dans cette phase.
- **Subscriptions provision**, **CRUD** wallets/positions/allocations : laissés hors diff minimal ; **réaudit** si le produit les rattache à des flux cash réels.

---

## Tests ajoutés / mis à jour

- **`tests/test_internal_transfer.py`** : en-têtes Bearer + ordre de setup (client PE avant `commit` custody).
- **`tests/test_wallet_transfer_sensitive_auth.py`** : réponses structurées **401** / **403** (mock `evaluate_request_security_context`), hooks **completed** / **failed** sur transfert interne, smoke **403** sur `POST /api/portfolio-engine/trades` avec corps vide (Depends avant validation).

---

## Ambiguïtés restantes

- **Orchestration** avec **Idempotency-Key** rejoué : pas d’émission de hook SIEM sur la réponse rejouée (réponse courte-circuitée).
- **Exécutions** : transitions autres que **create** / **fill** sans hook **failed** détaillé (exceptions génériques + `rollback`).
- **Provisionnement** souscription / bundles : pourrait mériter `wallet_transfer` ou une clé dédiée selon la politique produit.

---

## Recommandation — phase suivante

- Cartographier **exchange** / **app** (`/api/app/orders`, etc.) si des flux cash sortent du PE admin.
- Introduire **`internal_transfer_low`** uniquement si une **règle de montant** / **même titulaire** est **codée** et testée.

---

## Synthèse livraison

| Élément | Détail |
|--------|--------|
| **Fichiers changés** | Voir section « Fichiers modifiés » |
| **Routes protégées** | Toutes listées ci‑dessus avec **`wallet_transfer`** |
| **Tests** | `test_internal_transfer` + `test_wallet_transfer_sensitive_auth` (15 tests au passage local) |
| **Risques résiduels** | Sessions de test **nested transaction** vs `db.commit()` dans les routes ; clients **internes** appelant **executions** sans JWT ni en-têtes acteur → **cassés** (comportement voulu : sécurisation). |

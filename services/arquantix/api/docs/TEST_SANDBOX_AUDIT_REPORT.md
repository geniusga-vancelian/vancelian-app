# Test Sandbox Audit Report

## 1. Executive Summary

**Problème principal** : les tests backend pytest écrivent de façon **permanente dans la base de données locale réelle** (pas d'isolation transactionnelle). Chaque exécution de la suite de tests crée ~15 providers `Bank-{uuid}`, ~15 clients `exchange-{uuid}@example.com` et ~15 comptes `client_deposit_account` qui **ne sont jamais nettoyés**.

**Niveau de pollution actuel** :
- 64 custody providers (63 `Bank-{uuid}` + 1 `Modulr`)
- 64 pe_clients (63 `exchange-*@example.com` / `cash-e2e-*@example.com` + le current)
- 64 client_deposit_account (63 de test + 1 réel)
- 1 company_settlement_account (correct)
- 10 crypto_custody_accounts (correct, via bootstrap)

**Cause principale** : les test helpers appellent l'API via `TestClient` sans override de `get_db`. L'app utilise sa `SessionLocal` standard → écritures directes dans la DB locale. La fixture `db` avec rollback existe dans `conftest.py` mais n'est **pas utilisée** par ces tests (ils passent par le TestClient HTTP).

---

## 2. Current Data Snapshot

| Ressource | Count | Attendu | Surplus |
|-----------|-------|---------|---------|
| custody_providers | 64 | 1 (Modulr) | +63 |
| pe_clients | 64 | 1 (current) | +63 |
| client_deposit_account | 64 | 1 (EUR client current) | +63 |
| company_settlement_account | 1 | 1 | ✓ OK |
| crypto_custody_accounts | 10 | 10 (5 assets × 2 types) | ✓ OK |
| crypto_custody_balances | 10 | 10 | ✓ OK |
| custody_account_balances | 65 | 2 | +63 |
| custody_transactions | 0 | — | ✓ vide |
| exchange_orders | 0 | — | ✓ vide |
| crypto_positions | 0 | — | ✓ vide |
| crypto_settlement_deltas | 0 | — | ✓ vide |

**Current test client** : `e34ff297-ba21-44b9-9d49-a2305b21d59a` (email: `cash-e2e-e33e4a1e@example.com`)

**Patterns de pollution visibles** :

Les 63 providers `Bank-*` sont créés en lots de 15, correspondant exactement aux 15 tests de `test_exchange_engine.py` :

| Timestamp batch | Count | Source probable |
|----------------|-------|-----------------|
| 2026-03-18 06:45 | 15 | pytest run #1 |
| 2026-03-18 06:48 | 2 | pytest partiel |
| 2026-03-18 06:54 | 15 | pytest run #2 |
| 2026-03-18 07:00 | 15 | pytest run #3 |
| 2026-03-18 07:03 | 15 | pytest run #4 |

Corrélation 1:1 confirmée : chaque `Bank-{uuid}` est créé au même timestamp (delta=0s) qu'un `exchange-{uuid}@example.com` et un `client_deposit_account`.

---

## 3. Provider Creation Audit

### Où les providers sont créés

| Source | Fichier | Noms | Automatique ? |
|--------|---------|------|---------------|
| Endpoint admin | `api/services/custody/router.py` → `POST /api/admin/custody/providers` | Payload | Non (manuel) |
| Script modulr | `api/scripts/ensure_single_modulr_and_settlement.py` | "Modulr" (fixe) | Non (script CLI) |
| Test helper | `api/tests/test_exchange_engine.py` `_create_provider()` | `Bank-{uuid.uuid4().hex[:6]}` | **OUI — à chaque test** |
| Test helper | `api/tests/test_custody.py` `_create_provider()` | `Bank-{uuid.uuid4().hex[:6]}` | **OUI — à chaque test** |
| Test helper | `api/tests/test_simulated_deposit.py` `_create_provider()` | `Bank-{uuid.uuid4().hex[:6]}` | **OUI — à chaque test** |
| Test helper | `api/tests/test_internal_transfer.py` `_create_provider()` | `Bank-{uuid.uuid4().hex[:6]}` | **OUI — à chaque test** |
| Test helper | `api/tests/test_custody_hardening.py` `_create_provider()` | `Bank-{uuid.uuid4().hex[:6]}` | **OUI — à chaque test** |

### Pourquoi ils se multiplient

1. Chaque test appelle `_full_setup()` qui appelle `_create_provider()`.
2. `_create_provider()` crée **systématiquement** un nouveau provider avec un nom aléatoire `Bank-{uuid}`.
3. Le `TestClient` écrit dans la **base réelle** sans rollback.
4. `test_exchange_engine.py` a **15 tests** qui appellent chacun `_full_setup()` = 15 providers par run.
5. 4 exécutions de pytest = 63 providers `Bank-*` persistants.

### Pas de création au startup/bootstrap/reset

Aucun startup hook dans `main.py`, aucun bootstrap automatique, et le reset ne crée pas de providers.

---

## 4. Test Client Creation Audit

### Où les clients sont créés

| Source | Fichier | Email pattern | Automatique ? |
|--------|---------|---------------|---------------|
| Endpoint admin | `api/services/test_clients/router.py` → `POST /api/admin/test-clients` | Payload | Non (manuel) |
| Page admin | `web/src/app/admin/test-clients/page.tsx` → `handleCreate` | Saisi par l'utilisateur | Non (1 seul par clic) |
| Test helper | `api/tests/test_exchange_engine.py` `_create_test_client()` | `exchange-{uuid}@example.com` | **OUI — à chaque test** |
| Test helpers | 7 autres fichiers de tests | Divers `@example.com` | **OUI — à chaque test** |

### Pourquoi ils se multiplient

Même mécanisme que les providers :
1. `_full_setup()` → `_create_test_client()` → `POST /api/admin/test-clients` → insertion permanente dans `pe_clients`.
2. 15 tests × 4 runs = ~63 clients `exchange-*@example.com`.
3. Le client `cash-e2e-e33e4a1e@example.com` (le "current") a été créé par un test de `test_cash_endpoint.py`.

### Le Test Client System ne crée pas en masse

- `POST /api/admin/test-clients` crée **un seul client** par appel.
- La page admin n'a pas de bulk create.
- Aucun script ne crée de clients.
- La multiplication vient exclusivement des **tests**.

---

## 5. Custody Account Creation Audit

### Où les comptes sont créés

| Type | Source | Fichier | Automatique ? |
|------|--------|---------|---------------|
| client_deposit_account | Endpoint admin | `router.py` → `POST /api/admin/custody/accounts/client` | Non |
| client_deposit_account | Test helper | `test_exchange_engine.py` `_create_client_account()` | **OUI** |
| company_settlement_account | Endpoint admin | `router.py` → `POST /api/admin/custody/accounts/settlement` | Non |
| company_settlement_account | Test helper | `test_exchange_engine.py` `_create_settlement_account()` | **OUI** (mais gère 409 conflit) |
| company_settlement_account | Script | `ensure_single_modulr_and_settlement.py` | Non (CLI) |
| crypto_custody_accounts | Bootstrap endpoint | `admin_router.py` → `POST bootstrap` | Non (bouton admin) |

### Pourquoi les comptes EUR clients se multiplient

1. Chaque test crée un provider + un client + un compte client → corrélation 1:1:1.
2. Le helper `_create_client_account()` appelle `POST /api/admin/custody/accounts/client` avec un IBAN aléatoire `DE{uuid}`.
3. Aucune vérification d'unicité par client dans le code de création de compte.

### Pourquoi le settlement account peut afficher "Not Found"

Le settlement account est **unique** (1 seul). La logique actuelle :
- `_create_settlement_account()` dans les tests gère le `409 Conflict` (essaie de retrouver le compte existant).
- `find_settlement_account(db, currency)` dans le repository filtre sur `account_type = 'company_settlement_account'`, `currency = 'EUR'`, `is_master_account = True`.
- **Cause possible** : si le provider du settlement account a été supprimé par `ensure_single_modulr_and_settlement.py` (suppression en cascade des comptes non-Modulr) sans recréer le settlement sur Modulr, ou si le champ `is_master_account` n'est pas set correctement.

Aujourd'hui : 1 settlement account existe sur Modulr → OK.

---

## 6. Reset Behavior Audit

### Ce que le reset supprime

| Table | Action |
|-------|--------|
| `custody_webhook_events` | DELETE all |
| `custody_transactions` | DELETE all |
| `pe_ledger_entries` | DELETE all |
| `exchange_orders` | DELETE all |
| `crypto_positions` | DELETE all |
| `crypto_settlement_deltas` | DELETE all |
| `custody_account_balances` | UPDATE → available_balance = 0, pending_balance = 0 |

### Ce que le reset conserve

- `custody_providers` ✓
- `pe_clients` ✓
- `custody_accounts` ✓
- `pe_ledger_accounts` ✓
- `crypto_custody_accounts` ✓
- `crypto_custody_balances` ✓ (non touchés par le reset)
- Produits, templates, bundles ✓

### Ce que le reset recrée

**Rien.** Le reset ne fait aucun create, aucun bootstrap, aucun seed.

### Est-ce qu'il déclenche un bootstrap implicite ?

**Non.** Le code de `run_reset()` est strictement : DELETE + UPDATE + rapport. Le frontend appelle `fetchAll()` après le reset pour rafraîchir l'affichage, mais `fetchAll()` est un GET (lecture seule).

### Point d'attention

Le reset ne touche pas `crypto_custody_balances` : après un reset, `expected_balance` et `actual_balance` des comptes crypto techniques conservent leurs valeurs alors que `crypto_positions` est vidé → mismatch possible.

---

## 7. Lazy Creation / Bootstrap Map

### Carte complète des créateurs automatiques de données

#### Providers fiat

| Créateur | Type | Impact |
|----------|------|--------|
| `POST /api/admin/custody/providers` | Endpoint (manuel) | 1 provider par appel |
| `_create_provider()` dans 5+ fichiers de tests | Test helper (auto) | **1 provider par test, non rollbacké** |

#### Test clients

| Créateur | Type | Impact |
|----------|------|--------|
| `POST /api/admin/test-clients` | Endpoint (manuel) | 1 client par appel |
| `_create_test_client()` dans 8+ fichiers de tests | Test helper (auto) | **1 client par test, non rollbacké** |

#### Comptes EUR clients

| Créateur | Type | Impact |
|----------|------|--------|
| `POST /api/admin/custody/accounts/client` | Endpoint (manuel) | 1 compte par appel |
| `_create_client_account()` dans les tests | Test helper (auto) | **1 compte par test, non rollbacké** |

#### Compte EUR settlement

| Créateur | Type | Impact |
|----------|------|--------|
| `POST /api/admin/custody/accounts/settlement` | Endpoint (manuel) | 1 compte (gère 409 conflit) |
| `ensure_single_modulr_and_settlement.py` | Script CLI | 1 compte si absent |

#### Comptes crypto techniques

| Créateur | Type | Impact |
|----------|------|--------|
| `POST /api/admin/exchange/crypto-custody/bootstrap` | Endpoint (manuel) | get_or_create, idempotent |
| `get_or_create_account()` dans le repository | Lazy create | Idempotent (unique constraint) |

#### Positions / deltas (lazy create dans le buy)

| Créateur | Type | Impact |
|----------|------|--------|
| `ExchangeService.execute_buy()` | Service buy | `crypto_positions.get_or_create_for_update()` |
| `ExchangeService.execute_buy()` | Service buy | `crypto_settlement_deltas.get_or_create()` |

---

## 8. Test Isolation Audit

### Les tests écrivent-ils dans la vraie DB locale ?

**OUI — de manière permanente.**

### Preuves

1. **`conftest.py`** : la fixture `client` crée un `TestClient(test_app)` **sans override de `get_db`**. L'app FastAPI utilise sa propre `get_db` → `SessionLocal` → `DATABASE_URL` → base locale réelle.

2. **`_full_setup()` dans `test_exchange_engine.py`** : appelle `POST /api/admin/custody/providers`, `POST /api/admin/test-clients`, `POST /api/admin/custody/accounts/client`, `POST /api/admin/custody/accounts/settlement` via le TestClient. Chaque appel crée une row **permanente**.

3. **Corrélation temporelle prouvée** : les 63 providers `Bank-*` sont créés en lots de 15 (exactement le nombre de tests dans `test_exchange_engine.py`), avec des timestamps correspondant aux exécutions de pytest (06:45, 06:54, 07:00, 07:03).

4. **`SessionLocal` directe** : certains tests utilisent `SessionLocal()` directement (ex: `test_exchange_engine.py` lignes 531, 592 pour `ExchangeFeeConfigRepository.upsert` → `commit()`).

5. **La fixture `db` existe** avec rollback transactionnel, mais elle est ignorée par les tests qui passent par le TestClient HTTP. Seuls quelques tests unitaires (ex: `test_crypto_custody_layer.py` pour les tests repos purs) utilisent cette fixture.

6. **Exception notable** : `test_bundle_engine.py` override `get_db` avec la session de la fixture → isolation correcte. C'est le seul fichier qui fait ça.

### Tests qui polluent la DB réelle

| Fichier | Providers créés/run | Clients créés/run | Comptes créés/run |
|---------|--------------------|--------------------|-------------------|
| `test_exchange_engine.py` | 15 | 15 | 15 |
| `test_custody.py` | ~6 | ~6 | ~6 |
| `test_simulated_deposit.py` | ~3 | ~3 | ~3 |
| `test_internal_transfer.py` | ~4 | ~4 | ~4 |
| `test_custody_hardening.py` | ~2 | ~2 | ~2 |
| `test_euro_account.py` | ~2 | ~2 | ~2 |
| `test_cash_endpoint.py` | ~1 | ~1 | ~1 |

---

## 9. Root Causes

### Cause #1 : Absence d'isolation DB dans les tests HTTP (CAUSE PRINCIPALE)

Le `TestClient(test_app)` utilise la DB réelle. Chaque test qui passe par l'API HTTP crée des données permanentes. La fixture `db` avec rollback n'est pas connectée au TestClient.

**Impact** : chaque `pytest` ajoute ~30-50 rows (providers, clients, comptes) qui ne sont jamais supprimées.

### Cause #2 : Helpers de test créent systématiquement de nouvelles données

`_full_setup()` crée un **nouveau** provider + client + compte **par test** au lieu de réutiliser des données existantes ou une session partagée.

**Impact** : multiplication linéaire avec le nombre de tests × le nombre de runs.

### Cause #3 : Aucun nettoyage post-test

Pas de `teardown`, pas de `autouse fixture` de cleanup, pas de `pytest-transaction` ou `pytest-postgresql` pour isoler automatiquement.

### Cause #4 : Le reset ne nettoie pas les données de structure

Le reset supprime les **données runtime** (transactions, orders, positions) mais conserve les **données de structure** (providers, clients, comptes). C'est le comportement voulu, mais cela signifie que la pollution de structure s'accumule indéfiniment.

---

## 10. Recommended Correction Plan

### Phase 1 : Isolation des tests (priorité absolue)

1. **Modifier `conftest.py`** : override `get_db` dans `test_app` pour que le TestClient utilise la session transactionnelle avec rollback automatique (comme `test_bundle_engine.py` le fait déjà).
2. Cela résout 100% de la pollution future sans toucher aux tests eux-mêmes.

### Phase 2 : Nettoyage one-shot de la base actuelle

1. Supprimer tous les providers sauf Modulr (`DELETE FROM custody_providers WHERE name != 'Modulr'` avec cascade sur accounts/balances).
2. Supprimer tous les clients sauf le current.
3. Vérifier qu'il reste : 1 provider, 1 client, 1 compte EUR client, 1 settlement EUR.
4. Le script `ensure_single_modulr_and_settlement.py` + `delete_clients_except_current.py` font déjà ça → les exécuter.

### Phase 3 : Hardening de la sandbox

1. Ajouter une contrainte applicative : empêcher la création de providers avec des noms `Bank-*` (pattern de test) en environnement non-test.
2. S'assurer que le reset ne touche pas `crypto_custody_balances` (ou les remet à 0 si voulu).
3. Optionnel : module-scope ou session-scope fixtures pour les tests qui partagent un setup (éviter 15× le même setup).

### Phase 4 : Sandbox canonique stable

État cible :
- 1 provider `Modulr` (bank, active)
- 1 client `cash-e2e-*@example.com` (current)
- 1 compte `client_deposit_account` EUR avec IBAN `FR76...`
- 1 compte `company_settlement_account` EUR sur Modulr
- 10 comptes `crypto_custody_accounts` (5 assets × 2 types)
- Reset = vide les runtime data uniquement
- Les tests n'écrivent plus dans la DB réelle

---

## 11. What Must NOT Be Done

| Action dangereuse | Pourquoi |
|-------------------|----------|
| Supprimer le code de `_full_setup()` dans les tests | Les tests en ont besoin ; il faut isoler la DB, pas supprimer le setup |
| Lancer `DELETE FROM custody_providers` sans cascade | FK constraints → erreurs |
| Modifier `DATABASE_URL` pour pointer vers une autre DB en test | Risque de casser les imports et la config ; mieux vaut override `get_db` |
| Ajouter un cleanup automatique après chaque test (DELETE) | Fragile, risque de supprimer des données voulues ; le rollback transactionnel est la bonne approche |
| Supprimer les scripts `ensure_single_modulr_and_settlement.py` | Ils sont utiles pour le nettoyage ponctuel |
| Rendre le reset plus agressif (supprimer providers/clients) | Le reset doit rester "runtime-only" ; le nettoyage de structure est un acte séparé |
| Ajouter un bootstrap automatique au startup de l'app | Crée des données à chaque redémarrage → même problème qu'aujourd'hui |
| Créer une DB de test séparée | Surdimensionné pour le problème ; l'override `get_db` avec rollback suffit |

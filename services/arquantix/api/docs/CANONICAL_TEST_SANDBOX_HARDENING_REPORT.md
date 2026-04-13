# Canonical Test Sandbox Hardening Report

## 1. Executive Summary

| Objectif | Statut |
|---|---|
| Pollution future stoppée | **OUI** — `conftest.py` override `get_db` avec session transactionnelle + rollback |
| Cleanup one-shot effectué | **OUI** — 63 providers, 63 clients, 63 comptes supprimés |
| Tests passent post-correction | **OUI** — 85/85 (custody/exchange) + 56 (bundle/reset) = 141 tests OK |
| DB stable après 141 tests | **OUI** — providers=1, clients=1, EUR client=1, settlement=1 |
| Niveau de confiance | **Élevé** — l'isolation est structurelle, pas comportementale |

---

## 2. Files Modified

| Fichier | Rôle |
|---|---|
| `api/tests/conftest.py` | **Fix principal** — override `get_db` dans le fixture `client` pour utiliser la session `db` transactionnelle |
| `api/tests/test_exchange_engine.py` | Remplacé `SessionLocal()` par fixture `db` dans `test_fee_calculation` et `test_settlement_delta_uses_raw_volume` |
| `api/tests/test_crypto_custody_layer.py` | Remplacé `SessionLocal()` par fixture `db` dans `test_settlement_uses_persisted_balance` |
| `api/tests/test_custody.py` | Remplacé `SessionLocal()` par fixture `db` dans `test_ledger_entries_created` |
| `api/tests/test_custody_hardening.py` | Remplacé `SessionLocal()` par fixture `db` dans `test_concurrent_withdraw_optimistic_lock`, `test_balance_version_increments`, `test_ledger_invariant_after_webhook_deposit` |
| `api/tests/test_euro_account.py` | Remplacé `SessionLocal()` par fixture `db` dans `test_euro_account_no_current_client` |
| `api/tests/test_test_clients.py` | Remplacé `SessionLocal()` + `TestClient(test_app)` par fixtures `client` + `db` dans `test_bootstrap_fails_if_no_current` |
| `api/scripts/cleanup_sandbox.py` | **Nouveau** — script de nettoyage one-shot canonique |

---

## 3. Test Isolation Fix

### Comment `get_db` est overridé

```python
# api/tests/conftest.py

@pytest.fixture(scope="function")
def client(test_app, db):
    def _override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(test_app) as c:
        yield c
    test_app.dependency_overrides.pop(get_db, None)
```

### Comment le TestClient est isolé

Le fixture `client` **dépend du fixture `db`**, qui crée une connexion avec une transaction ouverte. L'override de `get_db` fait que chaque endpoint FastAPI utilise **la même session** que le test. Quand le test termine, le fixture `db` fait `trans.rollback()` — toutes les données disparaissent.

### Comment le rollback fonctionne

```
connexion DB
  └── BEGIN (transaction externe)
        └── SAVEPOINT (nested transaction)
              └── endpoint 1: INSERT ...   (visible dans la même session)
              └── endpoint 2: INSERT ...
              └── assertion du test: SELECT ...
        └── RELEASE SAVEPOINT (ou rollback si erreur)
  └── ROLLBACK  ← tout est annulé, rien n'est persisté
```

Le listener `after_transaction_end` recrée un savepoint après chaque commit interne des endpoints, permettant à SQLAlchemy de fonctionner normalement tout en restant dans la transaction englobante.

### Cas particulier : `SessionLocal()` dans les tests

Certains tests utilisaient directement `SessionLocal()` pour lire/écrire — ces sessions étaient **hors** de la transaction isolée et voyaient/écrivaient dans la DB réelle. Tous ces usages ont été remplacés par le fixture `db` partagé.

---

## 4. Cleanup Logic

### Entités conservées

| Entité | ID | Raison |
|---|---|---|
| Provider "Modulr" | `817eed08-1109-459a-b704-bf6a01d9bf56` | Seul provider fiat de test |
| Client test | `e34ff297-ba21-44b9-9d49-a2305b21d59a` | Current test client |
| Compte EUR client | `ead746c7-322e-421b-bbec-6aa055719f6b` | Unique compte client IBAN |
| Settlement EUR | `9a6e0406-99ed-43d9-8adc-3e5fd05b29fc` | Unique compte settlement |
| `crypto_custody_accounts` (10) | — | Comptes techniques BTC/ETH/SOL/USDC/USDT × pool/wallet |
| `crypto_custody_balances` (10) | — | Balances associées |
| Bundles / templates / produits | — | Non touchés |

### Entités supprimées

| Entité | Nombre | Pattern |
|---|---|---|
| Providers "Bank-*" | 63 | Créés par tests HTTP non isolés |
| Clients `exchange-*@example.com` | 63 | Créés par `_create_test_client()` dans les tests |
| `client_deposit_account` excédentaires | 63 | Un par client de test |
| `custody_account_balances` orphelines | 63 | Liées aux comptes supprimés |
| `pe_ledger_accounts` non-current | 63 | Liées aux clients supprimés |

### Ordre d'exécution (respect FK)

1. `app_runtime_settings` — restauration du current client
2. Tables runtime (webhooks, transactions, entries, orders, positions, deltas)
3. `custody_account_balances` non-canoniques
4. `custody_accounts` client_deposit non-canoniques
5. `pe_ledger_accounts` non-current
6. `pe_clients` non-current
7. `custody_providers` non-Modulr
8. Reset des balances canoniques à zéro

### Garanties FK

- Les webhooks/transactions sont supprimés avant les comptes
- Les balances sont supprimées avant les comptes
- Les ledger accounts/entries sont supprimés avant les clients
- Les comptes sont supprimés avant les providers
- Le settlement EUR, Modulr, et le current client ne sont jamais ciblés par les DELETE

---

## 5. Post-cleanup State

| Table | Count | Attendu | Status |
|---|---|---|---|
| `custody_providers` | 1 | 1 | ✅ |
| `pe_clients` | 1 | 1 | ✅ |
| `custody_accounts` (client_deposit) | 1 | 1 | ✅ |
| `custody_accounts` (settlement) | 1 | 1 | ✅ |
| `crypto_custody_accounts` | 10 | 10 | ✅ (préservé) |
| `crypto_custody_balances` | 10 | 10 | ✅ (préservé) |
| `custody_account_balances` | 2 | 2 | ✅ |
| `app_runtime_settings` | 1 | 1 | ✅ |

**Après exécution de 141 tests :**

| Table | Count avant tests | Count après tests | Delta |
|---|---|---|---|
| `custody_providers` | 1 | 1 | 0 |
| `pe_clients` | 1 | 1 | 0 |
| `custody_accounts` | 2 | 2 | 0 |
| `crypto_custody_accounts` | 10 | 10 | 0 |

→ **Zéro pollution après 141 tests.**

---

## 6. Reset Behavior Verification

### Ce que le reset supprime (runtime-only)

| Table | Action |
|---|---|
| `custody_webhook_events` | DELETE ALL |
| `custody_transactions` | DELETE ALL |
| `pe_ledger_entries` | DELETE ALL |
| `exchange_orders` | DELETE ALL |
| `crypto_positions` | DELETE ALL |
| `crypto_settlement_deltas` | DELETE ALL |
| `custody_account_balances` | UPDATE → `available_balance = 0, pending_balance = 0` |

### Ce qu'il conserve

- `custody_providers` — non touché
- `pe_clients` — non touché
- `custody_accounts` — non touché
- `pe_ledger_accounts` — non touché
- `crypto_custody_accounts` — non touché
- `crypto_custody_balances` — non touché
- Bundles / templates / produits — non touchés

### Confirmation qu'il ne recrée rien

Le code de `run_reset()` dans `api/services/financial_reset/reset.py` :
- N'a aucun `INSERT`
- N'a aucun `get_or_create`
- N'appelle aucun bootstrap
- N'instancie aucun modèle ORM
- Se termine par un rapport de comptage (avant/après), sans effet de bord

---

## 7. Final Status

**Le sandbox peut-il désormais rester stable avec exactement 1 Modulr, 1 current client, 1 compte EUR client, et 1 compte EUR settlement ?**

### **OUI.**

**Raisons :**

1. **L'isolation transactionnelle** dans `conftest.py` empêche structurellement tout test HTTP de persister quoi que ce soit dans la DB réelle. Ce n'est pas un contrat comportemental (chaque test doit nettoyer) mais un contrat structurel (le rollback est automatique).

2. **Le reset financier** ne touche qu'aux données runtime et ne recrée jamais d'entités structurelles.

3. **Le bootstrap crypto** (`/api/admin/exchange/crypto-custody/bootstrap`) est idempotent et ne crée pas de providers/clients supplémentaires.

4. **Le cleanup one-shot** (`api/scripts/cleanup_sandbox.py`) est réexécutable si nécessaire et respecte les FK.

5. **La protection contre Bank-*** n'a pas été ajoutée dans le code car le pattern "Bank-{uuid}" n'est généré que par les helpers de tests, désormais isolés. Si un re-passage sans isolation devait se produire, le script `cleanup_sandbox.py` peut être réexécuté.

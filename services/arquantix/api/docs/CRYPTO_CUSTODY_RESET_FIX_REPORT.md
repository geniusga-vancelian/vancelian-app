# Crypto Custody Reset Fix Report

## 1. Executive Summary

| Objectif | Statut |
|---|---|
| Reset des crypto balances corrigé | **OUI** |
| `actual_balance` remis à 0 | **OUI** — 10/10 rows |
| `expected_balance` remis à 0 | **OUI** — 10/10 rows |
| `updated_from_provider_at` remis à NULL | **OUI** |
| Comptes crypto préservés | **OUI** — 10 accounts, 10 balances inchangés |
| Tests passent | **OUI** — 141 passed, 0 failed |
| Sandbox canonique intact | **OUI** — 1 Modulr, 1 client, 1 EUR, 1 settlement |
| Niveau de confiance | **Élevé** |

---

## 2. Files Modified

| Fichier | Rôle |
|---|---|
| `api/services/financial_reset/reset.py` | Ajout de l'UPDATE `crypto_custody_balances` et du comptage avant/après |
| `api/tests/test_reset_financial_test_state.py` | Nouveau test `test_reset_zeroes_crypto_custody_balances` + couverture élargie |
| `api/tests/test_exchange_engine.py` | Settlement tests renforcés : bootstrap + set-actual-balance DB avant settlement |

---

## 3. Reset Behavior Change

### Avant (incomplet)

Le reset remettait à zéro :
- `custody_account_balances` (fiat) → `available_balance=0`, `pending_balance=0`
- 6 tables runtime (DELETE)

**Manquait :**
- `crypto_custody_balances` conservait ses valeurs `actual_balance` / `expected_balance`
- Les settlement wallets gardaient une liquidité résiduelle après reset

### Après (corrigé)

Le reset remet désormais à zéro :

| Table | Action |
|---|---|
| `custody_webhook_events` | DELETE ALL |
| `custody_transactions` | DELETE ALL |
| `pe_ledger_entries` | DELETE ALL |
| `exchange_orders` | DELETE ALL |
| `crypto_positions` | DELETE ALL |
| `crypto_settlement_deltas` | DELETE ALL |
| `custody_account_balances` | UPDATE → `available_balance=0, pending_balance=0` |
| **`crypto_custody_balances`** | **UPDATE → `actual_balance=0, expected_balance=0, updated_from_provider_at=NULL`** |

### Ce qui reste conservé (inchangé)

- `custody_providers` — non touché
- `pe_clients` — non touché
- `custody_accounts` — non touché
- `pe_ledger_accounts` — non touché
- `crypto_custody_accounts` — non touché (rows préservées)
- `crypto_custody_balances` — **rows préservées**, seules les valeurs sont remises à zéro
- Bundles / templates / produits — non touchés

---

## 4. Crypto Custody Verification

### Comptes conservés

```
crypto_custody_accounts: 10 (5 assets × 2 types)
crypto_custody_balances: 10 (1 par compte)
```

Aucun compte supprimé. Aucun compte recréé.

### Balances remises à zéro

Rapport de reset réel exécuté :

```
before:
  crypto_total_actual:   537037.03
  crypto_total_expected: 301.50
  crypto_custody_accounts: 10
  crypto_custody_balances: 10

after:
  crypto_total_actual:   0.0
  crypto_total_expected: 0.0
  crypto_custody_accounts: 10  (inchangé)
  crypto_custody_balances: 10  (inchangé)

crypto_balances_updated: 10
```

### Mismatch remis à zéro

Avec `actual_balance=0` et `expected_balance=0`, le mismatch calculé (`actual - expected`) = 0 pour tous les comptes.

---

## 5. Post-reset State

| Table | Count | Attendu |
|---|---|---|
| `custody_providers` | 1 | 1 (Modulr) |
| `pe_clients` | 1 | 1 (current) |
| `custody_accounts` (client_deposit) | 1 | 1 |
| `custody_accounts` (settlement) | 1 | 1 |
| `crypto_custody_accounts` | 10 | 10 |
| `crypto_custody_balances` | 10 | 10 |
| `crypto_positions` | 0 | 0 |
| `crypto_settlement_deltas` | 0 | 0 |
| `exchange_orders` | 0 | 0 |
| Total `actual_balance` | 0.0 | 0.0 |
| Total `expected_balance` | 0.0 | 0.0 |

---

## 6. Final Status

**Le reset financier remet-il maintenant complètement à zéro les balances fiat + crypto tout en préservant la structure canonique du sandbox ?**

### **OUI.**

Le bouton "Reset financial test state" signifie désormais : **retour à un état financier entièrement nul**. Aucune transaction, aucune position, aucun delta, aucune balance non-nulle (fiat ou crypto).

Si une liquidité de test est nécessaire après reset (ex: 100000 BTC pour tester le settlement), elle doit être injectée via une action séparée :
- Bouton "Set actual balance" dans l'admin Crypto Custody
- Endpoint `POST /api/admin/exchange/crypto-custody/{id}/set-actual-balance`
- Script dédié de seed

Cette séparation est volontaire : **reset ≠ seed**.

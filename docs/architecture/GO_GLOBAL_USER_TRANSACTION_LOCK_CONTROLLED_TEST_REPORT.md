# Rapport GO — Test contrôlé Global User Transaction Lock V1 (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **PR / merge** | [#59](https://github.com/geniusga-vancelian/vancelian-app/pull/59) · `9087eb41` |
| **Task definition** | **`arquantix-api:156`** |
| **Prérequis** | [GO_GLOBAL_USER_TRANSACTION_LOCK_POST_DEPLOY_REPORT.md](GO_GLOBAL_USER_TRANSACTION_LOCK_POST_DEPLOY_REPORT.md) ✅ |
| **Décision** | **✅ Global Lock controlled test = GO** |

---

## 1. Décision

**Global Lock controlled test = GO**

Doctrine **1 user = 1 transaction financière active** prouvée en production :

```text
acquire intent A → OK
acquire intent B (même user) → 409 transaction_in_progress
release A → OK
acquire B → OK
cleanup release B → baseline restaurée
```

Aucune blockchain · aucun swap · aucun mouvement économique · flag ON **job ECS uniquement** · TD prod flags OFF.

---

## 2. Identifiants

| Champ | Valeur |
| --- | --- |
| `test_run_id` | `2c1c0a513603427a9c72335d031b3857` |
| `intent_a_id` | `aeede876-5fbc-4296-b051-529574653775` |
| `intent_b_id` (final acquire) | voir JSON ECS (`acquire_b_ok`) |
| ECS task | `c6cacfae5c3f4bd9881aa44b96ce45a9` · exit **0** |

---

## 3. Résultats

| Check | Valeur | Attendu |
| --- | --- | --- |
| `all_checks_pass` | **true** | ✅ |
| `acquire_a_success` | **true** | ✅ |
| `acquire_b_conflict` | **true** | ✅ |
| `error_code_transaction_in_progress` | **true** | ✅ |
| `user_message` | *A transaction is already in progress…* | ✅ |
| `release_a_success` | **true** | ✅ |
| `acquire_b_after_release_success` | **true** | ✅ |
| `active_financial_transaction_locks` (fin) | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| `dead_letter` | **0** | ✅ |
| `completed` | **0** | ✅ |

### JSON ECS (extrait)

```json
{
  "test_run_id": "2c1c0a513603427a9c72335d031b3857",
  "acquire_a": { "acquired": true },
  "acquire_b_conflict": {
    "conflict_raised": true,
    "error_code": "transaction_in_progress",
    "user_message": "A transaction is already in progress. Please wait until it is completed."
  },
  "release_a": { "released": true },
  "acquire_b_ok": { "acquired": true },
  "baseline_after": {
    "active_financial_transaction_locks": 0,
    "pe_atoms": 19,
    "cost_basis": 67,
    "lifi_swap_legs": 131,
    "dead_letter": 0,
    "completed": 0
  },
  "all_checks_pass": true
}
```

---

## 4. Neutralité

| Critère | Statut |
| --- | --- |
| Pas de swap / LI.FI / settlement | ✅ |
| PE / CB / legs inchangés | ✅ |
| Pas de lock `financial_transaction` résiduel | ✅ |
| Outbox `dead_letter` = 0 | ✅ |
| Intents `COMPLETED` = 0 | ✅ |
| `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` absent en TD | ✅ **maintenu** |

---

## 5. Gate suivant — B4b minimal

Rail cible :

```text
Parent FROZEN
  → Child auto (B4a)
  → Global user lock acquis
  → Fresh swap LI.FI
  → Attach swap
  → Settlement B3c
  → Child LEDGER_SETTLED
```

**Global Lock V1 ✅** · **B4a ✅** → ouvrir **B4b**.

---

## Références

- Script : `scripts/arquantix-ecs-global-lock-controlled-test.sh`
- Inline : `scripts/_global-lock-controlled-test-inline.py`
- [S4_PRODUCT_LOCKS_MATRIX.md](S4_PRODUCT_LOCKS_MATRIX.md) §4.6

# Incident — Investissements Bundle concurrents (prod pilote)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Compte** | gaelitier@gmail.com · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **Sévérité** | Moyenne — pas de perte fonds · contention wallet / legs bloqués |
| **Statut** | Mitigation Global Lock mergée · **P0 lock orphaning** en cours · flag prod **OFF** · recovery **suspendue** |

---

## Symptôme

Deux invests Bundle lancés quasi simultanément via WebApp sur **deux portfolios différents** :

| Portfolio | Batch | Montant |
| --- | --- | --- |
| Crypto Majors `ab4ae920…` | `10d688bb…` | 25 USDC |
| Two Crypto Kings `daea3720…` | `3e7c5db4…` | 20 USDC |

Les deux flows ont tourné **en parallèle** (CBBTC confirmé sur chacun, CBETH bloqué en attente signature / submitted).

---

## Cause racine

1. La WebApp utilise le **`BundleOrchestrator` legacy** (`orchestrator.py` → `_invest_via_lifi`), pas le rail event-driven B4b.
2. Protection existante : **`bundle_invest_lock`** dans `pe_portfolios.metadata` — **1 lock par portfolio**, pas par utilisateur.
3. Le **Global User Transaction Lock V1** était implémenté et testé (controlled test B4b) mais **non câblé** au runtime WebApp legacy.
4. Flag prod `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` : **absent / OFF** (TD `:160`).

**Doctrine violée** : 1 user = 1 transaction financière active.

---

## Correctif

PR hotfix : `legacy_bundle_global_lock.py` + wiring dans :

- `BundleOrchestrator._invest_via_lifi` — acquire avant funding / swaps
- `BundleOrchestrator.resume_lifi_invest_batch` — acquire idempotent (même intent)
- `BundleOrchestrator._terminal_bundle_invest_lock` — release sur `clear` / `release_failed` uniquement
- Routes `POST /api/app/bundle/invest` et `/resume` — `409 transaction_in_progress`

| Flag | Comportement |
| --- | --- |
| `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` **OFF** | Inchangé (no-op strict) |
| **ON** (staging / fenêtre contrôlée) | 2e invest même user → **409** · resume même batch → OK |

---

## Avant / après

| Scénario | Avant | Après (flag ON) |
| --- | --- | --- |
| 2 portfolios · même user · invests parallèles | ✅ Autorisé | ❌ 409 sur le 2e |
| 2 invests · même portfolio | ❌ 409 `already_pending` | ❌ 409 (portfolio ou global) |
| Resume même batch | ✅ | ✅ (idempotent) |
| Batch pending signature | Lock global tenu | Lock global tenu |
| Batch terminal (completed / failed) | Lock portfolio libéré | Lock portfolio + **global** libérés |

---

## Batches incident (audit 2026-06-08)

État au moment de l’audit — **recovery manuelle requise** (Reprendre l’investissement) :

| Batch | Legs | État |
| --- | --- | --- |
| `10d688bb…` | 1/5 | CBBTC ✅ · CBETH submitted · LINK/AAVE/UNI quote |
| `3e7c5db4…` | 1/2 | CBBTC ✅ · CBETH awaiting signature |

**Ne pas relancer** de nouveaux tests WebApp réels tant que le flag n’est pas activé avec GO explicite.

---

## P0 — Perte silencieuse `bundle_invest_lock` (2026-06-08)

### Symptôme (batch `470c964f…` · Two Crypto Kings)

- Dépôt + funding OK · parent `awaiting_signature` · swaps `AWAITING_SIGNATURE`
- `pe_portfolios.metadata.bundle_invest_lock` = **null**
- UI : pas de bannière · pas de « Reprendre » · `resume` → `no_active_invest_lock`
- Classification audit : **`PARTIAL_BATCH_HIDDEN`**

### Cause racine

1. `GET /bundle/invest/active-lock` : `reconcile_or_expire_idle_invest_lock` + **`db.commit()`** sur lecture.
2. `reconcile_idle_invest_lock` → `clear_invest_lock` sans audit si travail bloquant non détecté (y compris autre batch du même portfolio).
3. `update_invest_lock_status` : échec silencieux si lock déjà clear.

### Correctif P0

- GET active-lock **read-only** (`peek_bundle_invest_lock_state`)
- Reconcile : **ne pas clear** si swaps bundle pending sur le portfolio (tous batches)
- `update_invest_lock_status` / `resume` : **réacquisition** + audit `bundle.invest_lock_reacquired`
- Recovery UI **après** deploy neutre + controlled test shape `470c964f`

---

## Références

- [S4_PRODUCT_LOCKS_MATRIX.md](S4_PRODUCT_LOCKS_MATRIX.md) §4.6
- [GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md](GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md)
- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md)

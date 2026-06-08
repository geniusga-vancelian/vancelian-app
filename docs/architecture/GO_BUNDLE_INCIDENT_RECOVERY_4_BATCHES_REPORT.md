# GO — Recovery incident 4 batches Bundle (prod pilote)

| Champ | Valeur |
| --- | --- |
| **Date audit initial** | 2026-06-08T17:40:06Z |
| **Compte** | gaelitier@gmail.com · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **TD prod** | `arquantix-api:161` |
| **Global Lock** | `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` **absent/OFF** |
| **Statut** | 🔴 **Recovery en cours** — 4/4 batches bloqués |

---

## Contexte

- Hotfix PR #61 mergé — wiring Global Lock legacy WebApp **déployé**.
- Flag **OFF** → parallélisme 2 portfolios **toujours possible** (comportement attendu).
- Retest utilisateur ~21:32 locale : nouveaux batches `94d810b4` + `470c964f` en parallèle des anciens.

**Interdictions actives** : aucun nouvel invest Bundle · recovery UI un batch à la fois · pas de cleanup DB auto.

---

## Audit initial (ECS read-only)

Script : `./scripts/arquantix-ecs-bundle-incident-4-batches-audit.sh`

### Santé globale

| Métrique | Valeur | Baseline doc | Δ |
| --- | --- | --- | --- |
| PE atoms | 19 | 19 | 0 |
| Cost basis executions | 80 | 67 (incident) | +13 |
| LI.FI swap deposits | 131 | 131 | 0 |
| Global locks actifs | **0** | 0 | — |
| Dead letter outbox | **0** | 0 | — |
| Outbox | pending=21 · processed=27 | — | — |

`stuck_bundle_parents` (tous intents bundle non terminaux) : **10** — inclut les 4 batches incident + parents orphelins `created`.

**`global_lock_activatable_after_recovery`** : **false** (4 batches stuck).

---

## Détail par batch (ordre recovery)

### 1. `94d810b4…` — Crypto Majors — **nouveau** — priorité 1

| Champ | Valeur |
| --- | --- |
| Parent status | `partial` |
| Classification | `stuck_in_progress` |
| Legs | **4/5 confirmed** · 1 pending |
| Funding | 20 USDC (UI) |

**Swaps**

| Asset | Status | tx_hash |
| --- | --- | --- |
| CBBTC | CONFIRMED | `0x2bd45377748c499f…` |
| CBETH | AWAITING_SIGNATURE | — |
| LINK | CONFIRMED | `0x8418a7d50870c450…` |
| AAVE | CONFIRMED | `0x27b2b49a386a7307…` |
| UNI | CONFIRMED | `0xd4516ecc4e2ce670…` |

**Note** : swap UNI CONFIRMED mais parent encore `partial` 4/5 — écart sync parent/legs à vérifier post-reprise UI (« Mise à jour du portefeuille »).

**Action** : Reprendre via UI → finaliser CBETH si bloqué · attendre terminal parent.

---

### 2. `470c964f…` — Two Crypto Kings — **nouveau** — priorité 2

| Champ | Valeur |
| --- | --- |
| Parent status | `awaiting_signature` |
| Classification | `stuck_in_progress` |
| Legs | **0/2 confirmed** · 2 pending |

**Swaps**

| Asset | Status |
| --- | --- |
| CBBTC | AWAITING_SIGNATURE |
| CBETH | AWAITING_SIGNATURE |

**Action** : Reprendre · signer CBBTC puis CBETH · **ne pas** lancer batch 3 avant terminal ou décision CTO.

---

### 3. `10d688bb…` — Crypto Majors — **ancien** — priorité 3

| Champ | Valeur |
| --- | --- |
| Parent status | `partial` |
| Classification | `stuck_in_progress` |
| Legs | **3/5 confirmed** · 1 submitted · 1 pending |

**Swaps**

| Asset | Status | tx_hash |
| --- | --- | --- |
| CBBTC | CONFIRMED | `0xef941cc2…` |
| CBETH | SUBMITTED | `0x36228d0c…` |
| LINK | CONFIRMED | `0x044e77e9…` |
| AAVE | CONFIRMED | `0x8e52c77b…` |
| UNI | AWAITING_SIGNATURE | — |

**Action** : Reprendre après batch 1 et 2 terminés.

---

### 4. `3e7c5db4…` — Two Crypto Kings — **ancien** — priorité 4

| Champ | Valeur |
| --- | --- |
| Parent status | `partial` |
| Classification | `stuck_in_progress` |
| Legs | **1/2 confirmed** · 1 pending |

**Swaps**

| Asset | Status | tx_hash |
| --- | --- | --- |
| CBBTC | CONFIRMED | `0x516f5573…` |
| CBETH | AWAITING_SIGNATURE | — |

**Action** : Reprendre en dernier.

---

## Procédure recovery (UI uniquement)

```
Pour chaque batch (ordre 1→4) :
  1. Ouvrir portfolio / écran invest
  2. « Reprendre l'investissement »
  3. Signer chaque leg AWAITING_SIGNATURE / SUBMITTED
  4. Attendre terminal (completed ou échec documenté)
  5. ./scripts/arquantix-ecs-bundle-incident-4-batches-audit.sh
  6. Si blocage > 30 min sur une leg → STOP + décision CTO
```

**Ne pas** traiter deux batches en parallèle.

---

## Journal recovery (à compléter)

| Batch | Reprise UI | Audit post | Terminal ? | Notes |
| --- | --- | --- | --- | --- |
| `94d810b4` | ⏳ | — | — | |
| `470c964f` | ⏳ | — | — | |
| `10d688bb` | ⏳ | — | — | |
| `3e7c5db4` | ⏳ | — | — | |

---

## Réponses critères GO

| Question | Réponse audit initial |
| --- | --- |
| Les 4 batches terminés ? | **Non** — 4/4 `stuck_in_progress` |
| Global Lock activable ? | **Non** — recovery requise d'abord |
| 409 WebApp fonctionne ? | **Non testé runtime** — flag OFF ; controlled test job OK |
| Reprendre plan WebApp 1 USDC ? | **Non** — après recovery + activation flag + test 409 |

---

## Références

- [INCIDENT_BUNDLE_CONCURRENT_INVESTMENTS_2026_06_08.md](INCIDENT_BUNDLE_CONCURRENT_INVESTMENTS_2026_06_08.md)
- [GO_LEGACY_GLOBAL_LOCK_ACTIVATION_RUNBOOK.md](GO_LEGACY_GLOBAL_LOCK_ACTIVATION_RUNBOOK.md)

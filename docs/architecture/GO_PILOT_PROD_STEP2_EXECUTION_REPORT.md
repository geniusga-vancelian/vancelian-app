# Rapport d’exécution — Go Pilot Prod Étape 2 (worker ON, ledger OFF)

| Champ | Valeur |
| --- | --- |
| **Runbook** | [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) § Étape 2 |
| **Feu vert** | Go Pilot Prod **Étape 2 uniquement** |
| **Opérateur** | Cursor (agent) |
| **Date** | 2026-06-07 |
| **Décision** | **Étape 2 OK avec réserves** (worker rollback OFF — TD `:116`) |
| **Suite** | **Stop pilot** jusqu'à merge **S2a.2** (intent au confirm) |

---

## Interdictions respectées

| Action | Statut |
| --- | --- |
| Activer `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | ❌ Non fait (`false`) |
| Swap on-chain / submit | ❌ Non fait (`tx_hash` null partout) |
| Supprimer outbox pending | ❌ Non fait |
| Étape 3 (ledger) | ❌ Non démarrée |

---

## 1. Activation ECS prod (us-east-1)

| Champ | Valeur |
| --- | --- |
| Cluster | `arquantix-cluster` |
| Service | `arquantix-api` |
| Task definition **avant** | `arquantix-api:114` |
| Task definition **après** | `arquantix-api:115` |
| Image | `arquantix-api:cd6c446b` (inchangée) |

### Changement unique

| Variable | `:114` | `:115` |
| --- | --- | --- |
| `LIFI_OUTBOX_WORKER_ENABLED` | `false` | **`true`** |
| `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` | `gaelitier@gmail.com` | inchangé |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `true` | inchangé |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | `false` | inchangé |

`update-service` + `wait services-stable` : **OK**.

### Tick worker déclenché

ECS one-shot : `python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480`

| Champ | Valeur |
| --- | --- |
| Task ARN tick | `ff1e8710356e473f8b45a11c5fc891d0` |
| Exit code | **2** (degraded — acceptable ops) |
| Step `transaction_outbox` | `enabled=true`, `polled=7`, `processed=7`, `failed=0`, `errors=[]` |
| Step `transaction_outbox_intent_settle` | `polled=0`, `processed=0` |

---

## 2. Flags runtime (container ECS lecture seule)

| Variable | Valeur |
| --- | --- |
| `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` | `gaelitier@gmail.com` |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `true` |
| `LIFI_OUTBOX_WORKER_ENABLED` | **`true`** |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | **`false`** |

---

## 3. Les 4 outbox Étape 1 — état post-worker

| # | intent_id | swap_id | amount | paire | outbox status | processed_at (UTC) | current_phase | swap_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `cdf189b0-…` | `547b4518-…` | 5 USDC | USDC→ETH | **processed** | 00:27:29 | **QUEUED** | EXPIRED |
| 2 | `c1ab777f-…` | `8607603e-…` | 1 USDC | USDC→AAVE | **processed** | 00:27:29 | **QUEUED** | EXPIRED |
| 3 | `3a273f76-…` | `34321a6c-…` | 1 USDC | USDC→AAVE | **processed** | 00:27:29 | **QUEUED** | EXPIRED |
| 4 | `c294e8dd-…` | `996d490d-…` | 5 USDC | USDC→AAVE | **processed** | 00:27:29 | **QUEUED** | EXPIRED |

Tous : `person_id=8b0e0044-f1ef-47a5-99d4-370598a77492` · `phase2_orchestrator=true` · `attempt_count=0` · `last_error=null` · `tx_hash=null`.

---

## 4. Transitions (4 intents Étape 1)

Par intent : **+2 transitions worker** (`VALIDATED` puis `QUEUED`, actor `outbox_worker_intent_created`) en plus de la transition bootstrap `CREATED` (`atomic_bootstrap`).

| intent_id | VALIDATED @ UTC | QUEUED @ UTC |
| --- | --- | --- |
| `cdf189b0-…` | 00:27:28 | 00:27:28 |
| `c1ab777f-…` | 00:27:28 | 00:27:28 |
| `3a273f76-…` | 00:27:28 | 00:27:28 |
| `c294e8dd-…` | 00:27:28 | 00:27:28 |

**Total transitions worker sur les 4 intents** : 8 (`VALIDATED`×4 + `QUEUED`×4).

---

## 5. Compteurs économiques (Δ vs Étape 1)

| Métrique | Étape 1 | Étape 2 | Δ |
| --- | --- | --- | --- |
| `pe_position_atoms` | 19 | **19** | 0 |
| `cost_basis_executions` | 66 | **66** | 0 |
| `person_wallet_deposits` `lifi-swap:%` | 116 | **116** | 0 |
| Jambes ledger sur swaps pilot | 0 | **0** | 0 |
| `intent.settle` outbox | 0 | **0** | 0 |
| Outbox `dead_letter` pilot | 0 | **0** | 0 |
| Intents `COMPLETED` orchestrateur | 0 | **0** | 0 |
| Autres users `phase2_orchestrator` | 0 | **0** | 0 |

**Outbox global** : `intent.created` / `processed` = **7** (voir réserve R1).

---

## 6. Critères Go Étape 2

| Critère | Résultat |
| --- | --- |
| Worker ON, ledger OFF | ✅ |
| 4 outbox Étape 1 → `processed` | ✅ |
| 4 intents → `QUEUED` | ✅ |
| +2 transitions worker / intent | ✅ |
| 0 jambe ledger | ✅ |
| PE / cost basis inchangés | ✅ |
| 0 `intent.settle` | ✅ |
| 0 `dead_letter` | ✅ |
| 0 `COMPLETED` | ✅ |
| 0 autre user orchestrateur | ✅ |
| `swap_status` reste `QUOTE_RECEIVED` | ⚠️ **EXPIRED** sur les 4 (maintenance tick, pas worker) |
| Exactement 4 events traités | ⚠️ **7** traités (3 quotes hors périmètre préparation) |

---

## 7. Réserves

| # | Réserve | Impact |
| --- | --- | --- |
| **R1** | **3 quotes supplémentaires** pendant la fenêtre déploiement (~00:26–00:27 UTC), même compte pilote : 5 USDC→ETH, **50 USDC→ETH**, 5 USDC→ETH — toutes passées `QUEUED` | Hors scope préparation (4 pending) ; **50 USDC** hors discipline pilot 1–5 USDC |
| **R2** | `swap_status` des 4 quotes Étape 1 passé à **EXPIRED** (step `swap_maintenance` du tick DeFi, pas le worker S2b) | Attendu à la vérif était `QUOTE_RECEIVED` — écart documenté, sans effet économique |
| **R3** | Tick DeFi exit **2** (degraded) | Acceptable ops ; step outbox **succès** (`processed=7`, `failed=0`) |

Aucune réserve ne déclenche rollback : **aucune écriture économique**, critères STOP non atteints.

---

## 8. Décision

| Verdict | Justification |
| --- | --- |
| **Étape 2 OK avec réserves** | Le worker S2b a traité les 4 `intent.created` pending en conditions réelles : `CREATED` → `VALIDATED` → `QUEUED`, outbox `processed`, zéro ledger / PE / cost basis / COMPLETED. Réserves : 3 quotes parasites (dont 50 USDC) et `swap_status` EXPIRED par maintenance. |

### STOP / rollback — non déclenché

| Trigger | Statut |
| --- | --- |
| Écriture ledger | ❌ Non |
| PE / cost basis Δ | ❌ Non |
| COMPLETED | ❌ Non |
| Autre user orchestrateur | ❌ Non |
| `dead_letter` inattendu | ❌ Non |

---

## Prochaine action (verrouillée)

**Pas Go Étape 3** sans feu vert explicite séparé.

Avant Étape 3 :

- **Stopper les quotes** tant que ledger OFF (discipline renforcée après R1).
- Ignorer les 3 intents parasites (déjà `QUEUED`, sans settlement).

Quand Go Étape 3 :

```bash
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=true
# worker + allowlist + orchestrateur restent ON
```

Puis **1 swap on-chain 1 USDC** Base confirmé — pas les quotes EXPIRED/parasites.

**Inchangé** : S3 Controller verrouillé · S4 avant élargissement allowlist.

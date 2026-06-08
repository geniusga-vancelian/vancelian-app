# Runbook — Activation contrôlée Global User Transaction Lock (legacy WebApp)

| Champ | Valeur |
| --- | --- |
| **Version** | 1.0 |
| **Date** | 2026-06-08 |
| **Prérequis code** | PR #61 mergé · TD `:161`+ |
| **Flag** | `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` |
| **Défaut prod** | **absent / false** (no-op) |

---

## Doctrine

**1 user = 1 transaction financière active** — le 2e invest Bundle (même user, portfolio différent) doit recevoir :

```json
HTTP 409
{
  "status": "transaction_in_progress",
  "error_code": "transaction_in_progress",
  "message": "A transaction is already in progress. Please wait until it is completed."
}
```

---

## Prérequis GO activation (tous requis)

| # | Gate | Vérification |
| --- | --- | --- |
| G1 | Recovery 4 batches | `stuck_count = 0` dans audit 4 batches |
| G2 | Aucun global lock zombie | `financial_transaction_global_locks_active = 0` |
| G3 | Dead letter | `dead_letter_count = 0` |
| G4 | Health | `GET /health` → 200 |
| G5 | GO CTO explicite | Documenté dans ce runbook |
| G6 | Aucun nouvel invest en cours | Utilisateur informé |

**Script pré-activation** :

```bash
LEGACY_GLOBAL_LOCK_VERIFY_MODE=pre_activation \
  ./scripts/arquantix-ecs-legacy-global-lock-activation-verify.sh
```

Attendu : `go_activation: true` · `stuck_bundle_parents: 0`.

**État 2026-06-08T17:40Z** : `go_activation: false` (10 parents stuck · 4 batches incident).

---

## Phase 0 — Stabilisation (EN COURS)

1. **STOP** tout nouvel invest Bundle.
2. Recovery UI — voir [GO_BUNDLE_INCIDENT_RECOVERY_4_BATCHES_REPORT.md](GO_BUNDLE_INCIDENT_RECOVERY_4_BATCHES_REPORT.md).
3. Audit après **chaque** batch :

```bash
./scripts/arquantix-ecs-bundle-incident-4-batches-audit.sh
```

4. Quand `summary.stuck_count = 0` → passer Phase 1.

---

## Phase 1 — Activation flag (GO CTO requis)

### 1.1 Mise à jour TD ECS

Ajouter **uniquement** sur le container `arquantix-api` :

```
GLOBAL_USER_TRANSACTION_LOCK_ENABLED=true
```

**Ne pas** activer d'autres flags (B4b, B5, dual-run, funding handler, etc.).

### 1.2 Deploy

- Attendre rollout ECS stable (service `arquantix-api` healthy).
- Vérifier TD révision déployée.

### 1.3 Verify post-deploy immédiat

```bash
LEGACY_GLOBAL_LOCK_VERIFY_MODE=post_activation \
  ./scripts/arquantix-ecs-legacy-global-lock-activation-verify.sh
```

Attendu :

- `flag_global_lock_on: true`
- `health_ok: true`
- `financial_transaction_global_locks_active: 0`
- `dead_letter_count: 0`

---

## Phase 2 — Test WebApp 409 (manuel · compte pilote)

| Étape | Action | Attendu |
| --- | --- | --- |
| T1 | Invest **1 USDC** portfolio A (ex. Crypto Majors) | Démarre · global lock acquis |
| T2 | Pendant actif, invest **1 USDC** portfolio B (ex. Two Crypto Kings) | **409** · pas de batch · pas de swap |
| T3 | Message UI/API | Texte user-safe (pas d'intent_id) |
| T4 | Terminer ou annuler invest A via UI | Terminal · global lock released |
| T5 | Invest B après release | Autorisé |

**Audit post-test** :

```bash
./scripts/arquantix-ecs-bundle-incident-4-batches-audit.sh
LEGACY_GLOBAL_LOCK_VERIFY_MODE=post_activation \
  ./scripts/arquantix-ecs-legacy-global-lock-activation-verify.sh
```

---

## Critères GO post-activation

| Critère | Assertion |
| --- | --- |
| 2e invest bloqué | HTTP 409 `transaction_in_progress` |
| Pas de batch 2e invest | Aucun parent créé pour tentative B |
| Pas de swap 2e invest | Aucun swap bundle_execution pour B |
| 1er invest resume OK | Idempotent acquire même intent |
| Release terminal | `active_global_lock_count = 0` après finish |
| Dead letter | 0 |
| Double PE/CB | Aucun delta anormal sur tentative bloquée |

---

## Rollback flag

Si 500, blocage inattendu, ou invest impossible :

1. `GLOBAL_USER_TRANSACTION_LOCK_ENABLED=false` (ou retirer variable TD).
2. Redeploy / rollback TD précédente.
3. Verify health 200 + `flag_global_lock_on: false`.
4. **Pas** de cleanup DB sans rapport incident.
5. Documenter dans recovery report.

---

## Scripts ops

| Script | Rôle |
| --- | --- |
| `arquantix-ecs-bundle-incident-4-batches-audit.sh` | Audit 4 batches + métriques globales |
| `arquantix-ecs-legacy-global-lock-activation-verify.sh` | Pré/post activation gates |
| `arquantix-ecs-bundle-legacy-global-lock-controlled-test.sh` | Test 409 job-only (flag ON en job) |

---

## Séquence complète (résumé)

```
Recovery 4 batches (UI, séquentiel)
  → audit stuck_count=0
  → pre_activation verify go_activation=true
  → GO CTO
  → TD GLOBAL_USER_TRANSACTION_LOCK_ENABLED=true
  → post_activation verify
  → test WebApp 409 manuel 1 USDC A + B
  → audit final
  → GO WebApp Bundle 1 USDC réel
```

---

## Interdictions

- Pas de B4b / B5 / WebApp test plan tant que Phase 0 incomplete.
- Pas d'activation flag avant `go_activation: true`.
- Pas de recovery parallèle deux batches.
- Pas de cleanup DB automatique.
- Pas de worker tick / settlement sans audit.

---

## Changelog

| Date | Action |
| --- | --- |
| 2026-06-08 | Runbook initial · audit 4 batches · pre_activation `go_activation: false` |

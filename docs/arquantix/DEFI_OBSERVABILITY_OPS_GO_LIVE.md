# Mise en service Ops — tick observabilité DeFi (production)

**Audience :** DevOps/SRE, ops admin.  
**Prérequis :** stack transactionnelle DeFi déployée (migrations 161–168, API + portail admin).  
**Hors périmètre :** alerting Slack/email (Phase 11), daemon applicatif, apply automatique.

Documents liés :

| Document | Rôle |
| --- | --- |
| [`DEFI_OBSERVABILITY_RUNBOOK.md`](DEFI_OBSERVABILITY_RUNBOOK.md) | Tick, tables, alertes JSON |
| [`DEFI_OBSERVABILITY_PROD_RUNBOOK.md`](DEFI_OBSERVABILITY_PROD_RUNBOOK.md) | Lock, timeout, SQL diagnostic |
| [`DEFI_TRANSACTION_ARCHITECTURE.md`](DEFI_TRANSACTION_ARCHITECTURE.md) | Architecture complète |
| [`ONCHAIN_INDEXER_BASE.md`](ONCHAIN_INDEXER_BASE.md) | Variables indexer |

---

## 1. Audit court (état au go-live)

| Élément | État | Notes |
| --- | --- | --- |
| Script tick | OK | `services/arquantix/api/scripts/defi_observability_tick.py` |
| Wrapper ops | OK | `scripts/run_defi_observability_tick_prod.sh` (pré-vols + exécution) |
| Orchestration | OK | `services/defi_observability/tick_service.py` — indexer → health → reconcile users |
| Verrou prod | OK | `pg_try_advisory_lock` — second run → `skipped_locked`, **exit 0** |
| Job runs | OK | Table `defi_observability_job_runs`, migration 168 |
| Admin API | OK | `GET /api/admin/onchain-reconciliation/jobs`, `/health`, `/discrepancies`, … |
| Admin UI | OK | `/admin/onchain-reconciliation/{jobs,health,intents}` + discrepancies |
| Mocks prod API | OK | `enforce_production_mock_guard` au boot — `LIFI_SWAPS_MOCK`, `BUNDLE_LIFI_SYNC_MOCK` interdits |
| Mocks prod Web | OK | `productionSandboxGuard.ts` (instrumentation Next.js) |
| Cron prod réel | **À activer** | Documenté ; pas de scheduler intégré dans l’API |
| `ONCHAIN_INDEXER_BASE_ENABLED` | **À vérifier** | Défaut `false` — **obligatoire `true` sur l’hôte du tick** pour écrire `raw_onchain_events` |
| RPC Base | **À vérifier** | `BASE_RPC_URL` / `BASE_RPC_URL_PRIMARY` / `NEXT_PUBLIC_BASE_RPC_URL` (première non vide) |

**Écritures autorisées en `--no-dry-run` uniquement :**

- `raw_onchain_events`, `onchain_indexer_checkpoints`
- `reconciliation_discrepancies` (détection, pas d’apply)
- `defi_observability_job_runs`

**Jamais via le tick :** balances, dépôts, `correction apply`, rebuild ledger, stale intent auto-fix.

---

## 2. Variables d’environnement (hôte d’exécution du tick)

Le tick s’exécute **hors** du cycle requête HTTP. Il doit voir la **même** `DATABASE_URL` que l’API prod.

| Variable | Obligatoire | Prod |
| --- | --- | --- |
| `DATABASE_URL` | Oui | Identique API |
| `ONCHAIN_INDEXER_BASE_ENABLED` | Oui pour indexer | `true` |
| `BASE_RPC_URL` (ou alias) | Oui pour indexer | URL RPC Base valide |
| `ONCHAIN_INDEXER_BASE_START_BLOCK` | Si pas de checkpoint | Bloc initial (une fois) |
| `APP_ENV` / `ENV` | Recommandé | `production` si garde-fous mock locaux |
| `DEFI_OPS_OPEN_P0_THRESHOLD` | Non | Défaut `3` |
| `DEFI_OPS_OPEN_P1_THRESHOLD` | Non | Défaut `10` |
| `INTENT_TTL_*_MINUTES` | Non | TTL stale (Phase 8) |

**Interdit en production (tick ou API) :**

- `LIFI_SWAPS_MOCK=1`
- `BUNDLE_LIFI_SYNC_MOCK=1`

---

## 3. Cron externe (recommandation)

### Fréquence

| Option | Crontab | `--max-duration-seconds` | Commentaire |
| --- | --- | --- | --- |
| **Recommandé** | `*/10 * * * *` | `480` | Marge si tick ~5–8 min |
| Alternative | `*/5 * * * *` | `240` | Plus réactif ; surveiller `skipped_locked` |

Règle : `max-duration` **<** intervalle cron (ex. 8 min tick, 10 min cron).

### Chevauchement / idempotence

- Un seul tick `--no-dry-run` actif : verrou advisory PostgreSQL.
- Run concurrent : `job_run.status = skipped_locked`, **code sortie 0** — le cron ne doit **pas** alerter comme une panne.
- `skipped_locked` répété sur **plusieurs créneaux** : le tick précédent dure trop long ou est bloqué → voir §6.3.

### Exemple crontab (bastion / ops host)

```cron
*/10 * * * * /path/to/vancelian-app/scripts/run_defi_observability_tick_prod.sh --execute >> /var/log/arquantix-defi-obs.log 2>&1
```

Le wrapper charge `.env.arquantix` (repo root), vérifie `DATABASE_URL`, RPC, indexer enabled, mocks, puis lance :

```bash
python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480
```

### Alternative : one-shot ECS (sans crontab sur bastion)

Même image / secrets que `arquantix-api` :

```bash
./scripts/run_defi_observability_tick_prod.sh --ecs-once
```

Prérequis ECS : `DATABASE_URL`, `BASE_RPC_URL*`, **`ONCHAIN_INDEXER_BASE_ENABLED=true`** sur la task definition (sinon indexer en erreur / pas d’écriture events).

Pour un cron ECS : EventBridge → `RunTask` avec la même commande (hors scope implémentation — documenter chez l’équipe infra).

### Codes de sortie (monitoring cron)

| Code | Interprétation | Action cron |
| --- | --- | --- |
| `0` | success ou `skipped_locked` | OK |
| `2` | degraded / `timeout_degraded` / alertes ops | Log + revue admin jobs (pas page ops) |
| `1` | erreur fatale | Incident §6 |

---

## 4. Procédure — premier run production

### 4.1 Avant le run

1. **API stable** : `GET https://<api-host>/health` → 200.
2. **Migrations** : Alembic à tête **168** sur la base prod (déjà fait au deploy API récent).
3. **Variables tick** (bastion ou ECS) :
   ```bash
   # Depuis repo root, après source .env.arquantix ou export manuel
   test -n "$DATABASE_URL"
   test "$(echo "${ONCHAIN_INDEXER_BASE_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')" = "true"
   test -n "${BASE_RPC_URL:-${BASE_RPC_URL_PRIMARY:-}}"
   ```
4. **Mocks** : aucun flag mock truthy (voir §2).
5. **Admin UI** (session admin) — état **avant** :
   - [Jobs](https://app.vancelian.finance/admin/onchain-reconciliation/jobs) — liste vide ou runs tests
   - [Health](https://app.vancelian.finance/admin/onchain-reconciliation/health)
   - [Intents](https://app.vancelian.finance/admin/onchain-reconciliation/intents)
   - [Discrepancies](https://app.vancelian.finance/admin/onchain-reconciliation)

6. **API lecture** (token admin) :
   ```bash
   curl -sS -H "Authorization: Bearer <ADMIN_TOKEN>" \
     "https://<api-host>/api/admin/onchain-reconciliation/health" | jq '.overall_status, .counts'
   ```

### 4.2 Dry-run prod (obligatoire avant `--no-dry-run`)

```bash
cd /path/to/vancelian-app
./scripts/run_defi_observability_tick_prod.sh
# ou :
cd services/arquantix/api
python3 -m scripts.defi_observability_tick --dry-run
```

Vérifier dans le JSON stdout : pas d’exception, `summary.indexer` cohérent, `overall_status` compris.

### 4.3 Premier run écriture

```bash
./scripts/run_defi_observability_tick_prod.sh --execute
```

Équivalent manuel :

```bash
cd services/arquantix/api
python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480
```

**Un seul** run `--no-dry-run` à la fois.

### 4.4 Après le run

Suivre la **checklist §5** et consulter à nouveau les pages admin + :

```bash
curl -sS -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "https://<api-host>/api/admin/onchain-reconciliation/jobs?limit=5" | jq '.items[0]'
```

---

## 5. Checklist post-run

| # | Vérification | OK si |
| --- | --- | --- |
| 1 | Job run créé | Dernier run visible dans `/admin/onchain-reconciliation/jobs` |
| 2 | Statut terminal | `success`, `degraded`, `timeout_degraded`, `skipped_locked`, ou `error` (pas bloqué en `running` > 15 min) |
| 3 | Pas de mutation ledger | Aucun mouvement balance / dépôt non expliqué ; pas de `correction apply` auto |
| 4 | Pas de correction auto | Discrepancies éventuelles **ouvertes** en UI — traitement humain preview → approve → apply |
| 5 | Stale intents | Détectés dans `summary_json` / page health — **non** corrigés automatiquement par le tick |
| 6 | Indexer | Si enabled : `raw_onchain_events` progressent (SQL ou admin) ; checkpoint avance |
| 7 | Exit code script | `0` ou `2` documenté ; `1` → incident |
| 8 | Alertes JSON | `summary_json.alerts` lues ; pas d’escalade Slack tant que Phase 11 inactive |

Requête SQL rapide :

```sql
SELECT id, status, started_at, finished_at,
       summary_json->>'overall_status' AS overall
FROM defi_observability_job_runs
ORDER BY started_at DESC
LIMIT 5;
```

---

## 6. Runbook incident minimal

### 6.1 Tick `failed` / exit `1`

| Étape | Action |
| --- | --- |
| 1 | Relire stderr / CloudWatch (`/ecs/arquantix-api` si ECS) |
| 2 | Dernier `job_run` : `error_json` dans admin jobs |
| 3 | Causes fréquentes : DB down, import Python, exception non catchée |
| 4 | **Ne pas** enchaîner plusieurs `--no-dry-run` en parallèle |
| 5 | Après fix : un seul `--dry-run` puis un seul `--execute` |

### 6.2 Tick `timeout_degraded` / exit `2`

- Le tick s’est arrêté **entre les étapes** (indexer partiel possible, checkpoint cohérent).
- Augmenter `--max-duration-seconds` ou réduire `--max-users` / fenêtre `--user-hours`.
- Pas d’apply auto.

### 6.3 `skipped_locked` répété (≥ 3 créneaux cron)

| Cause probable | Action |
| --- | --- |
| Tick précédent > intervalle cron | Augmenter intervalle ou `max-duration` |
| Process zombie / connexion DB bloquée | Identifier session PostgreSQL sur lock advisory ; tuer **uniquement** après validation DBA |
| Cron doublon (2 hôtes) | Un seul crontab prod |

### 6.4 DB unavailable

- Exit `1`, API `/health` peut aussi échouer.
- Rétablir RDS / réseau ; **ne pas** recréer de base parallèle.
- Reprendre avec `--dry-run` puis `--execute`.

### 6.5 RPC Base unavailable

- Alertes `indexer_rpc_error` / step indexer failed.
- Vérifier `BASE_RPC_URL*`, quotas Alchemy, connectivité depuis l’hôte du tick.
- Test : `python3 -m scripts.run_onchain_indexer --once --dry-run` (même env).

### 6.6 Migration / schema mismatch

- Symptôme : erreur SQL `relation does not exist`, Alembic en retard.
- **Corriger le deploy API** (migrations 161–168), pas de contournement DB alternative.
- Vérifier `alembic current` sur la base prod.

### 6.7 Volume anormal de discrepancies

- Admin discrepancies : tri P0/P1, corrélation `person_id` / produit.
- Alertes `open_discrepancies_p0_high` / `p1_high` dans `summary_json`.
- **Workflow manuel** uniquement ; pas de script apply de masse.

### 6.8 `raw_onchain_events` absents

- `ONCHAIN_INDEXER_BASE_ENABLED=false` sur l’hôte du tick → activer et relancer.
- RPC manquant → configurer `BASE_RPC_URL`.
- Checkpoint / `START_BLOCK` : voir `ONCHAIN_INDEXER_BASE.md`.

### 6.9 Health admin `degraded`

- Page `/admin/onchain-reconciliation/health` : stale intents, counts ouverts.
- Distinction **ops** (indexer RPC) vs **métier** (intents bloqués) — pas de correction auto tick.

---

## 7. Commandes de test

### Local (stack dev, sans toucher prod)

```bash
cd services/arquantix/api
python3 -m alembic upgrade head
python3 -m pytest tests/test_phase9_defi_observability_tick.py \
  tests/test_phase10_defi_observability_prod.py -q
python3 -m scripts.defi_observability_tick --dry-run
```

### Prod — lecture seule

```bash
./scripts/run_defi_observability_tick_prod.sh
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$API_BASE/api/admin/onchain-reconciliation/jobs?limit=3"
```

### Prod — exécution (go-live)

```bash
./scripts/run_defi_observability_tick_prod.sh --execute
```

### Prod — ECS one-shot

```bash
./scripts/run_defi_observability_tick_prod.sh --ecs-once
```

---

## 8. Recommandation finale : prêt pour cron prod ?

| Critère | Statut |
| --- | --- |
| Code + migrations en prod | Oui (si API deploy récent OK) |
| Tick manuel `--no-dry-run` testé | **À valider** par ops (1er run §4) |
| `ONCHAIN_INDEXER_BASE_ENABLED` + RPC sur hôte cron | **À configurer** |
| Cron / EventBridge installé | **Non** — prochaine action infra |
| Alerting Slack/email | Non (Phase 11 après cron réel) |

**Verdict :** **Prêt pour cron prod = OUI côté logiciel**, sous réserve de :

1. Premier run manuel réussi (§4–5).
2. Variables indexer + RPC sur **le même environnement** que le cron.
3. Un seul scheduler (bastion **ou** ECS, pas les deux sans coordination).

Ensuite seulement : Phase 11 alerting (webhook / email), pour éviter des alertes sans exécution réelle.

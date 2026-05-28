# Runbook prod — observabilité DeFi (Phase 10)

Complète le runbook opérationnel : [`DEFI_OBSERVABILITY_RUNBOOK.md`](DEFI_OBSERVABILITY_RUNBOOK.md).

**Mise en service cron / premier run prod :** [`DEFI_OBSERVABILITY_OPS_GO_LIVE.md`](DEFI_OBSERVABILITY_OPS_GO_LIVE.md) (checklist, incidents, wrapper `scripts/run_defi_observability_tick_prod.sh`).

## Principes prod

- **Pas de daemon** applicatif — cron externe uniquement.
- **Pas d’apply automatique** — corrections admin manuelles uniquement.
- **Pas de mutation financière** — balances, dépôts, correction apply, rebuild interdits dans le tick.
- **Un seul tick `--no-dry-run`** à la fois (verrou advisory PostgreSQL).

## Variables d’environnement obligatoires


| Variable       | Rôle                                       |
| -------------- | ------------------------------------------ |
| `DATABASE_URL` | Connexion PostgreSQL (même base que l’API) |


## Variables optionnelles (indexer)


| Variable                       | Défaut / note                                  |
| ------------------------------ | ---------------------------------------------- |
| `ONCHAIN_INDEXER_BASE_ENABLED` | `true` en prod pour écrire events + checkpoint |
| `ONCHAIN_INDEXER_BASE_RPC_URL` | RPC Base (ou équivalent config indexer)        |
| `ONCHAIN_INDEXER_BASE_*`       | Voir config `BaseIndexerConfig`                |


## Variables optionnelles (tick / alertes)


| Variable                     | Défaut         | Rôle                         |
| ---------------------------- | -------------- | ---------------------------- |
| `DEFI_OPS_OPEN_P0_THRESHOLD` | `3`            | Alerte si P0 ouverts ≥ seuil |
| `DEFI_OPS_OPEN_P1_THRESHOLD` | `10`           | Alerte si P1 ouverts ≥ seuil |
| `INTENT_TTL_*_MINUTES`       | (voir Phase 8) | TTL stale par statut intent  |


## Seuils recommandés (prod)


| Paramètre                    | Recommandation                |
| ---------------------------- | ----------------------------- |
| Cron                         | `*/10 * * * *` (10 min)       |
| `--max-duration-seconds`     | `480` (8 min) si cron 10 min  |
| `--max-users`                | `25`                          |
| `--user-hours`               | `48`                          |
| `DEFI_OPS_OPEN_P0_THRESHOLD` | `3` (ajuster si volume élevé) |
| `DEFI_OPS_OPEN_P1_THRESHOLD` | `10`                          |


## Commandes prod

```bash
cd services/arquantix/api

# Lecture seule (audit / debug)
python3 -m scripts.defi_observability_tick --dry-run

# Tick prod (écritures autorisées uniquement : raw events, checkpoints, discrepancies, job_runs)
python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480
```

### Codes de sortie


| Code | Signification                                                            |
| ---- | ------------------------------------------------------------------------ |
| `0`  | success, ou **skipped_locked** (autre tick en cours — pas d’erreur cron) |
| `2`  | degraded / **timeout_degraded** / alertes ops                            |
| `1`  | error fatal                                                              |


## Exemple cron externe

Recommandé (pré-vols env + mocks) :

```cron
*/10 * * * * /path/to/vancelian-app/scripts/run_defi_observability_tick_prod.sh --execute >> /var/log/arquantix-defi-obs.log 2>&1
```

Équivalent direct :

```cron
*/10 * * * * cd /path/to/vancelian-app/services/arquantix/api && /usr/bin/python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480 >> /var/log/arquantix-defi-obs.log 2>&1
```

Si le tick précédent est encore en cours, le run suivant enregistre `skipped_locked` et sort `0` (pas de double exécution).

## Admin


| Page          | URL                                    |
| ------------- | -------------------------------------- |
| Jobs          | `/admin/onchain-reconciliation/jobs`   |
| Santé intents | `/admin/onchain-reconciliation/health` |
| Intents       | `/admin/onchain-reconciliation/intents` |
| Discrepancies | `/admin/onchain-reconciliation`        |

Incidents détaillés (tick failed, timeout, DB/RPC, schema, flood P0) : [`DEFI_OBSERVABILITY_OPS_GO_LIVE.md` §6](DEFI_OBSERVABILITY_OPS_GO_LIVE.md#6-runbook-incident-minimal).


Statuts job : `success`, `degraded`, `error`, `skipped_locked`, `timeout_degraded`, `running`.

## Procédures incident

### Indexer down / désactivé

1. Vérifier `ONCHAIN_INDEXER_BASE_ENABLED` et logs RPC.
2. `python3 -m scripts.defi_observability_tick --dry-run` — inspecter `summary.indexer`.
3. Admin jobs : runs récents `degraded` + alerte `indexer_step_failed` / `indexer_rpc_error`.
4. **Ne pas** activer apply auto — indexer peut être relancé manuellement :
  ```bash
   python3 -m scripts.run_onchain_indexer --once
  ```
5. Une fois RPC OK, relancer `--no-dry-run` (un seul à la fois).

### RPC degraded (latence / erreurs sporadiques)

1. Compter `indexer.errors` dans `summary_json` des derniers job_runs.
2. Si dégradé mais health OK : traiter en **degraded** ops, pas P0 métier.
3. Augmenter temporairement `--max-duration-seconds` si timeouts fréquents.
4. Vérifier fournisseur RPC / rate limits.

### Flood P0 / P1

1. SQL diagnostic (voir ci-dessous) — identifier produit / person_id.
2. Admin discrepancies : tri par sévérité, **correction manuelle** uniquement.
3. Si seuil alerte déclenché : `open_discrepancies_p0_high` / `open_discrepancies_p1_high` dans `summary_json.alerts`.
4. **Jamais** `correction apply` en masse via tick.

### Rollback safe

Le tick **ne modifie pas** balances ni dépôts. En cas de mauvaise exécution :

1. **Ne pas** supprimer checkpoints sans analyse — risque re-indexation doublons (idempotence dépend du code indexer).
2. Discrepancies créées par erreur : fermer / annoter en admin (`status` ≠ open), pas de script apply auto.
3. `defi_observability_job_runs` : historique audit — conserver.
4. Si transaction DB partielle improbable (tick = une transaction commit en fin) : vérifier dernier `job_run` `error` vs `success`.

## Diagnostic SQL

```sql
-- Derniers ticks
SELECT id, status, started_at, finished_at,
       (summary_json->>'overall_status') AS overall,
       (summary_json->'steps') AS steps
FROM defi_observability_job_runs
ORDER BY started_at DESC
LIMIT 20;

-- Runs skipped / timeout
SELECT id, status, started_at, summary_json->>'reason' AS reason
FROM defi_observability_job_runs
WHERE status IN ('skipped_locked', 'timeout_degraded')
ORDER BY started_at DESC
LIMIT 10;

-- P0/P1 ouverts
SELECT severity, status, layer, count(*)
FROM reconciliation_discrepancies
WHERE status = 'open' AND severity IN ('P0', 'P1')
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC;

-- Intents stale Lombard / Bundle (aperçu)
SELECT product_type, status, count(*)
FROM transaction_intents
WHERE updated_at < now() - interval '2 hours'
  AND status NOT IN ('confirmed', 'failed', 'cancelled')
  AND product_type IN ('lombard_borrow', 'bundle_invest')
GROUP BY 1, 2;
```

## Verrou anti-concurrence

- Mécanisme : `pg_try_advisory_lock` (session PostgreSQL).
- Deux ticks `--no-dry-run` simultanés : le second crée `job_run` `**skipped_locked**`, exit `**0**`.
- Le verrou est libéré à la fin du script (succès, degraded, timeout ou exception).

## Timeout (`--max-duration-seconds`)

- Arrêt **entre les étapes** (indexer → health → reconcile users).
- Statut : `**timeout_degraded`** — pas d’interruption au milieu d’un appel indexer (checkpoint cohérent).
- Exit code `**2**` (comme degraded).

## Rappel absolu

**Jamais d’apply automatique** via ce pipeline. Le tick observe, indexe, signale ; les corrections passent par l’admin humain.

## Phase 11 proposée

Alerting Slack / email **optionnel**, feature-flag (`DEFI_OPS_ALERT_WEBHOOK_URL`), sans apply auto ni daemon.
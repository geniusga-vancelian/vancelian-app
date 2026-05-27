# Runbook observabilité DeFi (Phase 9)

## Objectif

Orchestrer **un tick** d’observabilité sans daemon applicatif :

1. Indexer Base `--once` (raw_onchain_events + checkpoint)
2. Santé transaction_intents + stale TTL
3. Réconciliation utilisateurs actifs récents (discrepancies uniquement)

**Aucune** correction automatique, **aucune** mutation balances / dépôts / apply.

## Commande unique

Depuis `services/arquantix/api` :

```bash
# Défaut — lecture seule, résumé JSON stdout
python3 -m scripts.defi_observability_tick --dry-run

# Écritures autorisées uniquement :
# - raw_onchain_events
# - onchain_indexer_checkpoints
# - reconciliation_discrepancies (layer=intent + autres layers existants)
# - defi_observability_job_runs
python3 -m scripts.defi_observability_tick --no-dry-run

# Limiter le périmètre users
python3 -m scripts.defi_observability_tick --no-dry-run --max-users 10 --user-hours 72

# Prod : timeout + verrou anti-concurrence (Phase 10)
python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480
```

Codes de sortie :

- `0` — success, ou `skipped_locked` (autre tick en cours)
- `2` — degraded / `timeout_degraded` / alertes ops
- `1` — error fatal

Runbook prod détaillé : [`DEFI_OBSERVABILITY_PROD_RUNBOOK.md`](DEFI_OBSERVABILITY_PROD_RUNBOOK.md).

## Cron externe (exemple)

**Ne pas** intégrer de daemon dans l’API. Exemple crontab ops :

```cron
*/10 * * * * cd /path/to/vancelian-app/services/arquantix/api && /usr/bin/python3 -m scripts.defi_observability_tick --no-dry-run >> /var/log/arquantix-defi-obs.log 2>&1
```

Prérequis :

- `.env` / `DATABASE_URL` identiques à l’environnement cible
- `ONCHAIN_INDEXER_BASE_ENABLED=true` si écriture indexer souhaitée
- RPC Base configuré (`ONCHAIN_INDEXER_BASE_*`)

## Tables

### `defi_observability_job_runs`

| Colonne | Description |
| --- | --- |
| `job_name` | `defi_observability_tick` |
| `status` | `running` → `success` / `degraded` / `error` / `skipped_locked` / `timeout_degraded` |
| `summary_json` | Résumé complet (indexer, health, users, alerts) |
| `error_json` | Erreurs step / traceback |

Migration : `168_defi_observability_job_runs`

## Admin UI

| Page | URL |
| --- | --- |
| Santé intents | `/admin/onchain-reconciliation/health` |
| Historique jobs | `/admin/onchain-reconciliation/jobs` |
| Intents | `/admin/onchain-reconciliation/intents` |
| Discrepancies | `/admin/onchain-reconciliation` |

API :

- `GET /api/admin/onchain-reconciliation/health`
- `GET /api/admin/onchain-reconciliation/jobs`
- `POST /api/admin/onchain-reconciliation/health/reconcile-stale?dry_run=false`

## Alertes ops (logs + UI, pas Slack/email)

Seuils env optionnels :

- `DEFI_OPS_OPEN_P0_THRESHOLD` (défaut 3)
- `DEFI_OPS_OPEN_P1_THRESHOLD` (défaut 10)

Alertes générées dans `summary_json.alerts` :

| Code | Condition |
| --- | --- |
| `indexer_rpc_error` | Erreurs RPC indexer |
| `indexer_step_failed` | Step indexer exception |
| `stale_intent_p1` | Intent stale Lombard/Bundle (P1) |
| `open_discrepancies_p0_high` | Trop de P0 ouverts |
| `open_discrepancies_p1_high` | Trop de P1 ouverts |

## Users « actifs récents »

Proxy : `person_id` avec `transaction_intents.updated_at` dans les `--user-hours` dernières heures (défaut 48 h), max `--max-users` (défaut 25).

Pour une personne ciblée, utiliser toujours :

```bash
python3 -m scripts.reconcile_user --person-id <UUID> --no-dry-run
```

## Tests

```bash
cd services/arquantix/api
python3 -m alembic upgrade head   # jusqu'à 168
python3 -m pytest tests/test_phase9_defi_observability_tick.py \
  tests/test_phase10_defi_observability_prod.py -q
```

## Phase 10 (branché)

- Verrou advisory PostgreSQL (`--no-dry-run` uniquement)
- `--max-duration-seconds` → `timeout_degraded`
- Runbook prod : [`DEFI_OBSERVABILITY_PROD_RUNBOOK.md`](DEFI_OBSERVABILITY_PROD_RUNBOOK.md)

## Phase 11 proposée

Alerting Slack/email optionnel (feature-flag), sans apply auto.

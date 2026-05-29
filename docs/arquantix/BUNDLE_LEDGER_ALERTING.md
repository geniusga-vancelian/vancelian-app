# Bundle Ledger — Alerting (Phase 4D)

Guide des seuils d'alerte pour l'exploitation quotidienne après activation limitée de `BUNDLE_LEDGER_HISTORY_ENABLED`.

---

## Vue d'ensemble

| Source | Outil |
|--------|-------|
| Health check quotidien | `scripts/check_bundle_ledger_health.py` |
| Smoke portfolio | `scripts/smoke_bundle_ledger_history.py` |
| Logs structurés | `bundle_ledger.*` dans logs API |
| Admin | `GET /api/admin/bundles/{id}/ledger/reconciliation` |

---

## Seuils recommandés

### Critique — action immédiate

| Signal | Seuil | Code alerte | Action |
|--------|-------|-------------|--------|
| Verdict réconciliation **DIFF** | **> 0** portfolio | `reconciliation_diff` | Rollback flag si post-activation ; investiguer PE vs ledger |
| Swap Li.FI confirmé sans entrée ledger | **> 0** | `orphan_confirmed_swap` | Backfill apply + vérif miroir Phase 4A |

### Warning — revue ops sous 24h

| Signal | Seuil | Code alerte | Action |
|--------|-------|-------------|--------|
| `ledger_history_fallback` (24h) après flag ON | **> 0** | `ledger_history_fallback` | Vérifier MATCH ; backfill ; ne pas élargir panel |
| Verdict **INCOMPLETE** | **> 0** | `reconciliation_incomplete` | Backfill dry-run → apply |
| Locks **expired** (invest + withdraw) | **> 5** / jour | `lock_expired` | `inspect_bundle_state` ; recovery runbook |

### Ops review

| Signal | Seuil | Code alerte | Action |
|--------|-------|-------------|--------|
| Withdraw **failed_partial** | **> 0** | `withdraw_failed_partial` | Finalize withdraw ; cash leg intacte — BUNDLE_RECOVERY_RUNBOOK |

---

## Health status agrégé

| `health_status` | Signification |
|-----------------|---------------|
| `ok` | Aucune alerte |
| `warning` | INCOMPLETE, fallbacks, locks expired |
| `critical` | DIFF ou orphan swap |

---

## Commandes monitoring

### Daily health check

```bash
cd services/arquantix/api

python3 -m scripts.check_bundle_ledger_health \
  --log-file /var/log/arquantix-api.log \
  --since-hours 24 \
  --fail-on-alert \
  --pretty
```

Sortie clé :

```json
{
  "active_bundle_portfolios": 42,
  "reconciliation_summary": { "MATCH": 40, "INCOMPLETE": 2, "DIFF": 0 },
  "log_metrics_24h": {
    "ledger_history_read": 120,
    "ledger_history_fallback": 0
  },
  "lock_summary": {
    "invest_lock_expired": 1,
    "withdraw_failed_partial": 0
  },
  "top_10_investigate": [...],
  "health_status": "ok",
  "alerts": []
}
```

### Smoke portfolio pilote

```bash
python3 -m scripts.smoke_bundle_ledger_history \
  --person-id <UUID> \
  --portfolio-id <UUID> \
  --pretty
```

Attendu : `"status": "PASS"`

### Grep logs (fallback manuel)

```bash
grep 'bundle_ledger.ledger_history_fallback' /var/log/arquantix-api.log | tail -20
grep 'bundle_ledger.ledger_reconciliation_diff' /var/log/arquantix-api.log | tail -20
```

---

## Escalade

1. **critical** → rollback flag + ticket incident
2. **warning** → backfill / reconcile dans la journée
3. **ops_review** → revue manuelle withdraw failed_partial

---

## Cron suggéré (staging / prod limitée)

```cron
# 07:00 UTC — health check
0 7 * * * cd /app/services/arquantix/api && python3 -m scripts.check_bundle_ledger_health --log-file /var/log/api.log --fail-on-alert >> /var/log/bundle-ledger-health.log 2>&1
```

---

## Documents liés

- [BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md](./BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md)
- [BUNDLE_RECOVERY_RUNBOOK.md](./BUNDLE_RECOVERY_RUNBOOK.md)
- [BUNDLE_LEDGER_RECONCILIATION.md](./BUNDLE_LEDGER_RECONCILIATION.md)

---

*Phase 4D — alerting ops. Pas d'activation globale sans panel MATCH.*

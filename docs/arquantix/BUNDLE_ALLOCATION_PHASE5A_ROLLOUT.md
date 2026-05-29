# Bundle Allocation Phase 5A — Rollout & Validation

Guide de déploiement progressif : buffer → staging parallel → prod limitée.

**Prérequis :** [BUNDLE_ALLOCATION_EXECUTION_ENGINE_PHASE5A.md](./BUNDLE_ALLOCATION_EXECUTION_ENGINE_PHASE5A.md)

---

## Configuration prod immédiate (recommandée)

```bash
BUNDLE_ALLOC_EXECUTION_BUFFER_USDC=1.0
BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=false
```

Effet :
- 1 USDC conservé en cash leg par invest
- Quotes séquentielles (comportement stable)
- Settlement PE réel actif (sans flag)

---

## Staging — activation parallel

```bash
BUNDLE_ALLOC_EXECUTION_BUFFER_USDC=1.0
BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=true
```

Validation obligatoire avant prod :

```bash
cd services/arquantix/api

# Read-only
python3 -m scripts.smoke_bundle_allocation_phase5a \
  --person-id <UUID> \
  --portfolio-id <UUID> \
  --fund-amount 1000 \
  --pretty

# Mock contrôlé (local/staging)
BUNDLE_LIFI_SYNC_MOCK=1 LIFI_SWAPS_MOCK=1 \
python3 -m scripts.smoke_bundle_allocation_phase5a \
  --person-id <UUID> \
  --portfolio-id <UUID> \
  --fund-amount 200 \
  --execute-mock \
  --pretty
```

Attendu : `"status": "PASS"`

---

## Critères d'activation parallel en prod

| Critère | Seuil |
|---------|-------|
| Smoke read-only | PASS sur panel 3 portfolios |
| Smoke mock staging | PASS Top 2 et Top 5 |
| `parallel_batch_completed` logs | Aucune erreur `fallback_to_sequential` récurrente |
| Quote latency p95 | < 2 s (batch complet) |
| EXPIRED quotes / 24h | 0 sur panel pilote |
| Cash résiduel moyen | ≈ buffer + dust (< 0.1 % fund) |
| Ledger DIFF | 0 sur panel |

**Ne pas activer parallel prod** si fallback séquentiel > 5 % des batchs sur 48 h staging.

---

## Métriques à surveiller

### Logs structurés (`bundle_allocation.*`)

| Event | Usage |
|-------|-------|
| `plan_created` | fund, buffer, allocatable, legs_count |
| `quote_started` / `quote_completed` | latence par leg |
| `parallel_batch_completed` | duration_ms, fallback_to_sequential |
| `settlement_real_amounts` | planned vs actual |
| `residual_cash` | post-invest reliquat |

### Grep ops

```bash
grep 'bundle_allocation.residual_cash' /var/log/arquantix-api.log | tail -20
grep 'bundle_allocation.parallel_batch_completed' /var/log/arquantix-api.log | tail -20
grep 'fallback_to_sequential": true' /var/log/arquantix-api.log | tail -20
```

### Champs clés JSON

`person_id`, `portfolio_id`, `batch_id`, `fund_amount`, `buffer_amount`, `allocatable_amount`, `legs_count`, `parallel_enabled`, `duration_ms`, `residual_cash`

---

## Rollback

| Action | Effet |
|--------|-------|
| `BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=false` | Quotes séquentielles immédiat |
| `BUNDLE_ALLOC_EXECUTION_BUFFER_USDC=0` | Désactive buffer |
| Restart API | Prise en compte flags |

Aucune migration DB. Cash leg et ledger intacts.

---

## Séquence rollout prod limitée

1. **Semaine 1** — buffer seul, 1 portfolio pilote
2. **Semaine 2** — buffer seul, 3 → 10 portfolios
3. **Staging** — parallel ON, smoke mock Top 5
4. **Semaine 3+** — parallel ON prod si critères OK, 1 portfolio canary
5. Élargir panel si métriques stables 7 jours

---

## Tests CI

```bash
cd services/arquantix/api
python3 -m pytest tests/test_bundle_allocation_phase5a.py \
  tests/test_bundle_allocation_phase5a_validation.py -q
```

---

## Documents liés

- [BUNDLE_ALLOCATION_EXECUTION_ENGINE_AUDIT.md](./BUNDLE_ALLOCATION_EXECUTION_ENGINE_AUDIT.md)
- [BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md](./BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md)
- [BUNDLE_LEDGER_ALERTING.md](./BUNDLE_LEDGER_ALERTING.md)

---

*Phase 5A.5 — validation avant parallel prod. Parallel OFF par défaut.*

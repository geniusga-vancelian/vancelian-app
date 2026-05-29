# Bundle Ledger — Go-live runbook (Phase 4C)

**Objectif :** activer progressivement l'historique bundle via ledger sur un **panel limité** de portfolios réels, avec monitoring et rollback simple.

**Ne pas activer globalement** tant que 1 → 3 → 10 portfolios n'ont pas produit `MATCH` de façon reproductible.

---

## Prérequis

- [ ] Migration **169** appliquée (`bundle_ledger_entries` existe)
- [ ] Phase 4A miroir actif (nouveaux flux écrivent dans le ledger)
- [ ] Tests CI Phase 4A/4B/4C verts
- [ ] Accès ops : `DATABASE_URL`, API locale ou staging
- [ ] Fichier panel portfolios (UUID par ligne)

Vérifier migration :

```bash
cd services/arquantix/api
python3 -m alembic current   # doit afficher 169 (head)
```

---

## Checklist avant activation (par portfolio)

- [ ] `inspect_bundle_state` — état nominal ou recoverable
- [ ] Backfill **dry-run** sans warnings bloquants
- [ ] Backfill **apply** si entrées manquantes
- [ ] Réconciliation **MATCH**
- [ ] Validation panel script → `rollout_ready: true`
- [ ] `BUNDLE_LEDGER_HISTORY_ENABLED=true` sur l'environnement cible
- [ ] Smoke test `GET /api/app/bundle/{portfolio_id}/transactions`
- [ ] Vérifier Mon Trading inchangé (transferts PE only)

---

## Commandes exactes

### 1. Inspection état

```bash
cd services/arquantix/api

python3 -m scripts.inspect_bundle_state \
  --person-id <PERSON_UUID> \
  --portfolio-id <PORTFOLIO_UUID> \
  --pretty
```

### 2. Backfill dry-run

```bash
python3 -m scripts.backfill_bundle_ledger \
  --person-id <PERSON_UUID> \
  --portfolio-id <PORTFOLIO_UUID> \
  --dry-run \
  --pretty
```

### 3. Backfill apply

```bash
python3 -m scripts.backfill_bundle_ledger \
  --person-id <PERSON_UUID> \
  --portfolio-id <PORTFOLIO_UUID> \
  --apply \
  --pretty \
  --fail-on-warning
```

### 4. Réconciliation MATCH

```bash
python3 -m scripts.reconcile_bundle_ledger_shadow \
  --person-id <PERSON_UUID> \
  --portfolio-id <PORTFOLIO_UUID> \
  --fail-on-diff \
  --pretty
```

Verdict attendu : **`MATCH`**

### 5. Validation panel (1, 3 ou 10 portfolios)

Créer `portfolios.txt` :

```
# portfolio UUIDs — un par ligne
aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```

```bash
python3 -m scripts.validate_bundle_ledger_rollout \
  --portfolio-ids portfolios.txt \
  --pretty

# Avec backfill apply sur tout le panel
python3 -m scripts.validate_bundle_ledger_rollout \
  --portfolio-ids portfolios.txt \
  --apply-backfill \
  --fail-on-diff \
  --pretty
```

Sortie cible :

```json
{
  "rollout_status": "ready",
  "summary": { "MATCH": 3, "INCOMPLETE": 0, "DIFF": 0 }
}
```

### 6. Activation flag (prod limitée)

Dans `.env` / config déploiement **staging ou prod limitée** :

```bash
BUNDLE_LEDGER_HISTORY_ENABLED=true
# BUNDLE_LEDGER_BACKFILL_DRY_RUN=true   # laisser true par défaut hors scripts apply
```

Redémarrer l'API. **Pas de flag global prod** tant que le panel élargi n'est pas vert.

### 7. Vérification admin

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8000/api/admin/bundles/<PORTFOLIO_UUID>/ledger/reconciliation"
```

Champs attendus :

- `verdict`: `MATCH`
- `current_history_source`: `ledger`
- `flag_enabled`: `true`
- `fallback_reason`: `null`
- `last_backfill_summary`: présent si apply exécuté

### 8. Smoke test app

```bash
curl -H "Authorization: Bearer <APP_TOKEN>" \
  "http://localhost:8000/api/app/bundle/<PORTFOLIO_UUID>/transactions"
```

Les transactions doivent avoir `source_system: bundle_ledger` si MATCH + flag ON.

---

## Checklist après activation

- [ ] Logs `ledger_history_read` présents (pas de `ledger_history_fallback` inattendu)
- [ ] Aucun `ledger_reconciliation_diff` en ERROR
- [ ] Historique bundle cohérent avec legacy (échantillon manuel)
- [ ] Mon Trading : aucun swap bundle interne visible
- [ ] Admin reconciliation reste `MATCH` après 24h

---

## Critères rollback

Rollback **immédiat** si :

| Signal | Action |
|--------|--------|
| `ledger_reconciliation_diff` en prod | `BUNDLE_LEDGER_HISTORY_ENABLED=false` |
| `ledger_history_fallback` massif | Rollback flag + investiguer |
| Plainte utilisateur historique bundle | Rollback flag (legacy reprend) |
| Verdict admin passe à `DIFF` | Rollback flag sur le portfolio / env |

### Rollback (1 commande config)

```bash
BUNDLE_LEDGER_HISTORY_ENABLED=false
```

Redémarrer l'API. **Aucune suppression** de `bundle_ledger_entries` requise. Fallback legacy automatique.

---

## Rollback détaillé (procédure ops)

### Quand rollback

- Alert `reconciliation_diff` (critique)
- `ledger_history_fallback` massif après activation flag
- Smoke test `FAIL` sur portfolio pilote
- Plainte utilisateur historique bundle incohérent

### Étapes (≈ 5 min)

**1. Désactiver le flag**

```bash
# .env / config déploiement / secret manager
BUNDLE_LEDGER_HISTORY_ENABLED=false
```

**2. Redémarrer l'API**

```bash
# Exemple Docker Compose — adapter à votre stack
docker compose restart arquantix-api
# ou rolling restart k8s / systemd
```

**3. Vérifier fallback legacy**

```bash
# Smoke — doit PASS (legacy history OK)
python3 -m scripts.smoke_bundle_ledger_history \
  --person-id <PERSON_UUID> \
  --portfolio-id <PORTFOLIO_UUID> \
  --pretty

# Admin — current_history_source doit être legacy
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8000/api/admin/bundles/<PORTFOLIO_UUID>/ledger/reconciliation"
# Attendu : "current_history_source": "legacy", "flag_enabled": false
```

**4. Vérifier Mon Trading inchangé**

- Aucun swap bundle interne visible
- Transferts PE `bundle_pe_transfer` toujours présents si applicable

**5. Conserver le ledger intact**

- **Ne jamais** `DELETE FROM bundle_ledger_entries`
- **Ne jamais** `UPDATE` destructif sur une entrée existante
- Correction comptable = entrée `BUNDLE_RECOVERY_ADJUSTMENT` / reversal append-only (Phase 4A)

**6. Post-mortem**

- Health check : `python3 -m scripts.check_bundle_ledger_health --pretty`
- Documenter cause (DIFF, backfill manquant, bug miroir)
- Re-backfill + reconcile MATCH avant réactivation flag

### Payload rollback attendu (admin)

```json
{
  "verdict": "MATCH",
  "flag_enabled": false,
  "current_history_source": "legacy",
  "fallback_reason": "flag_disabled",
  "history_switch": {
    "flag_enabled": false,
    "would_read_ledger": false
  }
}
```

Les entrées ledger **restent en base** pour audit et future réactivation.

---

## Stratégie panel progressive

| Étape | Portfolios | Critère go |
|-------|------------|------------|
| 1 | 1 portfolio pilote | MATCH + smoke OK 48h |
| 2 | 3 portfolios | Panel script `ready` |
| 3 | 10 portfolios | Panel script `ready` |
| 4 | Environnement élargi | Décision humaine — pas de flag global sans revue |

---

## Monitoring logs structurés

Événements émis (`bundle_ledger.*`) :

| Event | Niveau | Signification |
|-------|--------|---------------|
| `ledger_history_read` | INFO | Historique lu depuis ledger |
| `ledger_history_fallback` | WARN | Fallback legacy |
| `ledger_reconciliation_diff` | ERROR | Écart PE vs ledger |
| `bundle_backfill_applied` | INFO | Backfill apply OK |
| `bundle_backfill_warning` | WARN | Source ambiguë / intent sans audit |

Champs communs : `person_id`, `portfolio_id`, `verdict`, `fallback_reason`, `entries_count`

Filtrer logs :

```bash
# exemple
grep 'bundle_ledger.ledger_history_fallback' /var/log/arquantix-api.log
grep 'bundle_ledger.ledger_reconciliation_diff' /var/log/arquantix-api.log
```

---

## Verdicts panel

| Verdict | Rollout |
|---------|---------|
| **MATCH** | Prêt activation flag (prod limitée) |
| **INCOMPLETE** | Backfill apply puis re-valider |
| **DIFF** | **Not ready** — ne pas activer |

---

## Documents liés

- [BUNDLE_LEDGER_PHASE4A.md](./BUNDLE_LEDGER_PHASE4A.md)
- [BUNDLE_LEDGER_PHASE4B.md](./BUNDLE_LEDGER_PHASE4B.md)
- [BUNDLE_LEDGER_RECONCILIATION.md](./BUNDLE_LEDGER_RECONCILIATION.md)
- [BUNDLE_LEDGER_ALERTING.md](./BUNDLE_LEDGER_ALERTING.md)
- [BUNDLE_RECOVERY_RUNBOOK.md](./BUNDLE_RECOVERY_RUNBOOK.md)

---

## Phase 4D — exploitation quotidienne

```bash
# Health check daily
python3 -m scripts.check_bundle_ledger_health \
  --log-file /var/log/arquantix-api.log \
  --fail-on-alert --pretty

# Smoke portfolio pilote
python3 -m scripts.smoke_bundle_ledger_history \
  --person-id <UUID> --portfolio-id <UUID> --pretty
```

---

*Phase 4C — prod limitée only. Mon Trading inchangé. Balances PE inchangées. Fallback legacy conservé.*

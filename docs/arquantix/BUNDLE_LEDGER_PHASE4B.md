# Bundle Ledger — Phase 4B (read switch + backfill)

**Date :** 2026-05-29  
**Statut :** implémenté — backfill idempotent + switch lecture derrière feature flag

---

## Objectif

Faire de `bundle_ledger_entries` la **source prioritaire** de l'historique bundle (`GET /api/app/bundle/{portfolio_id}/transactions`), sans toucher Mon Trading ni les balances PE.

---

## Feature flags

| Variable | Défaut | Rôle |
|----------|--------|------|
| `BUNDLE_LEDGER_HISTORY_ENABLED` | `false` | Active la lecture historique depuis le ledger |
| `BUNDLE_LEDGER_BACKFILL_DRY_RUN` | `true` | Dry-run par défaut pour le script backfill |

**Ne pas activer `BUNDLE_LEDGER_HISTORY_ENABLED` globalement** tant que le backfill n'a pas produit `MATCH` sur un panel de portfolios réels.

---

## Procédure dry-run

```bash
cd services/arquantix/api

# 1. Réconciliation avant backfill
python3 -m scripts.reconcile_bundle_ledger_shadow \
  --person-id <UUID> --portfolio-id <UUID> --pretty

# 2. Plan backfill (aucune écriture)
python3 -m scripts.backfill_bundle_ledger \
  --person-id <UUID> \
  --portfolio-id <UUID> \
  --dry-run \
  --pretty
```

Sortie attendue :

- `planned_count` > 0 si entrées legacy manquantes
- `skipped_existing` pour entrées déjà miroir Phase 4A
- `warnings` — sources ambiguës (ne pas deviner)
- `reconciliation.verdict` après `--reconcile-after`

---

## Procédure apply

```bash
python3 -m scripts.backfill_bundle_ledger \
  --person-id <UUID> \
  --portfolio-id <UUID> \
  --apply \
  --pretty \
  --fail-on-warning
```

Puis re-vérifier :

```bash
python3 -m scripts.reconcile_bundle_ledger_shadow \
  --person-id <UUID> --portfolio-id <UUID> --fail-on-diff
```

**Verdict cible :** `MATCH`

---

## Critères activation flag

Activer `BUNDLE_LEDGER_HISTORY_ENABLED=true` **par environnement** uniquement si :

1. Backfill `--apply` exécuté sur les portfolios pilotes
2. Réconciliation `MATCH` sur chaque portfolio pilote
3. Tests CI Phase 4B verts
4. Panel ops validé (pas de `DIFF`)

Ordre recommandé :

1. Staging : backfill + flag ON pour 2–3 portfolios test
2. Prod limitée : flag ON après MATCH confirmé manuellement
3. Prod globale : uniquement après panel représentatif MATCH

---

## Comportement read switch

Quand `BUNDLE_LEDGER_HISTORY_ENABLED=true` :

| Verdict réconciliation | Comportement |
|------------------------|--------------|
| `MATCH` | Lit `bundle_ledger_entries` → format UI |
| `INCOMPLETE` | **Fallback legacy** (audit + swaps) |
| `DIFF` | **Fallback legacy** + log error |
| Ledger vide | **Fallback legacy** |

**Inchangé :**

- `get_crypto_transactions` (Mon Trading)
- `build_wallet_history` scope self-trading
- Atoms PE (balances)

---

## Rollback

1. `BUNDLE_LEDGER_HISTORY_ENABLED=false` — retour immédiat à la projection legacy
2. Aucune suppression de `bundle_ledger_entries` requise
3. Les entrées ledger restent disponibles pour audit / réconciliation

---

## Risques connus

| Risque | Mitigation |
|--------|------------|
| Legacy pre-4A sans ledger | Backfill `--apply` obligatoire |
| Swap sans `bundle_pe_atoms_applied` | Ignoré au backfill ; warning |
| Intent sans audit | Warning only — pas d'écriture devinée |
| `INCOMPLETE` avec flag ON | Fallback legacy automatique |
| Double écriture | Idempotence `idempotency_key` |

---

## Exemple de sortie backfill

```json
{
  "dry_run": true,
  "portfolio_id": "...",
  "planned_count": 3,
  "skipped_existing_count": 1,
  "planned": [
    {
      "action": "record_bundle_deposit",
      "idempotency_key": "pe_transfer:batch-uuid:fund:BUNDLE_DEPOSIT:credit",
      "source": "pe_audit_events"
    }
  ],
  "warnings": [],
  "reconciliation": {
    "verdict": "INCOMPLETE",
    "missing_ledger_entries": [...]
  }
}
```

Après `--apply` + backfill complet :

```json
{
  "reconciliation": {
    "verdict": "MATCH",
    "expected_cash_from_ledger": 45.0,
    "actual_cash_from_pe": 45.0
  }
}
```

---

## Fichiers livrés

| Fichier | Rôle |
|---------|------|
| `bundle_ledger/backfill.py` | Plan + apply idempotent |
| `bundle_ledger/history.py` | Format UI + switch flag |
| `bundle_ledger/config.py` | Feature flags |
| `scripts/backfill_bundle_ledger.py` | CLI ops |
| `tests/test_bundle_ledger_backfill.py` | Tests backfill |
| `tests/test_bundle_history_from_ledger.py` | Tests read switch |

---

## Validation portfolios (tests automatisés)

| Scénario | Verdict attendu |
|----------|-----------------|
| Dépôt seul post-4A | MATCH |
| Dépôt + allocation | MATCH |
| Allocation partielle | MATCH |
| Retrait partiel | MATCH |
| Audit legacy sans ledger (pre-backfill) | INCOMPLETE → fallback legacy |
| Ledger DIFF (mock) | fallback legacy |

Panel **réel** : exécuter reconcile + backfill dry-run sur vos portfolios prod limitée avant flag global.

---

*Phase 4B — Mon Trading inchangé. Balances PE inchangées. Historique bundle = ledger quand MATCH.*

---

## Phase 4C — prod limitée

Voir [BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md](./BUNDLE_LEDGER_GO_LIVE_RUNBOOK.md) pour le rollout panel, monitoring et rollback.

# Bundle Ledger — Réconciliation shadow (Phase 4A.5)

**Date :** 2026-05-29  
**Objectif :** prouver que `bundle_ledger_entries` raconte la même histoire que PE + Li.FI **avant** Phase 4B.

---

## Pourquoi cette phase

Phase 4A écrit en miroir dans le shadow ledger. Phase 4B basculera l’historique bundle sur ce journal.

**Sans réconciliation validée**, un basculement prématuré pourrait afficher un historique incomplet sur des bundles legacy (événements avant 4A sans entrée ledger).

Aucun écran n’est modifié à cette étape.

---

## Script read-only

Depuis `services/arquantix/api` :

```bash
python3 -m scripts.reconcile_bundle_ledger_shadow \
  --person-id <PERSON_UUID> \
  --portfolio-id <BUNDLE_PORTFOLIO_UUID> \
  [--batch-id <BATCH_UUID>] \
  [--pretty] \
  [--fail-on-diff]
```

### Sortie principale

| Champ | Description |
|-------|-------------|
| `expected_cash_from_ledger` | Cash leg reconstruit depuis le journal |
| `actual_cash_from_pe` | Cash leg PE (`pe_position_atoms`) |
| `expected_spots_from_ledger` | Spots reconstruits par asset |
| `actual_spots_from_pe` | Spots PE actuels |
| `missing_ledger_entries` | Audit / swap confirmé sans entrée ledger |
| `extra_ledger_entries` | Entrée ledger sans source audit/swap |
| `duplicated_idempotency_keys` | Anomalie idempotence |
| `orphan_lifi_swaps` | Swaps bundle confirmés sans ledger |
| `orphan_transaction_intents` | Intents terminés sans activité ledger |
| `verdict` | `MATCH` / `DIFF` / `INCOMPLETE` |
| `recommendations` | Actions ops suggérées (sans exécution) |

---

## Verdicts

### MATCH

- Balances ledger = balances PE (tolérance `1e-6`)
- Pas d’entrée manquante critique
- Pas de clé idempotence dupliquée

→ Bundle prêt pour validation ops ; candidat Phase 4B après échantillon représentatif.

### DIFF

- Écart cash ou spot ledger vs PE
- Entrée ledger manquante **avec** désalignement de balance
- Clés idempotence dupliquées

→ **Ne pas basculer Phase 4B.** Investiguer avec `inspect_bundle_state` + logs miroir.

### INCOMPLETE

- Audit `fund`/`release` legacy sans entrée ledger, **mais** balances PE cohérentes entre elles
- Données antérieures à Phase 4A (pas de backfill encore)
- Filtre `--batch-id` avec événements batch OK mais sans comparer le solde global

→ Shadow ledger **incomplet** sur l’historique, pas forcément **faux** sur le stock actuel. Backfill 4B requis avant switch UI.

---

## Écarts acceptables (prod limitée)

| Écart | Acceptable ? | Action |
|-------|--------------|--------|
| `orphan_transaction_intents` seul | Oui (souvent) | Intent créé avant fund ; pas bloquant si balances MATCH |
| `missing_ledger_entries` audit legacy | Oui → INCOMPLETE | Backfill Phase 4B |
| Recovery `BUNDLE_RECOVERY_ADJUSTMENT` INFO | Oui | Ignoré pour balances |
| `BUNDLE_DEPOSIT` internal_cash_leg | Oui | Mouvement cash interne (sell → cash leg) |
| DIFF cash > tolérance | **Non** | Bug miroir ou PE — investiguer |
| duplicated_idempotency_keys | **Non** | Anomalie DB |

---

## Si une entrée manque

1. Vérifier que l’événement est **post-Phase 4A** (fund, release, allocation confirmée).
2. Si post-4A : bug d’écriture miroir — corriger le hook, pas le backfill aveugle.
3. Si pre-4A : normal → INCOMPLETE ; planifier backfill idempotent 4B depuis :
   - `pe_audit_events` (`bundle.fund_cash_leg`, `bundle.release_cash_leg`)
   - swaps Li.FI confirmés avec `bundle_pe_atoms_applied`
4. **Ne jamais** modifier une entrée ledger existante — reversal append-only si correction.

---

## Endpoint admin (shadow)

```
GET /api/admin/bundles/{portfolio_id}/ledger/reconciliation
  ?person_id=<UUID>   (optionnel — déduit du portfolio)
  &batch_id=...
```

Protégé `require_admin_or_ops`. Même payload que le script.

---

## Tests

```bash
pytest tests/test_bundle_ledger_reconciliation.py -q
```

Scénarios : dépôt seul, dépôt+allocation, allocation partielle, retrait partiel, entrée manquante, idempotence dupliquée, recovery INFO ignoré pour balances.

---

## Pourquoi aucun écran n’est basculé

- Le ledger shadow peut être **incomplet** sur bundles historiques.
- Mon Trading ne doit **jamais** lire ce journal (PE transfers only).
- L’historique bundle actuel reste la projection audit + swaps + intents.
- Phase 4B = backfill + read switch **uniquement** après MATCH/INCOMPLETE maîtrisé sur un panel de portfolios.

---

## Commandes ops recommandées

```bash
# 1. État temps réel
python3 -m scripts.inspect_bundle_state --person-id ... --portfolio-id ...

# 2. Réconciliation shadow
python3 -m scripts.reconcile_bundle_ledger_shadow \
  --person-id ... --portfolio-id ... --fail-on-diff

# 3. Journal shadow (lecture)
curl -H "Authorization: Bearer …" \
  "http://localhost:8000/api/app/bundle/{portfolio_id}/ledger"
```

---

*Phase 4A.5 — read-only only. Aucune mutation DB.*

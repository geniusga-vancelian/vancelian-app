# Phase 3A — Vault Scope Funding — Runbook prod

**Date :** 2026-05-31  
**Statut :** runbook d'exécution — **aucune action prod exécutée**  
**Commit cible (local, non poussé) :** `70de5a348` — *Add vault scope funding engine*  
**Person pilote prod :** `8b0e0044-f1ef-47a5-99d4-370598a77492` (Gael)  
**Références :** [Phase 3A spec](./INTERNAL_SCOPE_MOVEMENTS_PHASE3A_VAULT.md) · [Phase 2 dry-run](./INTERNAL_SCOPE_MOVEMENTS_PHASE2_DRY_RUN.md)

---

## Résumé opérationnel

Phase 3A écrit des **PE atoms** (`direct_portfolio` ↔ `vault_portfolio`) pour refléter les dépôts/retraits Vault déjà exécutés on-chain. **Patrimoine économique inchangé** ; **affichage comptable PE modifié**.

| Avant backfill | Après backfill vault seul (cible Gael) |
|----------------|----------------------------------------|
| trading_available USDC ≈ **182.11** | ≈ **2.11** |
| vault_position USDC = **0** | **180** |
| Lombard / bundle PE | **inchangés** (Phase 3B plus tard) |

**Hors scope apply :** Lombard, hook OVT live (`dual_write`), Cost Basis, Reconciliation Controller, Privy.

---

## 0. Garde-fous absolus

- **Ne pas** lancer `--apply` sans GO explicite et snapshot RDS.
- **Ne pas** brancher `vault_ovt_bridge` sur receipt OVT avant validation post-backfill.
- **Ne pas** toucher aux scripts `scripts/_*.js` / repair prod ad hoc.
- **Une seule person** en apply initial (`person_id` pilote).
- Rollback primaire = **restauration snapshot RDS** ; chirurgie atoms = secondaire.

---

## 1. Pré-checks

### 1.1 Git / commit

```bash
cd /path/to/vancelian-app
git log -1 --oneline
# Attendu : 70de5a348 Add vault scope funding engine

git show 70de5a348 --stat --name-only
```

**Fichiers attendus dans le commit :**

| Fichier |
|---------|
| `docs/arquantix/INTERNAL_SCOPE_MOVEMENTS_PHASE3A_VAULT.md` |
| `services/arquantix/api/scripts/vault_scope_backfill.py` |
| `services/arquantix/api/services/portfolio_engine/vault_execution/__init__.py` |
| `services/arquantix/api/services/portfolio_engine/vault_execution/vault_funding.py` |
| `services/arquantix/api/services/portfolio_engine/vault_execution/vault_ovt_bridge.py` |
| `services/arquantix/api/services/portfolio_engine/internal_scope_movements/pe_reader.py` |
| `services/arquantix/api/tests/test_vault_scope_funding_phase3a.py` |

```bash
git status --short
# Vérifier : aucun fichier hors scope staged pour push Phase 3A
# Exclure : bundle_funding.py, chain_balance.py, scripts/_*, tsbuildinfo, tmp/
```

### 1.2 Migrations Alembic

```bash
rg "vault_portfolio|vault_execution|vault_scope" services/arquantix/api/alembic/
# Attendu : aucune migration Phase 3A
```

**Confirmation : aucune migration requise.**

Phase 3A réutilise le schéma existant :

| Table | Effet apply |
|-------|-------------|
| `pe_portfolios` | INSERT possible `portfolio_type = vault_portfolio` (auto-provision) |
| `pe_position_atoms` | UPDATE/INSERT SPOT sur `direct_portfolio` + `vault_portfolio` |
| `pe_audit_events` | INSERT append-only (idempotence) |
| `pe_assets` / `pe_instruments` | INSERT possible si instrument USDC absent (via `_resolve_or_create_instrument`) |

**Non touchées :** `onchain_vault_transactions`, `user_vault_positions`, `person_wallet_balances`, `bundle_ledger_entries`, `pe_ledger_entries`, tables Lombard, Privy.

### 1.3 Baseline dry-run scopes (prod read-only — déjà déployé Phase 2)

> Exécutable **avant** push Phase 3A (module `internal_scope_movements` sur ECS `:82+`).

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.internal_scope_movements_audit \
    --dry-run --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492'
```

**Exit code attendu :** `1` (gaps > 0 — normal pre-backfill).

**Valeurs de référence (prod 2026-05-31, post-fix CBETH) :**

| Métrique | Valeur attendue |
|----------|-----------------|
| `current_pe.trading_available.USDC` | `182.1111430000` |
| `current_pe.vault_position` | `{}` |
| `expected_from_legacy.vault_position.USDC` | `180` |
| `expected_from_legacy.trading_available_net_from_legacy.USDC` | `-102` *(inclut Lombard — pas cible Phase 3A seule)* |
| `summary.vault_movement_count` | **15** |
| `summary.lombard_movement_count` | 16 *(ignoré Phase 3A)* |
| `summary.bundle_movement_count` | **6** |
| `summary.gap_count` | **8** |

**Calcul trading USDC post-backfill vault seul :**

```
182.111143 − 180 = 2.111143 ≈ 2.11 USDC
```

*(Le gap legacy `-102` inclut Lombard ; ne pas l'utiliser comme cible immédiate post-3A.)*

### 1.4 Comptage OVT éligibles (SQL read-only prod)

```sql
-- OVT vault Morpho/Ledgity success, deposit/withdraw
SELECT operation, COUNT(*), SUM(
  (amount_raw::numeric / POWER(10, COALESCE(asset_decimals, 6)))
) AS total_usdc
FROM onchain_vault_transactions
WHERE person_id = '8b0e0044-f1ef-47a5-99d4-370598a77492'
  AND integration_mode IN ('direct_morpho', 'ledgity_vault')
  AND status = 'success'
  AND operation IN ('deposit', 'withdraw')
GROUP BY operation
ORDER BY operation;
```

**Attendu :**

| | Count | Net USDC |
|---|-------|----------|
| **Total OVT** | **15** | — |
| deposit (fund) | ~12 | — |
| withdraw (release) | ~3 | — |
| **Net vault** | — | **180** |

### 1.5 Absence d'apply partiel préalable

```sql
SELECT action, entity_id, created_at, metadata
FROM pe_audit_events
WHERE entity_type = 'onchain_vault_transactions'
  AND action IN ('vault.fund_from_self_trading', 'vault.release_to_self_trading')
  AND metadata->>'client_id' IN (
    SELECT id::text FROM pe_clients WHERE person_id = '8b0e0044-f1ef-47a5-99d4-370598a77492'
  )
ORDER BY created_at;
```

**Attendu :** **0 ligne** (Phase 3A jamais appliquée).

### 1.6 Tests locaux (gate avant push)

```bash
cd services/arquantix/api
python3 -m pytest \
  tests/test_vault_scope_funding_phase3a.py \
  tests/test_internal_scope_movements_dry_run.py -q
# Attendu : 17 passed
```

---

## 2. Dry-run backfill (prod, sans effet DB)

> **Prérequis :** commit `70de5a348` **pushé + API déployée** (script `vault_scope_backfill` absent de `:82`).

### 2.1 Commande ECS — plan complet person

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.vault_scope_backfill \
    --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492'
```

**Comportement :** `dry_run=True` par défaut → **`db.rollback()`** en fin de script → **aucune mutation**.

### 2.2 Commande ECS — OVT unitaire (spot-check)

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.vault_scope_backfill \
    --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492 \
    --ovt-id cmpl7qmrh0001ad014ro1niu3'
```

### 2.3 Output JSON attendu (racine)

```json
{
  "person_id": "8b0e0044-f1ef-47a5-99d4-370598a77492",
  "dry_run": true,
  "ovt_count": 15,
  "fund_count": 12,
  "release_count": 3,
  "planned_movements": [ ... ]
}
```

> Valider `fund_count` / `release_count` exacts depuis l'output ; les totaux ci-dessus sont la référence dry-run Phase 2.

### 2.4 Structure par mouvement planifié

Chaque entrée de `planned_movements` :

```json
{
  "ok": true,
  "dry_run": true,
  "would_apply": "fund_vault_from_self_trading",
  "ovt_id": "cmpl7qmrh0001ad014ro1niu3",
  "operation": "deposit",
  "asset": "USDC",
  "amount": "10",
  "integration_mode": "direct_morpho",
  "tx_hash": "0x..."
}
```

Withdraw :

```json
{
  "ok": true,
  "dry_run": true,
  "would_apply": "release_vault_to_self_trading",
  "operation": "withdraw",
  "amount": "5"
}
```

**NO-GO immédiat si :** un mouvement a `"ok": false` ou `"reason": "vault.funding.insufficient_trading_available"`.

### 2.5 Idempotence — clés métier

| Concept | Valeur |
|---------|--------|
| **Clé primaire apply** | `linked_reference_id` = **`onchain_vault_transactions.id`** (OVT cuid) |
| **Garde-fou DB** | `pe_audit_events` : `(entity_type, entity_id, action)` unique en pratique |
| `entity_type` | `onchain_vault_transactions` |
| `entity_id` | OVT id |
| `action` fund | `vault.fund_from_self_trading` |
| `action` release | `vault.release_to_self_trading` |
| Rejeu | `{ "skipped": true, "reason": "already_applied" }` |

**Pas de table `idempotency_key` dédiée Phase 3A** — l'audit PE fait foi.

### 2.6 Vérification net USDC (depuis planned_movements)

Script local sur JSON capturé :

```python
from decimal import Decimal
import json, sys
plan = json.load(sys.stdin)
net = Decimal(0)
for m in plan["planned_movements"]:
    if not m.get("ok"):
        print("FAIL", m); sys.exit(1)
    amt = Decimal(m["amount"])
    if m["operation"] == "deposit":
        net += amt
    else:
        net -= amt
assert net == Decimal("180"), net
print("OK net USDC", net)
```

**Attendu :** `OK net USDC 180`  
**Asset attendu :** **USDC uniquement** — NO-GO si autre asset.

### 2.7 Confirmation zéro effet DB

Après dry-run ECS, re-vérifier :

```sql
-- Toujours 0 audit vault Phase 3A
SELECT COUNT(*) FROM pe_audit_events
WHERE action LIKE 'vault.%from_self_trading';
```

---

## 3. Conditions GO / NO-GO

### GO — toutes obligatoires

| # | Critère | Seuil |
|---|---------|-------|
| G1 | OVT vault success éligibles | **15** |
| G2 | Net USDC vault (deposits − withdraws) | **180** |
| G3 | Tous `planned_movements[].ok` | `true` |
| G4 | Aucun `insufficient_trading_available` | 0 |
| G5 | Aucun doublon `linked_reference_id` dans plan | 15 ids uniques |
| G6 | Asset inattendu | **aucun** (USDC only) |
| G7 | `internal_scope_movements` bundle count | **6** (inchangé vs baseline) |
| G8 | Lombard | **non évalué / ignoré** |
| G9 | `pe_audit_events` vault Phase 3A pre-apply | **0** |
| G10 | Snapshot RDS planifié + fenêtre validée | oui |
| G11 | Tests locaux 17/17 | pass |

### NO-GO — une suffit

| Code | Condition |
|------|-----------|
| N1 | `ovt_count ≠ 15` |
| N2 | `net USDC ≠ 180` |
| N3 | Mouvement `ok: false` |
| N4 | `vault.funding.insufficient_trading_available` |
| N5 | Doublon OVT id dans le plan |
| N6 | Asset ≠ USDC |
| N7 | Audit vault déjà présent (apply partiel) |
| N8 | `bundle_movement_count` baseline ≠ 6 post-déploiement dry-run |
| N9 | Migration Alembic oubliée en prod *(ici : aucune attendue)* |
| N10 | Pas de snapshot RDS |

---

## 4. Apply plan (ordre strict)

### Phase A — Préparation (J-0)

1. **Snapshot RDS manuel** (AWS Console ou CLI) — nommer `pre-phase3a-vault-YYYYMMDD`
2. Noter l'heure UTC + ARN snapshot
3. Confirmer GO checklist §3

### Phase B — Déploiement code (sans apply PE)

```bash
git push origin main   # commit 70de5a348
# Attendre CI : Arquantix API Build & push ECR + Deploy ECS stable
# Noter task definition : arquantix-api:XX
```

4. Re-run **§2 dry-run backfill** sur ECS déployé → re-valider GO

### Phase C — Apply backfill ciblé (une person)

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.vault_scope_backfill \
    --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492 \
    --apply'
```

**Effet attendu :**

- 15 appels fund/release (ordre chronologique OVT `created_at ASC`)
- 15 lignes `pe_audit_events` (fund + release)
- 1 `vault_portfolio` auto-provisionné
- Atoms `direct_portfolio` USDC SPOT débité net **180**
- Atoms `vault_portfolio` USDC SPOT crédité net **180**

### Phase D — Vérifications post-apply (prod read-only)

#### D1 — Audit scopes

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.internal_scope_movements_audit \
    --dry-run --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492'
```

| Métrique | Cible post-3A vault |
|----------|---------------------|
| `current_pe.vault_position.USDC` | **180** |
| `current_pe.trading_available.USDC` | **≈ 2.11** (tolérance ±0.01) |
| Gap vault USDC | **0** ou gap_count −1 vs baseline |
| `summary.bundle_movement_count` | **6** (inchangé) |
| Lombard gaps | **inchangés** (Phase 3B) |

#### D2 — Patrimoine PE USDC conservé

```sql
-- trading + vault ≈ 182.11 (pre-apply trading, vault=0)
SELECT
  COALESCE(SUM(CASE WHEN p.portfolio_type = 'direct_portfolio' THEN a.quantity END), 0) AS direct_usdc,
  COALESCE(SUM(CASE WHEN p.portfolio_type = 'vault_portfolio' THEN a.quantity END), 0) AS vault_usdc
FROM pe_position_atoms a
JOIN pe_portfolios p ON p.id = a.portfolio_id
JOIN pe_instruments i ON i.id = a.instrument_id
JOIN pe_assets s ON s.id = i.asset_id
JOIN pe_clients c ON c.id = p.client_id
WHERE c.person_id = '8b0e0044-f1ef-47a5-99d4-370598a77492'
  AND s.symbol = 'USDC'
  AND a.status = 'open'
  AND a.position_type = 'spot';
```

**Attendu :** `direct_usdc + vault_usdc ≈ 182.111143`

#### D3 — Idempotence

Re-run dry-run backfill (sans `--apply`) : tous les mouvements restent `ok: true`, apply réel serait skipped.

Re-run `--apply` : **aucun double audit** ; logs `idempotent_skip`.

#### D4 — Bundle / Lombard / Privy

| Domaine | Vérification | Attendu |
|---------|--------------|---------|
| Bundle | `bundle_movement_count` audit | 6 |
| Bundle atoms | quantités bundle_cash / bundle_position | inchangées |
| Lombard | locked / liability PE | `{}` |
| Privy | balances on-chain | **inchangées** |

### Phase E — Non faire (post-apply immédiat)

- **Ne pas** brancher hook OVT live tant que D1–D4 OK + validation humaine
- **Ne pas** lancer Phase 3B Lombard
- **Ne pas** étendre `--apply` à d'autres person_id

---

## 5. Rollback plan

### 5.1 Rollback primaire — snapshot RDS

1. Stopper writes API (scale 0 ou maintenance banner)
2. Restaurer snapshot `pre-phase3a-vault-*` → nouvelle instance ou restore in-place **selon procédure AWS validée**
3. Redémarrer ECS
4. Re-run audit Phase 2 → baseline §1.3

**C'est la procédure recommandée** si patrimoine PE anormal.

### 5.2 Rollback chirurgical — atoms vault Phase 3A only

> À n'utiliser que si snapshot impossible et apply limité à **une person** avec audit traçable.

**Étape 1 — Lister les apply Phase 3A**

```sql
SELECT id, action, entity_id AS ovt_id, metadata, created_at
FROM pe_audit_events
WHERE entity_type = 'onchain_vault_transactions'
  AND action IN ('vault.fund_from_self_trading', 'vault.release_to_self_trading')
  AND metadata->>'client_id' = (
    SELECT id::text FROM pe_clients
    WHERE person_id = '8b0e0044-f1ef-47a5-99d4-370598a77492'
  )
ORDER BY created_at DESC;
```

**Étape 2 — Reversal par OVT (ordre inverse chronologique)**

Pour chaque audit **fund** : exécuter logique inverse de `release_vault_to_self_trading` avec même `linked_reference_id`  
Pour chaque audit **release** : exécuter logique inverse de `fund_vault_from_self_trading`

> **Recommandé :** script ECS one-shot utilisant `fund_vault` / `release_vault` en reversal **uniquement après** revue manuelle des montants — ne pas improviser SQL direct sur `pe_position_atoms` sans recalcul cost_basis.

**Étape 3 — Nettoyage audit**

```sql
DELETE FROM pe_audit_events
WHERE id IN (/* ids Phase 3A vault listés étape 1 */);
```

**Étape 4 — Vault portfolio vide**

Si `vault_portfolio` sans atoms open :

```sql
-- Vérifier quantité 0 avant delete portfolio
SELECT p.id, p.portfolio_type, SUM(a.quantity)
FROM pe_portfolios p
LEFT JOIN pe_position_atoms a ON a.portfolio_id = p.id AND a.status = 'open'
WHERE p.client_id = (SELECT id FROM pe_clients WHERE person_id = '8b0e0044-f1ef-47a5-99d4-370598a77492')
  AND p.portfolio_type = 'vault_portfolio'
GROUP BY p.id;
```

### 5.3 Vérifier bundle non impacté

```bash
# Audit bundle count
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.internal_scope_movements_audit \
    --dry-run --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492' \
  | jq .summary.bundle_movement_count
# Attendu : 6
```

```sql
SELECT p.portfolio_type, s.symbol, a.position_type, a.quantity
FROM pe_position_atoms a
JOIN pe_portfolios p ON p.id = a.portfolio_id
JOIN pe_instruments i ON i.id = a.instrument_id
JOIN pe_assets s ON s.id = i.asset_id
JOIN pe_clients c ON c.id = p.client_id
WHERE c.person_id = '8b0e0044-f1ef-47a5-99d4-370598a77492'
  AND p.portfolio_type = 'bundle_portfolio'
  AND a.status = 'open';
```

Comparer quantités **avant / après** apply (capture baseline SQL pre-apply).

---

## 6. Tests post-apply

| # | Test | Commande | Succès |
|---|------|----------|--------|
| T1 | Audit scopes | `internal_scope_movements_audit --dry-run` | vault=180, trading≈2.11 |
| T2 | Backfill idempotent | `vault_scope_backfill` sans `--apply` | 15 ok, apply skipped si re-run |
| T3 | Re-apply idempotent | `vault_scope_backfill --apply` | 15× skipped, atoms stables |
| T4 | Bundle isolation | audit `bundle_movement_count` | 6 |
| T5 | Lombard untouched | audit locked/liability gaps | identiques baseline |
| T6 | Privy | pas de settlement vault Privy | balances chain inchangées |
| T7 | Patrimoine PE USDC | SQL §4.D2 | somme ≈ 182.11 |
| T8 | UI *(si dispo)* | Trading history / Savings | transferts vault visibles *(Phase 3A+2 projections)* |

---

## 7. Timeline recommandée

```
J-0  Pré-checks §1 + snapshot RDS
J-0  Push 70de5a348 + deploy API
J-0  Dry-run backfill §2 → GO/NO-GO §3
J-0  Apply person pilote §4.C (fenêtre basse activité)
J-0  Tests §6 + validation humaine
J+1  Décision hook OVT live (hors scope immédiat)
J+n  Phase 3B Lombard (séparé)
```

---

## 8. Journal d'exécution (à remplir le jour J)

| Heure UTC | Action | Résultat | Opérateur |
|-----------|--------|----------|-----------|
| | Snapshot RDS ARN | | |
| | Push `70de5a348` | | |
| | Deploy `arquantix-api:__` | | |
| | Dry-run backfill | ovt= / net= | |
| | GO / NO-GO | | |
| | Apply `--apply` | | |
| | Post-audit vault USDC | | |
| | Post-audit trading USDC | | |
| | Rollback nécessaire ? | | |

---

## 9. État actuel (2026-05-31)

| Item | Statut |
|------|--------|
| Commit `70de5a348` | local main, **non poussé** |
| Deploy Phase 3A | **non** |
| Apply prod | **non** |
| Baseline dry-run scopes | prod `:82`, gaps=8, vault net=180 |
| Hook OVT live | **non branché** |

**Prochaine action autorisée après validation humaine de ce runbook :** push → deploy → §2 dry-run → GO → snapshot → §4 apply person pilote.

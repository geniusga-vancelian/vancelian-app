# Transaction Engine — Clôture Phase 3B + statut global

**Date :** 2026-06-02  
**Person pilote prod-test :** `8b0e0044-f1ef-47a5-99d4-370598a77492` (Gael)  
**Client PE :** `080358a8-4519-4acf-b5da-25485446c967`  
**Décision :** **forward transaction engine validé** pour le périmètre produit actuel ; clôture du chantier forward ; suite = couches UX, repay Lombard, net worth, Reconciliation Controller, reset compte test optionnel.

**Documents liés :**

- Phase 2 + 3A (précédent) : [`TRANSACTION_SYSTEM_CLOSURE_STATUS.md`](./TRANSACTION_SYSTEM_CLOSURE_STATUS.md)
- Spec 3B Lombard : [`INTERNAL_SCOPE_MOVEMENTS_PHASE3B_LOMBARD_SPEC.md`](./INTERNAL_SCOPE_MOVEMENTS_PHASE3B_LOMBARD_SPEC.md)
- Runbook Vault 3A : [`PHASE3A_VAULT_SCOPE_FUNDING_PROD_RUNBOOK.md`](./PHASE3A_VAULT_SCOPE_FUNDING_PROD_RUNBOOK.md)

---

## 1. Executive summary

Le **forward transaction engine** est **implémenté, déployé et validé en prod** sur les principaux flux DeFi du produit.

| Phase | Périmètre | Statut |
|-------|-----------|--------|
| **Phase 2** | Intents, attempts, trace events, dual-write forward | ✅ Validée |
| **Phase 3A** | Vault Morpho/Ledgity — scopes PE `trading_available` ↔ `vault_position`, hook live post-OVT | ✅ Validée |
| **Phase 3B** | Lombard borrow — scopes PE lock collateral + borrow USDC, hook live post-`open_loan` | ✅ **Validée live prod** |

**Chaîne transactionnelle + comptable confirmée en réel (Lombard 2026-06-02) :**

```
OVT Lombard success
  → intent confirmed
  → attempt confirmed
  → trace events
  → PE audit lombard.lock_collateral
  → PE audit lombard.open_borrow
  → CBBTC trading_available ↓
  → CBBTC trading_locked_collateral ↑
  → USDC trading_available ↑
  → USDC liability ↑
```

**Verdict final :** le **forward transaction engine est validé** pour le scope produit actuel. Ce qui reste n’est plus le moteur forward, mais les couches suivantes : historique UX, repay/unlock Lombard, net worth consolidé avec liability, Reconciliation Controller, reset compte test si besoin.

**Commit déployé Phase 3B (prod) :** `60ca168d7578047871bd2215ae0ea9904a1a0f33` — task definition `arquantix-api:87`.

---

## 2. Flux validés (forward engine)

| Flux | Intent / attempt | Trace | PE scope hook | Statut forward |
|------|------------------|-------|---------------|----------------|
| **Privy deposit externe** | Observé (pas d’intent dédié — by design) | — | Crédit trading via indexer | ✅ |
| **LI.FI swap** | intent + attempt | ✅ | Mouvement spot trading | ✅ |
| **Bundle invest** | intent + attempts `internal_bundle` | ✅ | bundle_cash / bundle_position | ✅ |
| **Vault Morpho deposit** | approve + deposit attempts | ✅ | `vault.fund_from_self_trading` | ✅ |
| **Vault Ledgity deposit** | approve + deposit attempts | ✅ | `vault.fund_from_self_trading` | ✅ |
| **Lombard borrow** | intent `lombard_borrow` + steps approve/open_loan | ✅ | `lombard.lock_collateral` + `lombard.open_borrow` | ✅ **live prod** |

**Dual-write forward :** `dual_write_vault_step`, sync intents Lombard/Morpho/Ledgity, rapports dry-run (`transaction_attempt_gap_report`, `phase2_forward_dual_write_report`, `internal_scope_movements_audit`).

---

## 3. Dernier test Lombard prod (validation Phase 3B)

Test réel post-déploiement Phase 3B — mini borrow Lombard sur compte pilote Gael, audit **read-only** prod (2026-06-02 ~10:01 UTC).

### Contexte exécution

- Premier essai (~13:56 locale) : revert UserOp à l’étape `open_loan` (hash bundler non indexé BaseScan).
- **Retry immédiat : succès UI** — 1 USDC emprunté, garantie 0.000028 cbBTC, LTV 70 %.
- Ce `group_key` ne contient **qu’une étape `open_loan`** (allowance déjà suffisante après tentative précédente — pas de row OVT/attempt `approve` séparée dans ce groupe).

### Identifiants

| Champ | Valeur |
|-------|--------|
| **group_key** | `f83658c9-3b04-4de5-826e-f03ef7c3bba6` |
| **OVT open_loan** | `cmpwgx3dz0060ad01fm3e97xq` |
| **intent_id** | `525f2e93-dae9-4f1f-bd0c-9e2754cfb820` |
| **attempt_id** | `b0578600-17e5-41cf-80d1-63600c6ed78b` |
| **tx_hash** | `0x56d6c715e501ec1092c6e7bace0545ababa2dc57cb30ce4eeef10919a5287a61` |
| **collateral** | `0.000028` cbBTC (`guarantee_amount_raw`: `2847`) |
| **borrow** | `1` USDC (`borrow_amount_raw`: `1000000`) |
| **created_at** | `2026-06-02 10:01:44 UTC` |

### OVT

- `integration_mode` = `lombard_v1`
- `status` = `success`, `operation` = `deposit`
- `metadata.lombard_operation` = `open_loan`
- `guarantee_amount` / `borrow_amount` présents
- `tx_hash` open_loan présent

### Intent / attempts

- Intent `lombard_borrow` → **confirmed**
- Attempt `open_loan` → **confirmed** (`protocol=lombard`, `dual_write_source=vault_intent_sync`)
- tx_hash renseigné, **aucun duplicate** (group + global)
- Pas d’attempt `approve` dans **ce** group_key (retry — allowance réutilisée)

### PE audit events (exactement 2)

| audit_id | action |
|----------|--------|
| `55b628f7-a7d5-40c8-9e2c-20affa4395b8` | `lombard.lock_collateral` |
| `1e7ffbea-b661-4487-a3a3-674238f4bdcb` | `lombard.open_borrow` |

- `entity_id` = `cmpwgx3dz0060ad01fm3e97xq`
- `metadata.group_key`, `linked_reference_id`, `tx_hash` cohérents
- **Aucun** `vault.*` lié à cet OVT Lombard
- Pas de double audit

### Scopes PE (snapshot post-borrow)

| Scope | Valeur observée | Mouvement attendu (ce borrow) |
|-------|-----------------|-------------------------------|
| `CBBTC trading_available` | `0.00104215` | ↓ de `0.000028` |
| `CBBTC trading_locked_collateral` | **`0.000028`** | ↑ de `0.000028` (= garantie) |
| `USDC trading_available` | `2.111143` | ↑ de `1` USDC |
| `USDC liability` | **`1`** | ↑ de `1` USDC |

Pas de before/after capturé au moment exact du hook ; cohérence confirmée par snapshot + `internal_scope_movements_audit` (2 mouvements Lombard, **0 gap** sur cet OVT).

### Reports (read-only, ce group_key uniquement)

| Report | Résultat |
|--------|----------|
| `transaction_attempt_gap_report` | `gaps_for_group: []` |
| `internal_scope_movements_audit` | `scope_gaps_for_ovt: []` |
| `phase2_forward_dual_write_report` | `phase2_anomalies: []` |

**Verdict test Lombard : PASS.**

### Borrow pre-3B même jour (hors scope validation hook)

| Champ | Valeur |
|-------|--------|
| **group_key** | `abeca8f1-1a5f-41b6-9f06-117dd65c610f` |
| **Heure** | ~08:25 UTC (avant deploy `60ca168`) |
| **Garantie / borrow** | 0.000069 cbBTC / 1 USDC |
| **PE scopes Lombard** | **Non écrits** — hook 3B non rétroactif |

---

## 4. Known limitations

| Limitation | Impact | Décision |
|------------|--------|----------|
| **Gaps historiques compte Gael** | ~50 blocking gaps (`vault_tx_missing_attempt`, legacy Lombard, etc.) | **Non traités** — hors scope forward validation |
| **Borrow pre-3B non rétroactif** | OVT Lombard success avant deploy 3B sans PE lock/borrow | Attendu — pas de backfill prod sans runbook |
| **Repay / unlock Lombard** | Phase 3C non implémentée | Prochaine phase |
| **Net worth** | `patrimony_merge` ne soustrait pas encore liability partout | Phase 4 |
| **Overlay Lombard UI** | Transition UX (available / locked / liability) incomplète | Phase 3D |
| **Reconciliation Controller** | Non lancé | Phase 5 |
| **Compte test Gael** | Historique volontairement imparfait (orphelin Morpho 10 USDC, gaps legacy) | **Ne pas utiliser comme référence comptable** jusqu’à reset |
| **Wallet USDC detail** | Affiche encore patrimoine fusionné, pas seulement `trading_available` | UX séparée, non bloquante forward |

---

## 5. Next phases

| Phase | Contenu | Priorité |
|-------|---------|----------|
| **3C** | Repay Lombard + unlock collateral (mouvements inverses, idempotents par `ovt_id`) | Haute |
| **3D** | Historique UX complet / portfolio surfaces (Lombard, vault, bundle) | Haute |
| **4** | Net worth / `patrimony_merge` − liability ; Cost Basis V2 ; export fiscal | Moyenne |
| **5** | Reconciliation Controller (observabilité + gates prod) | Moyenne |
| **Optionnel** | Reset compte test Gael (snapshot RDS → purge contrôlée → dépôt initial propre) | Quand convenient |

---

## 6. Do not do

- **No historical repair prod** — ne pas réparer les gaps legacy du compte pilote.
- **No backfill Lombard prod** sans runbook dédié + feu vert explicite.
- **No auto-repair** — pas de micro-sync, pas de correction PE manuelle ad-hoc.
- **No use Gael account as clean accounting reference** until reset — golden source interdit tant que l’historique test n’est pas purgé.
- **No migration / deploy** dans le cadre de cette clôture — documentation uniquement.

---

## 7. Final verdict

```
Forward transaction engine : VALIDATED for current product scope

Phase 2  attempts / traces     : ✅
Phase 3A Vault scopes + hook   : ✅
Phase 3B Lombard scopes + hook : ✅ (live prod 2026-06-02)

Couverture forward :
  Privy deposit externe  ✅
  LI.FI swap             ✅
  Bundle invest          ✅
  Vault Morpho/Ledgity   ✅
  Lombard borrow         ✅

Chantier forward engine  : CLOSED
Suite                    : 3C repay · 3D UX · 4 net worth · 5 Reconciliation · reset optionnel
```

---

## Doctrine retenue (post-3B)

```
Socle transactionnel forward : robuste et clôturé
Hook PE live (Vault + Lombard) : robuste sur flux couverts
Compte test prod             : historiquement sale — reset futur > réparation
Borrow pre-3B                : documenté, non rétroactif
Gaps legacy Gael             : acceptés, non traités
```

---

## Références commits clés

| Phase | Commits / artefacts |
|-------|---------------------|
| Phase 2 | `c61e37251`, `9e7fdab45`, `b80ef0430` |
| Phase 3A | `b1e0bf829`, `13ae9e037`, `49c7bb8f8`, `f8e43626b` |
| Phase 3B | `60ca168d7578047871bd2215ae0ea9904a1a0f33` — `lombard_funding.py`, `lombard_ovt_bridge.py`, hook `dual_write.py` |

---

## Checklist opérationnelle (post-clôture 3B)

- [x] Phase 3B Lombard forward live validée en prod (read-only audit PASS).
- [ ] Ne pas lancer backfill / repair Lombard prod sans runbook.
- [ ] Ne pas utiliser le compte pilote comme référence comptable (reset ou nouveau compte clean).
- [ ] Planifier 3C repay/unlock avant exposition repay UI.
- [ ] Planifier Phase 4 net worth avant messaging patrimoine net avec dette Lombard.
- [ ] Reconciliation Controller : après 3C + surfaces UX stabilisées.

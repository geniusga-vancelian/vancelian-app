# Transaction System — Statut de clôture (Phase 2 + Phase 3A Vault)

**Date :** 2026-06-01  
**Person pilote prod-test :** `8b0e0044-f1ef-47a5-99d4-370598a77492` (Gael)  
**Client PE :** `080358a8-4519-4acf-b5da-25485446c967`  
**Décision :** clôturer le chantier code + doctrine ; **ne pas réparer l’historique sale** du compte test ; **reset contrôlé futur**.

---

## Executive summary

Le socle transactionnel (Phase 2) et la comptabilité vault PE (Phase 3A + hook live) sont **implémentés, testés et validés en prod** sur le compte pilote interne.

- **Phase 2** : intents, attempts, trace, dual-write forward — **robuste** pour les flux couverts (LI.FI, Bundle, Vault Morpho/Ledgity).
- **Phase 3A** : scopes `trading_available` / `vault_position`, backfill pilote, garde-fous API/BFF, hook live post-OVT — **robuste**.
- **Compte prod-test** : historique **volontairement imparfait** (1 OVT Morpho orphelin 10 USDC) ; **pas de repair** — reset compte prévu.

**Verdict :** chantier **clos côté produit/code**. Suite = reset compte test + évolutions hors scope (3B Lombard, wallet UI patrimoine, Reconciliation Controller).

---

## Ce qui est terminé

### Phase 2 — Transaction attempts & trace

| Flux | Modèle | Statut code |
|------|--------|-------------|
| **Privy deposit externe** | Événement observé ; pas d’intent/attempt dédié (by design) | ✅ |
| **LI.FI swap** | intent + attempt + `transaction_trace_events` | ✅ |
| **Bundle invest** | intent + attempts `internal_bundle` | ✅ |
| **Vault Morpho / Ledgity** | approve + deposit/withdraw attempts, 1 tx_hash → 1 attempt | ✅ |
| **Dual-write forward** | `dual_write_vault_step`, Morpho approve sans intent bloquant | ✅ |
| **Rapports dry-run** | `transaction_attempt_gap_report`, `phase2_forward_dual_write_report` | ✅ |

Commits de référence : `c61e37251` (couche attempts/trace), `9e7fdab45`, `b80ef0430`, `b1e0bf829` (hook vault).

### Phase 3A — Vault scope PE

| Élément | Statut |
|---------|--------|
| Moteur `fund_vault_from_self_trading` / `release_vault_to_self_trading` | ✅ |
| Backfill `--apply` compte pilote (15 OVT historiques) | ✅ appliqué prod |
| Exposition API `trading_available` sur `/api/app/crypto-positions/direct` | ✅ `13ae9e037` |
| Garde-fou BFF prepare Morpho/Ledgity (`amount > trading_available` → 400) | ✅ |
| UI Vault Invest : balance = `trading_available` PE (plus solde fusionné) | ✅ `49c7bb8f8`, fix overlay Lombard `f8e43626b` |
| Hook live post-OVT success (`apply_vault_scope_movement_for_ovt`) | ✅ `b1e0bf829` |

Runbook détaillé : [`PHASE3A_VAULT_SCOPE_FUNDING_PROD_RUNBOOK.md`](./PHASE3A_VAULT_SCOPE_FUNDING_PROD_RUNBOOK.md).

---

## Ce qui est validé en prod (read-only, 2026-06-01)

### Déploiements

| Service | Révision observée |
|---------|-------------------|
| API | `arquantix-api:85` |
| Web | `vancelian-next` (post-`f8e43626b`) |

### État PE compte pilote (post test Ledgity 1 USDC)

| Scope | USDC |
|-------|------|
| `trading_available` | **1.111143** (≈ 1.11 après dépôt 1 USDC) |
| `vault_position` | **181** (180 backfill + 1 hook live) |
| `bundle_cash` | **1** (inchangé) |

### Test hook live Ledgity — **validé ✅**

| Champ | Valeur |
|-------|--------|
| OVT id | `cmpur9jzx0003ad01tr2gylzx` |
| tx_hash | `0x6807992491e4f8d925cdfaa09104600fc3ac377de11864b554f054e1382591ae` |
| Montant | 1 USDC |
| intent id | `a91359a1-a132-4498-955f-9a7e71d0845c` (confirmed) |
| attempt id | `3d57c009-2a20-4b6f-b383-179a40ecd965` (ledgity / deposit / confirmed) |
| PE audit | `143f7970-e412-4fe4-9fdd-2b4e65a63d69` — `vault.fund_from_self_trading` |
| Double audit | non (1 ligne) |
| Gap vault USDC | **0** |
| `bundle_movement_count` | **6** (inchangé) |

### Test hook live Morpho

- **Code prêt** (même chemin `dual_write_vault_step` + `integration_mode=direct_morpho`).
- **Validé indirectement** par backfill Phase 3A sur OVT Morpho historiques ; pas de nouveau dépôt Morpho post-fix UI sur ce compte (orphelin 10 USDC bloquant volontairement non retesté).

### UI Vault Invest

- Balance affichée **2.11 USDC** avant test → **1.11 USDC** après — conforme à `trading_available` PE.

---

## Ce qui reste hors scope (clôture explicite)

| Sujet | Raison |
|-------|--------|
| **Phase 3B Lombard scopes PE** | Attendre reset compte ou snapshot propre |
| **Reconciliation Controller** | Lombard scopes non implémentés |
| **Wallet USDC detail** (`/wallet/crypto/usdc`) | Affiche encore patrimoine total fusionné (~183 $US), pas `trading_available` — UX séparée, non bloquante pour vault invest |
| **Repair / micro-sync / backfill global** | Compte test → reset futur |
| **OVT orphelin Morpho 10 USDC** | Voir § Known issues — **ne pas traiter** |
| **Scripts prod ad-hoc** (`scripts/_*.js`, `repair_*.py`) | Outils forensic locaux, non commités comme procédure officielle |

---

## Known issues acceptés

### 1. OVT Morpho orphelin 10 USDC (compte test uniquement)

| Champ | Valeur |
|-------|--------|
| **OVT id** | `cmptfgskt000cad01mxww402q` |
| **Contexte** | Dépôt tenté **avant** correction UI `trading_available` ; UI affichait ~183 USDC disponibles |
| **On-chain** | success / tx confirmée |
| **Intent / attempt** | OK |
| **PE vault scope** | **non appliqué** — hook a refusé : `vault.funding.insufficient_trading_available` (2.11 < 10) |
| **Gap legacy** | `expected_from_legacy.vault_position.USDC` ≈ **191** vs PE **181** (= écart 10 dû à cet orphelin) |
| **Décision** | **Known test-account orphan, to be cleared by account reset** |
| **Interdit** | micro-sync, repair, backfill global, correction manuelle PE |

### 2. Gaps audit globaux (Lombard / legacy)

- `internal_scope_movements_audit --dry-run` : `gap_count` ≈ **7** (Lombard + legacy trading) — **hors Phase 3A vault USDC**.
- `vault_usdc_gaps` : **[]** après hook Ledgity 1 USDC.

### 3. Compte test non référence comptable

Tant que le reset n’est pas fait, **ne pas utiliser ce person_id** comme golden source patrimoine / réconciliation.

---

## Reset plan — compte test (futur, hors clôture)

Procédure cible **après** retrait des fonds et conversion USDC :

1. **Retirer** tous les vaults Morpho/Ledgity vers wallet Privy (on-chain).
2. **Convertir** les actifs test restants en USDC (swaps LI.FI si besoin).
3. **Vérifier** solde Privy USDC final on-chain + ledger Privy.
4. **Snapshot RDS** (obligatoire avant toute mutation).
5. **Reset contrôlé** des tables **test-account uniquement** (person + PE + OVT + intents/attempts liés) — procédure à rédiger au moment du reset, pas maintenant.
6. **Recréer** un dépôt USDC initial propre (Privy → PE).
7. **Relancer audits read-only :**
   ```bash
   ./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
     'cd /app && python3 -m scripts.transaction_attempt_gap_report --dry-run --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492'

   ./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
     'cd /app && python3 -m scripts.internal_scope_movements_audit \
       --dry-run --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492'

   cd services/arquantix/api && python3 -m scripts.phase2_forward_dual_write_report
   ```
8. **Gate GO** : gaps vault = 0, trading_available cohérent, aucun orphelin OVT vault.

---

## Checklist opérationnelle (post-clôture)

- [ ] **Ne pas** utiliser le compte pilote comme référence comptable tant que reset non fait.
- [ ] **Ne pas** traiter l’orphelin `cmptfgskt000cad01mxww402q` manuellement (pas de repair PE, pas de micro-sync).
- [ ] **Ne pas** lancer Phase 3B Lombard avant reset ou snapshot propre.
- [ ] **Ne pas** lancer Reconciliation Controller tant que Lombard scopes PE non implémentés.
- [ ] **Ne pas** lancer backfill / repair / migration sur prod sans runbook + feu vert explicite.
- [ ] Nouveaux tests vault : toujours vérifier UI **Balance = trading_available** avant dépôt > 2 USDC.

---

## Safe next steps (priorisés)

1. **Reset compte test** (quand convenient) — seule voie pour historique propre.
2. **UX wallet USDC** : afficher patrimoine total **et** « disponible trading » (`trading_available`) — chantier séparé, non bloquant.
3. **Phase 3B Lombard** : après reset + snapshot.
4. **Reconciliation Controller** : après 3B.
5. **Étendre hook live** à d’autres personnes prod : seulement après reset pilote ou nouveau compte clean.

---

## Vérifications read-only finales (2026-06-01)

| Check | Résultat |
|-------|----------|
| `git status` | Doc clôture seule à committer ; autres modifs locales non liées (scripts forensic, runbook edits) |
| Commits non poussés | **Aucun** sur `main` au moment de la clôture (`origin/main` à jour jusqu’à `f8e43626b`) |
| `vaultDepositValidation.test.ts` (web) | **7/7 pass** |
| `test_vault_forward_hook.py` (api local) | skipped (DB locale requise) — couverture prod via test Ledgity 1 USDC |
| Writes prod cette session | **Aucun** (audits ECS read-only uniquement) |

---

## Doctrine retenue

```
Socle transactionnel     : robuste
Vault forward + hook     : robuste (Morpho + Ledgity)
Compte test prod         : historiquement sale (1 orphelin accepté)
Décision                 : reset futur > réparation historique
Orphelin Morpho 10 USDC  : documenté, non traité, cleared by reset
```

---

## Références

- [`PHASE3A_VAULT_SCOPE_FUNDING_PROD_RUNBOOK.md`](./PHASE3A_VAULT_SCOPE_FUNDING_PROD_RUNBOOK.md)
- [`INTERNAL_SCOPE_MOVEMENTS_PHASE2_DRY_RUN.md`](./INTERNAL_SCOPE_MOVEMENTS_PHASE2_DRY_RUN.md)
- Commits clés : `70de5a348` → `0f3fe8742` → `b1e0bf829` → `13ae9e037` → `49c7bb8f8` → `f8e43626b`

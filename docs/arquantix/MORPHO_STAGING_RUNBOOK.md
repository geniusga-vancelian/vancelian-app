# Morpho USDC Volt — Runbook staging

Validation manuelle en conditions réelles avant ouverture beta client.

**Prérequis staging**
- Web : `app.staging.vancelian.finance` (ou URL staging équivalente)
- Wallet Privy embedded créé + session portail active
- USDC sur Base dans le wallet embedded (montant test : **1–5 USDC**)
- Vault publié en CMS (`/admin/morpho-vaults`) — recommander **direct_morpho V2** pour premier test
- Migrations Prisma Phase 1 + Phase 2 appliquées
- `pnpm morpho:sync-vault-registry` exécuté au moins une fois

---

## 0. Préparation

```bash
cd services/arquantix/web
pnpm morpho:sync-vault-registry
pnpm morpho:backfill-positions   # si wallets préexistants
```

Vérifier monitoring admin : `/admin/morpho-vaults/monitoring` → statut **Healthy** ou **Warning** documenté.

---

## 1. Connexion wallet Privy réel

| # | Action | Résultat attendu |
|---|--------|------------------|
| 1.1 | Se connecter au portail staging | Session JWT cookie `arq_portal_access_token` |
| 1.2 | Aller sur Invest → section Earn / Morpho vaults | Vaults publiés visibles (APY, USDC, badge Direct/Privy) |
| 1.3 | Ouvrir modal vault | Wallet embedded affiché, disclaimer visible si 1er dépôt |

**Échec si** : wallet absent → créer via `/portal/wallet` (Mon wallet crypto).

---

## 2. Dépôt USDC (montant faible)

Montant recommandé : **1.00 USDC**.

| # | Étape | Vérification |
|---|-------|--------------|
| 2.1 | Accepter disclaimer (1er dépôt) | Checkbox/CTA « J'ai compris » |
| 2.2 | Saisir `1` USDC, Confirmer | UI : Preparing → Approval pending (si besoin) → Deposit pending → Confirmed |
| 2.3 | Bouton désactivé pendant exécution | Impossible double-clic |
| 2.4 | Succès affiché **uniquement** après receipt success | Pas de « confirmé » avant fin on-chain |

**API (DevTools Network)**
- `POST /api/portal/morpho/prepare` → `idempotency_key`, `ledgerEntries`, `transactions`
- `POST /api/portal/morpho/confirm` → `confirmed: true`, status `success`

**Ledger DB**
```sql
SELECT operation, status, amount_raw, tx_hash, idempotency_key
FROM onchain_vault_transactions
WHERE person_id = '<PERSON_ID>'
ORDER BY created_at DESC LIMIT 5;
```

---

## 3. Approval (si requis)

Certains vaults exigent `approve` USDC avant `deposit`.

| # | Check |
|---|-------|
| 3.1 | Phase UI « Approval pending » visible |
| 3.2 | Deux entrées ledger : `approve` + `deposit` |
| 3.3 | Les deux receipts en `success` après confirm |

---

## 4. Affichage position

| # | Check |
|---|-------|
| 4.1 | `GET /api/portal/morpho/position` → `assetsInVaultDisplay` ≈ 1 USDC |
| 4.2 | Position modal rafraîchie après dépôt |
| 4.3 | `wallet_address` = adresse EVM (0x…), pas Privy ID |

---

## 5. Intérêts / valeur actuelle

| # | Check |
|---|-------|
| 5.1 | Si ledger historique : `earnedYieldDisplay` calculé (≠ hardcodé 0) |
| 5.2 | Si backfill sans ledger : « Rendement en cours de synchronisation » |
| 5.3 | `yieldSyncStatus: pending` si `cost_basis_unknown` |

Attendre 24h+ en staging pour voir yield > 0 si souhaité (optionnel).

---

## 6. Retrait partiel

Montant : **0.50 USDC** (ou 50 % de la position).

| # | Check |
|---|-------|
| 6.1 | Onglet Retirer, saisir montant < position |
| 6.2 | Confirm → phases withdraw → Confirmed |
| 6.3 | Position diminuée après refresh |
| 6.4 | Ledger : entrée `withdraw` status `success` |

**Rejet attendu** : montant > position → erreur métier `morpho.withdraw_exceeds_position`.

---

## 7. Retrait max

| # | Check |
|---|-------|
| 7.1 | Clic « Retirer le maximum » |
| 7.2 | Montant = position arrondie down (6 decimals USDC) |
| 7.3 | Retrait complet sans dust excessif |
| 7.4 | Position ≈ 0 après confirm |

---

## 8. Transaction revert (si simulable)

**Option A — staging contrôlé** : utiliser un vault test non listé (non recommandé prod).

**Option B — inspection ledger** : vérifier qu'une tx `reverted` met le ledger en `reverted` et UI en **Failed**.

| # | Check |
|---|-------|
| 8.1 | Ledger status `reverted` ou `failed` |
| 8.2 | UI n'affiche pas « Confirmed » |
| 8.3 | `error_message` renseigné si applicable |

---

## 9. Tx pending longue

Simuler en interrompant le réseau mid-flow ou laisser une tx pending en DB (support).

| # | Check |
|---|-------|
| 9.1 | Entrée ledger `pending` persiste |
| 9.2 | Monitoring admin : alerte `pending_tx_stale` si > 15 min |
| 9.3 | `globalStatus` → Warning ou Critical |

---

## 10. Réconciliation post-opération

```bash
pnpm morpho:reconcile
```

| # | Check |
|---|-------|
| 10.1 | Run terminé, `matchedCount` ≥ 1 pour le wallet test |
| 10.2 | Admin monitoring : mismatches = 0 (ou delta < tolérance) |
| 10.3 | `GET /api/portal/morpho/history` → txs deposit/withdraw visibles |

---

## 11. Idempotency (optionnel)

| # | Action | Attendu |
|---|--------|---------|
| 11.1 | Rejouer prepare avec même `idempotency_key` | Pas de double dépôt, 409 ou replay safe |
| 11.2 | Double-clic rapide sur Confirmer | Une seule opération ledger |

---

## 12. Critères de sortie staging

- [ ] Dépôt 1 USDC confirmé on-chain + ledger success
- [ ] Retrait partiel + max OK
- [ ] Position et history API cohérents
- [ ] Réconciliation matched (ou mismatch expliqué)
- [ ] Monitoring Healthy ou Warning acceptable
- [ ] Disclaimer visible au 1er dépôt
- [ ] Aucune tx pending > 15 min non résolue

**Go beta** : valider checklist production (`MORPHO_PRODUCTION_CHECKLIST.md`) + ce runbook signé par QA/ops.

---

## Rollback rapide staging

1. Dépublier vaults dans `/admin/morpho-vaults` (`isPublished = false`)
2. Vérifier portail : vaults disparaissent de Invest
3. Ledger conservé — pas de suppression de données
4. Investiguer via `/admin/morpho-vaults/monitoring` + logs `onchain_vault_transactions`

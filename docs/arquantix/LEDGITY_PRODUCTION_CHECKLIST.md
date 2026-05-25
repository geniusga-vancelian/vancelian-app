# Checklist activation production — Ledgity Vaults

Objectif : valider monitoring + réconciliation + liquidité RWA **avant** toute activation live (dépôts/retraits réels).

Références :
- [LEDGITY_AUDIT.md](./LEDGITY_AUDIT.md)
- [LEDGITY_LOCAL_SANDBOX.md](./LEDGITY_LOCAL_SANDBOX.md)
- Monitoring admin : `/admin/ledgity-vaults/monitoring`
- Job réconciliation : `pnpm ledgity:reconcile`

---

## 1. Contrats & adresses

- [ ] Contrats lyUSDC / lyEURC vérifiés sur [BaseScan](https://basescan.org)
- [ ] Adresses USDC / EURC Circle validées depuis la doc Ledgity
- [ ] Adresses vault alignées avec `ledgityConstants.ts` et seed DB
- [ ] `integrationMode = ledgity_vault`, `protocol = ledgity` dans le ledger

| Rôle | Adresse Base |
|------|--------------|
| lyUSDC vault | `0x916f179D5D9B7d8Ad815AC2f8570aabF0C6a6e38` |
| lyEURC vault | `0xFaA1e3720e6Ef8cC76A800DB7B3dF8944833b134` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| EURC | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` |

---

## 2. Lecture ERC-4626 (read-only)

- [ ] `asset()`, `totalAssets()`, `convertToAssets(shares)` testés
- [ ] `balanceOf(wallet)` testé sur wallet de test
- [ ] PPS (via `convertToAssets(1e18)`) cohérent avec UI
- [ ] `maxWithdraw(address)` et `maxRedeem(address)` testés
- [ ] `previewRedeem(shares)` testé
- [ ] Comportement `paused()` documenté si présent sur le contrat

---

## 3. Liquidité & risque RWA

- [ ] Retrait partiel testé quand `maxWithdraw >= montant`
- [ ] Retrait max testé — si `maxWithdraw < solde`, erreur métier affichée :
  > *La liquidité disponible du vault ne permet pas un retrait instantané complet. Veuillez réessayer plus tard.*
- [ ] Aucun message ne garantit un retrait instantané systématique
- [ ] Monitoring affiche `withdrawAvailability` (instant / deferred / paused)
- [ ] Alerte `liquidity_low` testée en staging

---

## 4. Tests live limités (pré-prod)

Activation initiale recommandée : **10 USDC / 10 EURC max**, MetaMask uniquement.

- [ ] 1 dépôt faible montant (USDC) — ledger `success`
- [ ] 1 dépôt faible montant (EURC) — ledger `success`
- [ ] 1 retrait partiel testé
- [ ] 1 retrait max testé (dans la limite `maxWithdraw`)
- [ ] `metadata_json` contient `pps_at_tx`, `share_symbol`, `wallet_source`
- [ ] `pnpm ledgity:reconcile` → statut `matched`
- [ ] Monitoring admin → **Healthy** (ou Warning documenté)

---

## 5. Flags production (live contrôlé — accès ouvert)

Valeurs cibles :

```env
LEDGITY_VAULTS_ENABLED=true
LEDGITY_BETA_ENABLED=false
LEDGITY_DEPOSITS_DISABLED=false
LEDGITY_WITHDRAWS_DISABLED=false
LEDGITY_MAX_DEPOSIT_RAW=10000000
LEDGITY_MAX_USER_EXPOSURE_RAW=50000000
LEDGITY_MAX_GLOBAL_EXPOSURE_RAW=500000000
LEDGITY_LOCAL_SANDBOX_ENABLED=false
```

Voir runbook : [LEDGITY_LIVE_RUNBOOK.md](./LEDGITY_LIVE_RUNBOOK.md)

- [ ] Pas d’allowlist beta (`LEDGITY_BETA_ENABLED=false`)
- [ ] Plafonds 10 / 50 / 500 validés
- [ ] Privy + MetaMask / WalletConnect testés
- [ ] Kill switch dépôts testé
- [ ] `LEDGITY_LOCAL_SANDBOX_ENABLED=false` en prod (guard au boot)

---

## 6. Monitoring & cron

- [ ] Page `/admin/ledgity-vaults/monitoring` accessible (admin)
- [ ] Alertes testées : `rpc_unavailable`, `pps_unavailable`, `liquidity_low`, `ledger_onchain_mismatch`, `sandbox_enabled_in_prod`
- [ ] Cron quotidien 06:15 UTC : `pnpm ledgity:reconcile`
- [ ] Réconciliation relancée après chaque batch de tests live

---

## 7. UX & conformité

- [ ] Disclaimers liquidité RWA / retrait différé visibles (Invest + Épargne)
- [ ] APY / PPS présentés comme indicatifs, non garantis
- [ ] Support informé des codes d’alerte monitoring

---

## 8. Risques restants avant activation live

| Risque | Mitigation |
|--------|------------|
| Liquidité RWA insuffisante pour retrait instantané | `maxWithdraw` check + message utilisateur + alerte `liquidity_low` |
| PPS indisponible (RPC / contrat) | Alerte `pps_unavailable` Critical, pas de dépôt live |
| Écart ledger ↔ on-chain | Job `ledgity:reconcile` quotidien + alerte `ledger_onchain_mismatch` |
| Sandbox actif en prod | Guard `productionSandboxGuard` + alerte Critical |
| Exposition utilisateur / globale | Limites beta `LEDGITY_MAX_*_RAW` |
| Vault en pause | Alerte `vault_paused` / `withdrawals_paused` |

**Ne pas activer les dépôts live** tant que monitoring + réconciliation ne sont pas validés.

---

## 9. Go-live (accès ouvert)

Suivre [LEDGITY_LIVE_RUNBOOK.md](./LEDGITY_LIVE_RUNBOOK.md) :

1. `./scripts/vancelian-sync-ledgity-prod.sh`
2. Smoke tests Privy + MetaMask (10 USDC / 10 EURC max)
3. `npm run ledgity:reconcile` après chaque batch

# Audit — redirection post-transaction vers le e-wallet

## Symptôme

Après succès (swap, borrow, bundle, vault), le CTA « Voir mon wallet … » mène parfois à un **écran d’erreur** (`Unable to load position details.`) au lieu du détail actif visé (ex. cbETH, USDC).

## Cause racine (SWAP / BORROW — actifs crypto)

| Facteur | Détail |
|---------|--------|
| **Invalidation cache agressive** | `invalidatePortalCache` supprime les entrées **avant** `router.push` |
| **Lag settlement** | Après tx confirmée, `/api/portal/crypto-wallet/{asset}` peut répondre **404** tant que le hub Privy n’a pas le nouveau solde |
| **Pas de retry** | `usePortalCachedScreen` affiche l’erreur dès le premier 404 sans données en cache |
| **Borrow** | `invalidatePortalCache()` vide **tout** le cache portail avant navigation USDC |

Route cible correcte : `portalCryptoWalletAssetRoute('CBETH')` → `/app/wallet/crypto/cbeth` (OK).

## Par type de transaction

### SWAP

- **CTA** : `Voir mon wallet {toAsset}` → `portalCryptoWalletAssetRoute(toAsset)`
- **Bug** : race cache + 404 API
- **Fix** : prefetch avec retry, fallback hub crypto

### BORROW (Lombard)

- **CTA** : `Voir mon USDC` → `portalCryptoWalletAssetRoute('usdc')`
- **Bug** : idem + `invalidatePortalCache()` global
- **Fix** : navigation robuste + invalidation ciblée

### BUNDLE invest

- **CTA** : `Voir mon panier`
- **Bug fonctionnel** : redirige vers **Invest / Markets** (`onExit`), pas vers `/app/wallet/crypto/bundle/{portfolioId}`
- **Fix** : `portalCryptoWalletBundleRoute(portfolioId)`

### BUNDLE withdraw

- **CTA** : `Voir Mon Trading`
- **Bug fonctionnel** : `onExit` → invest/markets, pas le wallet USDC crédité
- **Fix** : `portalCryptoWalletAssetRoute('USDC')` (+ retry)

### VAULT (Morpho / Ledgity)

- **CTA** : `Voir mon coffre` / fermer
- **Comportement** : `portalSavingsVaultRoute` si `?from=savings`, sinon invest — **cohérent**
- **Risque** : faible (écran savings, pas hub crypto positions)

## Correctifs implémentés

- `postTransactionWalletNav.ts` — prefetch retry + fallback hub
- Branchement SWAP, Lombard, bundle invest/withdraw
- Spec : ce document

## Vérification manuelle

1. Swap USDC → cbETH (Base) → succès → CTA → détail cbETH (ou hub si lag > 4s)
2. Borrow USDC → CTA → détail USDC
3. Bundle invest → CTA → détail panier bundle
4. Bundle withdraw → CTA → détail USDC
5. Vault deposit depuis savings → CTA → détail coffre savings

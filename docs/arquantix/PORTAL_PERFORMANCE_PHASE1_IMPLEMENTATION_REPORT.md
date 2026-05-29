# Portail — Phase 1 Performance Implementation Report

Date : 2026-05-29  
Build log : `/tmp/build-after-phase1.log` (production, `rm -rf .next && NODE_ENV=production npm run build`)  
Audits de référence : `PORTAL_NAVIGATION_PERFORMANCE_AUDIT.md`, `PORTAL_BUNDLE_ANALYSIS_PHASE0BIS.md`

## Résumé

Phase 1 retire Web3 du layout shell global, isole les boundaries Web3 sur les routes wallet/borrow, supprime le warmup/prefetch agressif au mount, lazy-load les modales d’exécution, et corrige une fuite Privy via `navigateToPortalLogin` → `PortalAuthPrivySessionHygiene` (import statique de `@privy-io/react-auth` sur tous les écrans utilisant `usePortalCachedScreen`).

**Résultat : toutes les cibles First Load JS Phase 1 sont atteintes.**

## Build before / after

| Route | Before (Phase 0 bis) | After Phase 1 | Cible | Statut |
|-------|---------------------:|--------------:|------:|--------|
| `/app/academy` | 1 370 kB | **124 kB** | < 250 kB | OK |
| `/app/dashboard` | 1 440 kB | **195 kB** | < 300 kB | OK |
| `/app/markets` | 1 620 kB | **133 kB** | < 450 kB | OK |
| `/app/profile` | 1 580 kB | **339 kB** | < 500 kB | OK |
| `/app/wallet/swap` | 1 610 kB | **1 610 kB** | élevé attendu | OK |
| `/app/markets/bundle/[productCode]` | 1 760 kB | **282 kB** | — | bonus |

Shared JS global : **92,3 kB** (stable).

### Chunks Web3 (manifest production)

| Route | Chunks Privy/Wagmi (55500, 43239, 66498) |
|-------|------------------------------------------|
| `(shell)/layout` | aucun |
| `/app/academy` | aucun |
| `/app/dashboard` | aucun |
| `/app/profile` | wagmi (`43239`) — boundary lazy wallet externe |
| `/app/wallet/swap` | Privy + Wagmi + viem (attendu) |

## Fichiers modifiés / créés (Phase 1)

### Shell & boundaries Web3

| Fichier | Changement |
|---------|------------|
| `src/app/app/(shell)/layout.tsx` | Retrait `PortalWeb3Providers`, `PortalAuthPrivyGate` |
| `src/app/app/(shell)/wallet/layout.tsx` | **Créé** — monte `PortalWeb3Boundary` |
| `src/app/app/(shell)/wallets/layout.tsx` | **Créé** — idem |
| `src/app/app/(shell)/borrow/layout.tsx` | **Créé** — idem |
| `src/components/portal/web3/PortalWeb3Boundary.tsx` | **Créé** — boundary client explicite |
| `src/components/portal/web3/PortalWeb3BoundaryLazy.tsx` | **Créé** — `next/dynamic`, `ssr: false` |
| `src/lib/portal/portalWeb3LayoutProps.ts` | **Créé** — cookies wagmi + appId serveur |

### Prefetch / warmup

| Fichier | Changement |
|---------|------------|
| `src/components/portal/PortalShell.tsx` | Suppression `warmAllPortalMainRoutes`, `preloadPrivyPortalProvider`, prefetch login au mount |
| `src/components/portal/PortalTopnav.tsx` | Suppression warmup profile au mount |
| `src/lib/portal/portalNavWarmup.ts` | Prefetch Next.js hover/focus uniquement ; `warmAllPortalMainRoutes` deprecated |

### Lazy modales & profil

| Fichier | Changement |
|---------|------------|
| `src/components/portal/bundles/PortalLazyBundleInvestDialog.tsx` | **Créé** |
| `src/components/portal/invest/PortalLazyEarnVaultModal.tsx` | **Créé** |
| `src/components/portal/invest/PortalLazyLedgityVaultModal.tsx` | **Créé** |
| `src/components/portal/profile/PortalProfileExternalWalletConnect.tsx` | **Créé** — Web3 au clic |
| `src/components/portal/markets/PortalCryptoBundlesSection.tsx` | → lazy invest dialog |
| `src/components/portal/invest/PortalPlacerView.tsx` | → lazy bundle + vault modals |
| `src/components/portal/bundles/PortalCryptoBundleDetailScreen.tsx` | → lazy invest dialog |
| `src/components/portal/profile/PortalProfileWalletsSection.tsx` | → connect externe lazy |

### Fix fuite Privy (post-layout)

| Fichier | Changement |
|---------|------------|
| `src/lib/portal/portalAuthPrivySessionStorage.ts` | **Créé** — helpers storage sans SDK Privy |
| `src/lib/portal/navigateToPortalLogin.ts` | Import depuis storage (plus depuis hygiene) |
| `src/components/portal/PortalAuthPrivySessionHygiene.tsx` | Réduit au composant + re-exports |
| `src/lib/portal/usePortalEmailOtpSend.ts` | Import storage pur |
| `src/components/portal/PortalShellMain.tsx` | `PortalRouteCachedPreview` en `dynamic()` |

## Ce qui a quitté le shell global

- `PortalWeb3Providers` (Wagmi, RainbowKit, TanStack Query, ExecutionWallet)
- `PortalAuthPrivyGate` / `PrivyPortalProvider`
- Warmup idle : 6 routes + ~8–11 requêtes API + preload chunk Privy
- Import statique Privy via `navigateToPortalLogin` sur écrans read-only

## Où Web3 est monté maintenant

```
/app/wallet/**     → wallet/layout.tsx → PortalWeb3Boundary
/app/wallets/**    → wallets/layout.tsx
/app/borrow/**     → borrow/layout.tsx
/app/login/**      → login/layout (inchangé)
Modales invest     → PortalLazy* + PortalWeb3BoundaryLazy à l’ouverture
Profil wallet ext. → PortalProfileExternalWalletConnect (clic)
```

## Prefetch retiré

- `warmAllPortalMainRoutes()` au mount `PortalShell`
- `preloadPrivyPortalProvider()` au mount
- `warmPortalRoute(profile)` au mount `PortalTopnav`
- Warmup API (`revalidatePortalCache` dashboard, crypto-wallet, invest, markets, profile) au mount shell

**Conservé :** prefetch Next.js sur hover/focus via `PortalNavLink` → `warmPortalRoute`.

## Dialogs lazy-loadés

- `PortalBundleInvestDialog` (markets, invest, bundle detail)
- `PortalEarnVaultModal`, `PortalLedgityVaultModal` (PlacerView)
- `PortalRouteCachedPreview` (transitions navigation shell)

## Risques résiduels

1. **Profile (339 kB)** — chunk wagmi `43239` encore référencé (connect externe lazy) ; acceptable vs cible 500 kB.
2. **Build flaky sans dev server arrêté** — conflit `.next` si `next dev` tourne ; utiliser `NEXT_WEBPACK_DISABLE_CACHE=1` si ENOENT `_document` / `[locale]/[slug]`.
3. **`PortalRouteCachedPreview` lazy** — léger délai à la première navigation inter-onglets (acceptable vs gain initial).
4. **Phase 2** — `portalSessionRouteHelpers` monolithique côté API server (~5 MB cold) non traité en Phase 1.

## Checklist QA manuelle

- [ ] Login OTP + verify (`/app/login`, `/app/login/verify`)
- [ ] Logout → redirect login + purge session
- [ ] `/app/academy`, `/app/dashboard`, `/app/markets` — chargement rapide, pas d’erreur console Privy
- [ ] `/app/markets` — ouvrir dialog invest bundle → Li.FI + signature OK
- [ ] `/app/profile` — section wallets ; clic connect MetaMask → boundary Web3
- [ ] `/app/wallet/swap` — flow swap complet (Privy + externe)
- [ ] `/app/borrow` — flow Lombard
- [ ] Navigation hover topnav — prefetch sans burst API au premier load

## Validation build

```bash
cd services/arquantix/web
# Arrêter next dev si actif
rm -rf .next
NEXT_WEBPACK_DISABLE_CACHE=1 NODE_ENV=production npm run build 2>&1 | tee /tmp/build-after-phase1.log
```

Build Phase 1 : **succès** (2026-05-29).

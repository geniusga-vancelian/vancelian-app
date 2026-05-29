# Portail — Phase 2 QA & Regression Guardrails

Date : 2026-05-29  
Prérequis : commit Phase 1 `1722c881e`  
Référence Phase 1 : `PORTAL_PERFORMANCE_PHASE1_IMPLEMENTATION_REPORT.md`

## Objectif

Vérifier le comportement post-Phase 1 et empêcher les régressions Web3/prefetch/bundle sans refactor produit ni changement infra.

---

## 1. Garde-fous automatisés

### Commande

```bash
cd services/arquantix/web
npm run test:portal-performance-guard
```

### Règles couvertes

| Règle | Fichiers surveillés | Échec si |
|-------|---------------------|----------|
| `shell-no-privy-sdk` | shell global | `from '@privy-io/react-auth'` |
| `shell-no-wagmi` | shell global | `from 'wagmi'` |
| `shell-no-rainbowkit` | shell global | `from '@rainbow-me/rainbowkit'` |
| `shell-no-portal-web3-providers` | shell global + layout | `PortalWeb3Providers` |
| `shell-no-portal-auth-privy-gate` | shell global | `PortalAuthPrivyGate` |
| `layout-no-portal-web3-providers` | `(shell)/layout.tsx` | import Web3 layout |
| `shell-no-idle-warmup` | `PortalShell.tsx` | appel `warmAllPortalMainRoutes()` |
| `shell-no-privy-preload` | `PortalShell.tsx` | appel `preloadPrivyPortalProvider()` |
| `login-nav-no-privy-hygiene-import` | `navigateToPortalLogin.ts` | import `PortalAuthPrivySessionHygiene` |
| `markets-no-static-bundle-invest-dialog` | sections markets read-only | import statique `PortalBundleInvestDialog` |

**Shell global** = `(shell)/layout.tsx`, `PortalShell.tsx`, `PortalShellMain.tsx`, `PortalTopnav.tsx`.

**Implémentation** : `src/lib/portal/portalPerformanceGuard.ts` + `portalPerformanceGuard.test.ts`.

### Statut (2026-05-29)

```
npm run test:portal-performance-guard → 9/9 pass
```

---

## 2. Budgets First Load JS (documentation)

Constantes exportées : `PORTAL_FIRST_LOAD_JS_BUDGETS_KB` dans `portalPerformanceGuard.ts`.

| Route | Budget max | Phase 1 mesuré | Marge |
|-------|----------:|---------------:|------:|
| `/app/academy` | 250 kB | 124 kB | 126 kB |
| `/app/dashboard` | 300 kB | 195 kB | 105 kB |
| `/app/markets` | 450 kB | 133 kB | 317 kB |
| `/app/profile` | 500 kB | 339 kB | 161 kB |

Source build : `/tmp/build-after-phase1.log` (commit `1722c881e`).

### Vérification manuelle post-build

```bash
cd services/arquantix/web
rm -rf .next
NEXT_WEBPACK_DISABLE_CACHE=1 NODE_ENV=production npm run build 2>&1 | tee /tmp/build-portal-perf.log
grep -E '/app/(academy|dashboard|markets|profile)' /tmp/build-portal-perf.log
```

Parser programmatique (optionnel) :

```typescript
import { scanFirstLoadJsBudgetViolations } from '@/lib/portal/portalPerformanceGuard'
// scanFirstLoadJsBudgetViolations(log) → [] si OK
```

---

## 3. QA manuelle — checklist

Légende : ✅ validé · ⬜ à valider humain · 🔶 smoke HTTP partiel

| # | Scénario | Statut | Notes |
|---|----------|--------|-------|
| 1 | Login OTP (`/app/login` → verify) | 🔶 | HTTP 200 login ; formulaire présent ; pas d’erreur « Configuration Privy » au load. **OTP complet : validation humaine.** |
| 2 | Logout → redirect login | ⬜ | Vérifier purge cookie JWT + redirect `/app/login?signed_out=1` |
| 3 | Dashboard navigation | 🔶 | HTTP 307 sans session (redirect attendu). **Contenu authentifié : validation humaine.** |
| 4 | Markets navigation | 🔶 | HTTP 200. Vérifier sections + WS quotes avec session. |
| 5 | Academy navigation | 🔶 | HTTP 200. Vérifier liste articles + pagination. |
| 6 | Profile page | 🔶 | HTTP 200. Vérifier sections sans Web3 au load. |
| 7 | Profile connect wallet (MetaMask/WC) | ⬜ | Clic → boundary lazy → RainbowKit ; pas de Web3 au load initial |
| 8 | `/app/wallet/swap` | 🔶 | HTTP 200. Flow swap complet (Privy + externe) : **validation humaine.** |
| 9 | `/app/borrow` | 🔶 | HTTP 200. Flow Lombard + signature : **validation humaine.** |
| 10 | Markets bundle invest dialog | ⬜ | Ouvrir dialog depuis section bundles → Li.FI + signature |
| 11 | Vault investment dialog (PlacerView) | ⬜ | Earn/Ledgity modals lazy + Web3 boundary à l’ouverture |
| 12 | Hard refresh `/app/academy` | ⬜ | Pas de chunk Privy 55500 dans Network (DevTools) |
| 13 | Hard refresh `/app/dashboard` | ⬜ | Idem |
| 14 | Hard refresh `/app/markets` | ⬜ | Idem ; Li.FI absent jusqu’à ouverture dialog |
| 15 | Hard refresh `/app/profile` | ⬜ | Wagmi uniquement si connect wallet déclenché |
| 16 | Hard refresh `/app/wallet/swap` | ⬜ | Web3 présent (attendu ~1,6 MB First Load) |

### Smoke HTTP local (2026-05-29, `next dev`)

```
/app/login       → 200
/app/academy     → 200
/app/dashboard   → 307
/app/markets     → 200
/app/profile     → 200
/app/wallet/swap → 200
/app/borrow      → 200
```

### Procédure hard refresh (DevTools)

1. Onglet Network → Disable cache.
2. Hard refresh (Cmd+Shift+R) sur la route.
3. Filtrer JS : vérifier absence de `55500-*` (Privy) sur academy/dashboard/markets.
4. Profile : `43239-*` (wagmi) acceptable seulement après action wallet externe.

---

## 4. Ce qui n’est pas couvert (Phase 3+)

- Split `portalSessionRouteHelpers` (cold start API server).
- Budget CI automatique sur chaque PR (nécessite `next build` en pipeline).
- E2E Playwright login + swap + invest (hors scope Phase 2).

---

## 5. Fichiers Phase 2

| Fichier | Rôle |
|---------|------|
| `src/lib/portal/portalPerformanceGuard.ts` | Règles + budgets + parser build log |
| `src/lib/portal/portalPerformanceGuard.test.ts` | Tests statiques anti-régression |
| `package.json` | Script `test:portal-performance-guard` |
| `docs/arquantix/PORTAL_PERFORMANCE_PHASE2_QA_GUARDRAILS.md` | Ce document |

---

## 6. Prochaine étape recommandée

**Phase 3 — Split API helpers** (`portalSessionRouteHelpers`) pour réduire le cold start des routes read-only API, une fois la checklist QA manuelle (§3) validée par l’équipe.

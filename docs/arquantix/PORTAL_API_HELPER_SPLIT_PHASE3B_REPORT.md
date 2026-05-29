# Portal API Helper Split — Phase 3B Report

Date : 2026-05-29  
Référence audit : [PORTAL_API_HELPER_SPLIT_AUDIT.md](./PORTAL_API_HELPER_SPLIT_AUDIT.md)

## Objectif

Découpler les helpers session JWT purs des dépendances vault/Web3 dans `portalWalletRouteHelpers.ts`, sans changer le comportement API ni toucher aux routes d’exécution (prepare/confirm/quote).

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `src/lib/portal/portalSessionRouteHelpers.ts` | Session JWT, parsing wallet/idempotency — zéro viem/Morpho/Ledgity/Lombard |
| `src/lib/portal/portalVaultRouteHelpers.ts` | Réponses erreurs RPC + `morphoLedgerErrorResponse` |
| `src/lib/portal/portalRequestValidation.ts` | Schéma Zod pur `idempotencyKeySchema` |
| `src/lib/portal/ledgity/ledgityVaultLiquidityErrors.ts` | Classe `LedgityVaultLiquidityError` sans viem |
| `src/lib/portal/portalSessionRouteHelpers.test.ts` | Tests unitaires session + parsing |

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `src/lib/portal/portalWalletRouteHelpers.ts` | Shim deprecated re-export only |
| `src/lib/portal/ledgity/ledgityVaultLiquidity.ts` | Import + re-export erreur depuis fichier pur |
| `src/lib/portal/morphoVaultValidation.ts` | Re-export `idempotencyKeySchema` depuis validation pure |
| `src/lib/portal/portalPerformanceGuard.ts` | Garde-fous Phase 3B (session pur + shim) |
| `src/lib/portal/portalPerformanceGuard.test.ts` | Tests des nouveaux garde-fous |

## Helpers créés / déplacés

### Session (`portalSessionRouteHelpers.ts`)

- `requirePortalSessionToken`
- `requirePortalPersonId`
- `parseWalletAddress`
- `parseIdempotencyKey`
- `resolvePortalSessionAccessToken` / `resolvePortalPersonIdFromAccessToken` — fonctions pures extraites pour tests (même logique que les async wrappers)

### Vault (`portalVaultRouteHelpers.ts`)

- `morphoRpcErrorResponse`
- `ledgityRpcErrorResponse`
- `morphoLedgerErrorResponse` — `instanceof LedgityVaultLiquidityError` via classe extraite

## Routes migrées (18)

### Commit 2 — session-only (13)

| Route | Import |
|-------|--------|
| `wallets/external/route.ts` | `portalSessionRouteHelpers` |
| `wallets/external/[id]/route.ts` | idem |
| `wallets/external/nonce/route.ts` | idem |
| `wallets/external/verify/route.ts` | idem |
| `savings-wallet/route.ts` | idem |
| `savings-wallet/[vault]/route.ts` | idem |
| `crypto-wallet/route.ts` | idem |
| `crypto-wallet/[asset]/route.ts` | idem |
| `morpho/vaults/route.ts` | idem |
| `ledgity/vaults/route.ts` | idem |
| `lombard/markets/route.ts` | idem |
| `lombard/qa-context/route.ts` | idem |
| `privy/send-sponsored-transaction/route.ts` | idem |

### Commit 3 — read-only avec error helpers (5)

| Route | Session | Vault |
|-------|---------|-------|
| `morpho/history/route.ts` | `portalSessionRouteHelpers` | `portalVaultRouteHelpers` |
| `morpho/position/route.ts` | idem | idem |
| `ledgity/history/route.ts` | idem | idem |
| `ledgity/position/route.ts` | idem | idem |
| `lombard/position/route.ts` | idem | `morphoRpcErrorResponse` |

## Routes volontairement non migrées (8 — exécution)

Ces routes restent sur le shim `portalWalletRouteHelpers` (backward compat) :

- `morpho/prepare`, `morpho/confirm`
- `ledgity/prepare`, `ledgity/confirm`
- `lombard/prepare`, `lombard/confirm`, `lombard/quote`, `lombard/capacity`

## Résultats tests

| Suite | Résultat |
|-------|----------|
| `npm run test:portal-performance-guard` | **12/12 pass** |
| `node --import tsx --test src/lib/portal/portalSessionRouteHelpers.test.ts` | **12/12 pass** |
| `npm run test:morpho-vault` | **77 pass**, 3 skip (DB sandbox) |
| `npm run test:ledgity-vault` | **29/29 pass** |
| `npm run test:lombard \|\| true` | **40 pass**, 2 fail pré-existants (`lodash.isplainobject` manquant dans `@morpho-org/blue-sdk`) |

## Build production

```bash
rm -rf .next
NEXT_WEBPACK_DISABLE_CACHE=1 NODE_ENV=production npm run build
```

- **Exit code : 0** (log : `/tmp/build-after-phase3b.log`)
- Première tentative sans `NEXT_WEBPACK_DISABLE_CACHE=1` : échec ENOENT admin academy (problème Next cache connu, non lié Phase 3B)

### Grep post-build

```bash
grep -R "from '@/lib/portal/portalWalletRouteHelpers'" src/app/api/portal
# → 8 routes exécution uniquement (attendu)

grep -R "createPublicClient" .next/server/chunks/*.js | wc -l
# → 4 (routes vault on-chain, inchangé)

grep -R "viem/chains" .next/server/chunks/*.js | wc -l
# → 0
```

## Garde-fous Phase 3B (performance guard)

- `portalSessionRouteHelpers.ts` : interdit viem, morpho, ledgity, lombard, privy, baseRpc
- `portalWalletRouteHelpers.ts` : shim re-export only, aucun `import` statement

## Routes lourdes restantes

Les 8 routes d’exécution ci-dessus importent encore le shim, qui re-exporte `portalVaultRouteHelpers` → graphe viem/ledger conservé pour prepare/confirm/quote (Phase 3C).

## Recommandation Phase 3C

1. Migrer les 8 routes d’exécution vers imports explicites (`portalSessionRouteHelpers` + `portalVaultRouteHelpers`).
2. Supprimer le shim `portalWalletRouteHelpers` après grep zero-import.
3. Optionnel : dynamic `import()` RPC pour listings vault (`morpho/vaults`, `ledgity/vaults`) afin de réduire le cold-start des chunks API read-only restants.
4. Mesurer taille chunk par route API (`next build` + analyse `.next/server/app/api/portal/...`) avant/après migration exécution.

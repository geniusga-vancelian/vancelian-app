# Portal API Helper Split — Phase 3C Report

Date : 2026-05-29  
Prérequis : [PORTAL_API_HELPER_SPLIT_PHASE3B_REPORT.md](./PORTAL_API_HELPER_SPLIT_PHASE3B_REPORT.md)

## Objectif

Supprimer le shim deprecated `portalWalletRouteHelpers.ts` en migrant les dernières routes vers des imports explicites (`portalSessionRouteHelpers` / `portalVaultRouteHelpers`).

## Routes migrées (15)

### Exécution portail (8)

| Route | Session | Vault |
|-------|---------|-------|
| `morpho/prepare` | `requirePortalPersonId` | `morphoLedgerErrorResponse`, `morphoRpcErrorResponse` |
| `morpho/confirm` | idem | `morphoLedgerErrorResponse` |
| `ledgity/prepare` | idem | `ledgityRpcErrorResponse`, `morphoLedgerErrorResponse` |
| `ledgity/confirm` | idem | `morphoLedgerErrorResponse` |
| `lombard/prepare` | idem | `morphoLedgerErrorResponse`, `morphoRpcErrorResponse` |
| `lombard/confirm` | idem | `morphoLedgerErrorResponse` |
| `lombard/quote` | idem | `morphoRpcErrorResponse` |
| `lombard/capacity` | idem | `morphoRpcErrorResponse` |

### Dev sandbox (7 — bonus pour grep zero-import)

| Route | Import |
|-------|--------|
| `dev/morpho-sandbox/status` | `portalSessionRouteHelpers` |
| `dev/morpho-sandbox/seed-current-user` | idem |
| `dev/morpho-sandbox/reset-current-user` | idem |
| `dev/morpho-sandbox/add-yield` | idem |
| `dev/external-wallet-mock/status` | idem |
| `dev/external-wallet-mock/link` | idem |
| `dev/external-wallet-mock/unlink` | idem |

Aucune modification de logique handler — imports uniquement.

## Shim

| Élément | Statut |
|---------|--------|
| `portalWalletRouteHelpers.ts` | **Supprimé** |
| Imports restants dans `src/app`, `src/components`, `src/lib` | **0** (hors garde-fou + tests) |

## Garde-fou performance

`scanDeprecatedPortalWalletRouteHelpersImports` interdit désormais tout import de `@/lib/portal/portalWalletRouteHelpers` sous :

- `src/app/api/portal`
- `src/components`
- `src/lib/portal`

L’ancien check « shim re-export only » a été retiré (fichier inexistant).

## Résultats tests

| Suite | Résultat |
|-------|----------|
| `npm run test:portal-performance-guard` | **12/12 pass** |
| `npm run test:morpho-vault` | **77 pass**, 3 skip |
| `npm run test:ledgity-vault` | **29/29 pass** |
| `npm run test:lombard` | **65/65 pass** |

## Build production

```bash
rm -rf .next
NEXT_WEBPACK_DISABLE_CACHE=1 NODE_ENV=production npm run build
```

- **Exit code : 0** (log : `/tmp/build-after-phase3c.log`)

### Grep post-build

```bash
grep -R "portalWalletRouteHelpers" src/app src/components src/lib
# → uniquement portalPerformanceGuard (+ test)

grep -R "createPublicClient" .next/server/chunks/*.js | wc -l
# → 4 (routes on-chain exécution, attendu)

grep -R "viem/chains" .next/server/chunks/*.js | wc -l
# → 0
```

## Routes API lourdes restantes

Le split helpers est **terminé**. Les routes suivantes restent lourdes par **design métier** (ledger, RPC, tx building) — ce n’est plus une pollution via un helper monolithique :

- `morpho/prepare`, `morpho/confirm`
- `ledgity/prepare`, `ledgity/confirm`
- `lombard/prepare`, `lombard/confirm`, `lombard/quote`, `lombard/capacity`
- Read-only avec RPC inline : `lombard/markets`, listings vault si catalog on-chain

Les routes session-only (`crypto-wallet`, `savings-wallet`, `morpho/vaults`, etc.) n’importent plus le graphe vault via un helper intermédiaire.

## Phase 3D (dynamic RPC import) — encore utile ?

**Verdict : optionnel / basse priorité** sauf si Phase 2b runtime montre encore une lenteur API mesurée.

| Pour | Contre |
|------|--------|
| `lombard/markets` et listings vault pourraient lazy-loader RPC | Phase 3B/3C a déjà isolé session vs vault ; `viem/chains` = 0 dans chunks globaux |
| Réduction cold-start sur 2–3 routes read-only spécifiques | Complexité `import()` + error paths ; gain incertain vs coût maintenance |
| | Les lenteurs restantes sont probablement **exécution métier** ou **DB upstream**, pas le helper |

**Recommandation :** clôturer le chantier performance API helpers. Ne lancer Phase 3D que si profiling runtime (TTFB routes `/api/portal/crypto-wallet`, `/api/portal/lombard/markets`) montre un bundle route-level > seuil après warm-up.

## Bilan chantier Phase 1 → 3C

| Phase | Livrable |
|-------|----------|
| 1 | Shell client sans Web3 global (~124–339 kB read-only) |
| 2 | Guardrails régression |
| 3A | Audit split helpers |
| 3B | Session pur + 18 routes migrées + shim |
| 3C | Shim supprimé, 26 routes sur imports explicites |

**Prochaine action suggérée :** QA runtime Phase 2b humaine ; arrêt du chantier sauf métriques contraires.

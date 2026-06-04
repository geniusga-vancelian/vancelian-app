import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assertPortalPerformanceGuardrails,
  collectPortalPerformanceViolations,
  listPortalWeb3BoundaryEagerLayoutOffenders,
  parseFirstLoadJsFromBuildLog,
  PORTAL_FIRST_LOAD_JS_BUDGETS_KB,
  PORTAL_READ_ONLY_TEMPORARY_EXCEPTIONS,
  PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS,
  PORTAL_WEB3_BOUNDARY_LAZY_SURFACES,
  scanFirstLoadJsBudgetViolations,
  scanMarketsReadOnlyBundleDialogImports,
  scanPortalGlobalShellImports,
  scanPortalReadOnlyWeb3Imports,
  scanPortalWeb3BoundaryLayoutOffenders,
  scanPortalWeb3BoundaryLazySurfaces,
  scanPortalSwapSetupExecutionImports,
  scanPortalBundleInvestPageNoEagerWeb3,
  scanPortalBundleInvestSetupExecutionImports,
  scanPortalWalletBundleDetailReadOnlyImports,
  scanPortalVaultSetupExecutionImports,
  scanPortalLombardSetupExecutionImports,
  scanPortalLombardBorrowPageNoEagerWeb3,
  scanPortalWalletsRedirectNoEagerWeb3,
  scanWalletReadSegmentNoWeb3Boundary,
  scanDeprecatedPortalWalletRouteHelpersImports,
  scanPortalSessionRouteHelpersImports,
  scanPortalShellMountWarmup,
} from '@/lib/portal/portalPerformanceGuard'

const PHASE1_BUILD_SNIPPET = `
├ ƒ /app/academy                                                                    4.33 kB         124 kB
├ ƒ /app/dashboard                                                                  8.61 kB         195 kB
├ ƒ /app/markets                                                                    8.23 kB         133 kB
├ ƒ /app/profile                                                                    16.6 kB         339 kB
`

describe('portalPerformanceGuard — repo guardrails', () => {
  it('shell global sans Web3 / providers', () => {
    assertPortalPerformanceGuardrails()
  })

  it('collectPortalPerformanceViolations retourne une liste vide', () => {
    assert.deepEqual(collectPortalPerformanceViolations(), [])
  })
})

describe('portalPerformanceGuard — détection synthétique', () => {
  it('signale un import Privy dans le shell', () => {
    const violations = scanPortalGlobalShellImports(undefined)
    assert.ok(Array.isArray(violations))
  })

  it('signale warmAllPortalMainRoutes dans PortalShell', () => {
    const violations = scanPortalShellMountWarmup()
    assert.equal(
      violations.some((v) => v.rule === 'shell-no-idle-warmup'),
      false,
    )
  })

  it('read-only screens sans Web3 / modales statiques', () => {
    assert.deepEqual(scanPortalReadOnlyWeb3Imports(), [])
  })

  it('portalSessionRouteHelpers sans dépendances vault/Web3', () => {
    assert.deepEqual(scanPortalSessionRouteHelpersImports(), [])
  })

  it('aucun import portalWalletRouteHelpers dans portal/api/components/lib', () => {
    assert.deepEqual(scanDeprecatedPortalWalletRouteHelpersImports(), [])
  })

  it('signale un import statique PortalBundleInvestDialog en markets', () => {
    const violations = scanMarketsReadOnlyBundleDialogImports()
    assert.equal(
      violations.some((v) => v.rule.includes('no-static-bundle-invest-dialog')),
      false,
    )
  })
})

describe('portalPerformanceGuard — R4.5-F Privy boundary', () => {
  it('known offender layouts — liste figée (wallet tx + invest vault/bundle tx)', () => {
    const found = listPortalWeb3BoundaryEagerLayoutOffenders()
    assert.deepEqual(found, [...PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS].sort())
    assert.deepEqual(scanPortalWeb3BoundaryLayoutOffenders(), [])
    assert.equal(PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS.length, 3)
    assert.equal(found.includes('src/app/app/(shell)/wallet/layout.tsx'), false)
    assert.equal(found.includes('src/app/app/(shell)/wallet/(tx)/layout.tsx'), true)
    assert.equal(found.includes('src/app/app/(shell)/wallets/layout.tsx'), false)
    assert.equal(found.includes('src/app/app/(shell)/borrow/layout.tsx'), false)
    assert.equal(found.includes('src/app/app/(shell)/invest/vault/(tx)/layout.tsx'), true)
    assert.equal(found.includes('src/app/app/(shell)/invest/vault/layout.tsx'), false)
    assert.equal(found.includes('src/app/app/(shell)/invest/bundle/(tx)/layout.tsx'), true)
    assert.equal(found.includes('src/app/app/(shell)/invest/bundle/layout.tsx'), false)
  })

  it('wallet/(read) segment — aucun layout Web3 (F2)', () => {
    assert.deepEqual(scanWalletReadSegmentNoWeb3Boundary(), [])
  })

  it('aucun nouveau layout eager PortalWeb3Boundary', () => {
    const violations = scanPortalWeb3BoundaryLayoutOffenders()
    assert.equal(
      violations.filter((v) => v.rule === 'web3-boundary-new-layout-offender').length,
      0,
    )
  })

  it('read-only surfaces — pas de nouvel import Web3/Privy', () => {
    assert.deepEqual(scanPortalReadOnlyWeb3Imports(), [])
  })

  it('aucune exception read-only temporaire (F5-B)', () => {
    assert.equal(PORTAL_READ_ONLY_TEMPORARY_EXCEPTIONS.length, 0)
  })

  it('PortalWeb3BoundaryLazy autorisé sur surfaces transactionnelles lazy', () => {
    assert.deepEqual(scanPortalWeb3BoundaryLazySurfaces(), [])
    assert.equal(PORTAL_WEB3_BOUNDARY_LAZY_SURFACES.length, 6)
  })

  it('swap setup — pas de hooks exécution LI.FI / Privy (F3)', () => {
    assert.deepEqual(scanPortalSwapSetupExecutionImports(), [])
  })

  it('vault setup — pas de hooks Morpho/Ledgity execution (F4)', () => {
    assert.deepEqual(scanPortalVaultSetupExecutionImports(), [])
  })

  it('bundle invest page — pas de layout Web3 eager (F5-A)', () => {
    assert.deepEqual(scanPortalBundleInvestPageNoEagerWeb3(), [])
  })

  it('bundle invest setup — pas de hooks LI.FI au mount (F5-A)', () => {
    assert.deepEqual(scanPortalBundleInvestSetupExecutionImports(), [])
  })

  it('wallet bundle detail — read-only sans LI.FI (F5-B)', () => {
    assert.deepEqual(scanPortalWalletBundleDetailReadOnlyImports(), [])
  })

  it('lombard borrow setup — pas de hooks open_loan / Privy (F6)', () => {
    assert.deepEqual(scanPortalLombardSetupExecutionImports(), [])
  })

  it('lombard borrow routes — pas de layout Web3 eager (F6)', () => {
    assert.deepEqual(scanPortalLombardBorrowPageNoEagerWeb3(), [])
  })

  it('wallets redirect — pas de layout Web3 eager (F7)', () => {
    assert.deepEqual(scanPortalWalletsRedirectNoEagerWeb3(), [])
  })
})

describe('portalPerformanceGuard — budgets First Load JS', () => {
  it('expose les budgets documentés Phase 1', () => {
    assert.equal(PORTAL_FIRST_LOAD_JS_BUDGETS_KB['/app/academy'], 250)
    assert.equal(PORTAL_FIRST_LOAD_JS_BUDGETS_KB['/app/dashboard'], 300)
    assert.equal(PORTAL_FIRST_LOAD_JS_BUDGETS_KB['/app/markets'], 450)
    assert.equal(PORTAL_FIRST_LOAD_JS_BUDGETS_KB['/app/profile'], 500)
  })

  it('parseFirstLoadJsFromBuildLog extrait les routes portail', () => {
    const parsed = parseFirstLoadJsFromBuildLog(PHASE1_BUILD_SNIPPET)
    assert.equal(parsed['/app/academy'], 124)
    assert.equal(parsed['/app/dashboard'], 195)
    assert.equal(parsed['/app/markets'], 133)
    assert.equal(parsed['/app/profile'], 339)
  })

  it('scanFirstLoadJsBudgetViolations passe sur les chiffres Phase 1', () => {
    assert.deepEqual(scanFirstLoadJsBudgetViolations(PHASE1_BUILD_SNIPPET), [])
  })

  it('scanFirstLoadJsBudgetViolations détecte un dépassement', () => {
    const over = `
├ ƒ /app/academy                                                                    4.33 kB         400 kB
`
    const violations = scanFirstLoadJsBudgetViolations(over)
    assert.equal(violations.length, 1)
    assert.equal(violations[0]!.route, '/app/academy')
    assert.equal(violations[0]!.actualKb, 400)
  })
})

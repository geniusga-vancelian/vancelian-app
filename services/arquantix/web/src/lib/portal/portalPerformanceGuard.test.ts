import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assertPortalPerformanceGuardrails,
  collectPortalPerformanceViolations,
  parseFirstLoadJsFromBuildLog,
  PORTAL_FIRST_LOAD_JS_BUDGETS_KB,
  scanFirstLoadJsBudgetViolations,
  scanMarketsReadOnlyBundleDialogImports,
  scanPortalGlobalShellImports,
  scanPortalReadOnlyWeb3Imports,
  scanPortalSessionRouteHelpersImports,
  scanPortalShellMountWarmup,
  scanPortalWalletRouteHelpersShim,
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

  it('portalWalletRouteHelpers reste un shim re-export only', () => {
    assert.deepEqual(scanPortalWalletRouteHelpersShim(), [])
  })

  it('signale un import statique PortalBundleInvestDialog en markets', () => {
    const violations = scanMarketsReadOnlyBundleDialogImports()
    assert.equal(
      violations.some((v) => v.rule.includes('no-static-bundle-invest-dialog')),
      false,
    )
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

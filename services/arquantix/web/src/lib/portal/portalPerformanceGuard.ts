import fs from 'node:fs'
import path from 'node:path'

/** Budgets First Load JS (production build Next.js) — post Phase 1. */
export const PORTAL_FIRST_LOAD_JS_BUDGETS_KB = {
  '/app/academy': 250,
  '/app/dashboard': 300,
  '/app/markets': 450,
  '/app/profile': 500,
} as const

export type PortalFirstLoadRoute = keyof typeof PORTAL_FIRST_LOAD_JS_BUDGETS_KB

/** Fichiers toujours montés via le shell portail read-only. */
export const PORTAL_GLOBAL_SHELL_RELATIVE_PATHS = [
  'src/app/app/(shell)/layout.tsx',
  'src/components/portal/PortalShell.tsx',
  'src/components/portal/PortalShellMain.tsx',
  'src/components/portal/PortalTopnav.tsx',
] as const

/** Sections markets read-only — pas d’import statique du dialog invest. */
export const MARKETS_READ_ONLY_GUARD_PATHS = [
  'src/components/portal/markets/PortalCryptoBundlesSection.tsx',
  'src/components/portal/markets/PortalMarketsScreen.tsx',
] as const

export type PortalPerformanceViolation = {
  rule: string
  file: string
  detail: string
}

type ForbiddenPattern = {
  rule: string
  pattern: RegExp
}

const SHELL_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'shell-no-privy-sdk', pattern: /from\s+['"]@privy-io\/react-auth['"]/ },
  { rule: 'shell-no-wagmi', pattern: /from\s+['"]wagmi['"]/ },
  { rule: 'shell-no-rainbowkit', pattern: /from\s+['"]@rainbow-me\/rainbowkit['"]/ },
  { rule: 'shell-no-portal-web3-providers', pattern: /PortalWeb3Providers/ },
  { rule: 'shell-no-portal-auth-privy-gate', pattern: /PortalAuthPrivyGate/ },
  { rule: 'shell-no-privy-portal-provider', pattern: /PrivyPortalProvider/ },
  { rule: 'shell-no-external-wallet-provider', pattern: /ExternalWalletProvider/ },
]

const STATIC_BUNDLE_INVEST_DIALOG_IMPORT =
  /import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*\s,]+)\s+from\s+['"][^'"]*PortalBundleInvestDialog['"]/

const PORTAL_SHELL_LAYOUT_PATH = 'src/app/app/(shell)/layout.tsx'
const PORTAL_SHELL_PATH = 'src/components/portal/PortalShell.tsx'
const NAVIGATE_TO_LOGIN_PATH = 'src/lib/portal/navigateToPortalLogin.ts'

function resolveWebRoot(webRoot?: string): string {
  return webRoot ?? path.join(__dirname, '..', '..', '..')
}

function readRelativeFile(webRoot: string, relativePath: string): string {
  const absolute = path.join(webRoot, relativePath)
  if (!fs.existsSync(absolute)) {
    throw new Error(`portalPerformanceGuard: missing file ${relativePath}`)
  }
  return fs.readFileSync(absolute, 'utf8')
}

export function scanPortalGlobalShellImports(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_GLOBAL_SHELL_RELATIVE_PATHS) {
    const source = readRelativeFile(root, relativePath)
    for (const { rule, pattern } of SHELL_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule,
          file: relativePath,
          detail: `Forbidden pattern ${pattern} in global portal shell`,
        })
      }
    }
  }

  return violations
}

export function scanPortalShellLayoutWeb3Imports(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const source = readRelativeFile(root, PORTAL_SHELL_LAYOUT_PATH)
  const violations: PortalPerformanceViolation[] = []

  if (/PortalWeb3Providers/.test(source)) {
    violations.push({
      rule: 'layout-no-portal-web3-providers',
      file: PORTAL_SHELL_LAYOUT_PATH,
      detail: 'PortalWeb3Providers must not be imported from (shell)/layout.tsx',
    })
  }

  return violations
}

export function scanPortalShellMountWarmup(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const source = readRelativeFile(root, PORTAL_SHELL_PATH)
  const violations: PortalPerformanceViolation[] = []

  if (/warmAllPortalMainRoutes\s*\(/.test(source)) {
    violations.push({
      rule: 'shell-no-idle-warmup',
      file: PORTAL_SHELL_PATH,
      detail: 'warmAllPortalMainRoutes must not be called from PortalShell',
    })
  }

  if (/preloadPrivyPortalProvider\s*\(/.test(source)) {
    violations.push({
      rule: 'shell-no-privy-preload',
      file: PORTAL_SHELL_PATH,
      detail: 'preloadPrivyPortalProvider must not be called from PortalShell mount',
    })
  }

  return violations
}

export function scanNavigateToPortalLoginImports(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const source = readRelativeFile(root, NAVIGATE_TO_LOGIN_PATH)
  const violations: PortalPerformanceViolation[] = []

  if (/PortalAuthPrivySessionHygiene/.test(source)) {
    violations.push({
      rule: 'login-nav-no-privy-hygiene-import',
      file: NAVIGATE_TO_LOGIN_PATH,
      detail:
        'navigateToPortalLogin must import storage helpers only (portalAuthPrivySessionStorage), not PortalAuthPrivySessionHygiene',
    })
  }

  return violations
}

export function scanMarketsReadOnlyBundleDialogImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of MARKETS_READ_ONLY_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    if (STATIC_BUNDLE_INVEST_DIALOG_IMPORT.test(source)) {
      violations.push({
        rule: 'markets-no-static-bundle-invest-dialog',
        file: relativePath,
        detail: 'Use PortalLazyBundleInvestDialog instead of static PortalBundleInvestDialog',
      })
    }
  }

  return violations
}

/** Parse la table `Route (app)` d’un log `next build` (First Load JS en kB). */
export function parseFirstLoadJsFromBuildLog(log: string): Partial<Record<PortalFirstLoadRoute, number>> {
  const out: Partial<Record<PortalFirstLoadRoute, number>> = {}

  for (const route of Object.keys(PORTAL_FIRST_LOAD_JS_BUDGETS_KB) as PortalFirstLoadRoute[]) {
    const escaped = route.replace(/\//g, '\\/')
    const pattern = new RegExp(
      `├\\s[ƒ○]\\s${escaped}\\s+[\\d.]+\\s+kB\\s+([\\d.]+)\\s+kB`,
    )
    const match = log.match(pattern)
    if (match?.[1]) {
      out[route] = Number.parseFloat(match[1])
    }
  }

  return out
}

export function scanFirstLoadJsBudgetViolations(
  log: string,
): Array<{ route: PortalFirstLoadRoute; actualKb: number; budgetKb: number }> {
  const parsed = parseFirstLoadJsFromBuildLog(log)
  const violations: Array<{ route: PortalFirstLoadRoute; actualKb: number; budgetKb: number }> = []

  for (const [route, budgetKb] of Object.entries(PORTAL_FIRST_LOAD_JS_BUDGETS_KB) as Array<
    [PortalFirstLoadRoute, number]
  >) {
    const actualKb = parsed[route]
    if (actualKb === undefined) continue
    if (actualKb >= budgetKb) {
      violations.push({ route, actualKb, budgetKb })
    }
  }

  return violations
}

export function collectPortalPerformanceViolations(webRoot?: string): PortalPerformanceViolation[] {
  return [
    ...scanPortalGlobalShellImports(webRoot),
    ...scanPortalShellLayoutWeb3Imports(webRoot),
    ...scanPortalShellMountWarmup(webRoot),
    ...scanNavigateToPortalLoginImports(webRoot),
    ...scanMarketsReadOnlyBundleDialogImports(webRoot),
  ]
}

export function assertPortalPerformanceGuardrails(webRoot?: string): void {
  const violations = collectPortalPerformanceViolations(webRoot)
  if (violations.length === 0) return

  const message = violations
    .map((v) => `[${v.rule}] ${v.file}: ${v.detail}`)
    .join('\n')
  throw new Error(`Portal performance guardrails failed:\n${message}`)
}

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

/** Écrans portail read-only — pas de SDK Web3 / modales d’exécution statiques. */
export const PORTAL_READ_ONLY_GUARD_PATHS = [
  'src/components/portal/academy/PortalAcademyScreen.tsx',
  'src/components/portal/academy/PortalArticleScreen.tsx',
  'src/components/portal/dashboard/PortalDashboardScreen.tsx',
  'src/components/portal/markets/PortalMarketsScreen.tsx',
  'src/components/portal/markets/PortalCryptoBundlesSection.tsx',
  'src/components/portal/markets/PortalAllCryptoScreen.tsx',
  'src/components/portal/profile/PortalProfileScreen.tsx',
  'src/components/portal/profile/PortalProfileWalletsSection.tsx',
  'src/components/portal/invest/PortalInvestScreen.tsx',
  'src/components/portal/invest/PortalPlacerView.tsx',
  'src/lib/portal/usePortalCachedScreen.ts',
] as const

/** @deprecated alias — préférer PORTAL_READ_ONLY_GUARD_PATHS */
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

/** SDK / providers Web3 interdits dans le shell global et les écrans read-only. */
export const PORTAL_WEB3_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'no-privy-sdk', pattern: /from\s+['"]@privy-io\/react-auth['"]/ },
  { rule: 'no-wagmi', pattern: /from\s+['"]wagmi['"]/ },
  { rule: 'no-rainbowkit', pattern: /from\s+['"]@rainbow-me\/rainbowkit['"]/ },
  { rule: 'no-viem', pattern: /from\s+['"]viem['"]/ },
  { rule: 'no-lifi-sdk', pattern: /from\s+['"]@lifi\// },
  { rule: 'no-portal-web3-providers', pattern: /PortalWeb3Providers/ },
  { rule: 'no-portal-auth-privy-gate', pattern: /PortalAuthPrivyGate/ },
  { rule: 'no-privy-portal-provider', pattern: /PrivyPortalProvider/ },
  { rule: 'no-external-wallet-provider', pattern: /ExternalWalletProvider/ },
  { rule: 'no-connect-external-wallet-button', pattern: /ConnectExternalWalletButton/ },
]

const SHELL_FORBIDDEN_IMPORTS = PORTAL_WEB3_FORBIDDEN_IMPORTS.map(({ rule, pattern }) => ({
  rule: `shell-${rule}`,
  pattern,
}))

const STATIC_EXECUTION_DIALOG_IMPORTS: Array<{ rule: string; pattern: RegExp; hint: string }> = [
  {
    rule: 'no-static-bundle-invest-dialog',
    pattern:
      /import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*\s,]+)\s+from\s+['"][^'"]*PortalBundleInvestDialog['"]/,
    hint: 'Use PortalLazyBundleInvestDialog',
  },
  {
    rule: 'no-static-earn-vault-modal',
    pattern:
      /import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*\s,]+)\s+from\s+['"][^'"]*PortalEarnVaultModal['"]/,
    hint: 'Use PortalLazyEarnVaultModal',
  },
  {
    rule: 'no-static-ledgity-vault-modal',
    pattern:
      /import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*\s,]+)\s+from\s+['"][^'"]*PortalLedgityVaultModal['"]/,
    hint: 'Use PortalLazyLedgityVaultModal',
  },
]

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

function scanReadOnlyPaths(
  webRoot: string,
  relativePaths: readonly string[],
  rulePrefix: string,
): PortalPerformanceViolation[] {
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of relativePaths) {
    const source = readRelativeFile(webRoot, relativePath)
    for (const { rule, pattern } of PORTAL_WEB3_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule: `${rulePrefix}-${rule}`,
          file: relativePath,
          detail: `Forbidden Web3 import in read-only portal surface`,
        })
      }
    }
    for (const { rule, pattern, hint } of STATIC_EXECUTION_DIALOG_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule: `${rulePrefix}-${rule}`,
          file: relativePath,
          detail: hint,
        })
      }
    }
  }

  return violations
}

export function scanPortalReadOnlyWeb3Imports(webRoot?: string): PortalPerformanceViolation[] {
  return scanReadOnlyPaths(resolveWebRoot(webRoot), PORTAL_READ_ONLY_GUARD_PATHS, 'readonly')
}

/** @deprecated alias — préférer scanPortalReadOnlyWeb3Imports */
export function scanMarketsReadOnlyBundleDialogImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  return scanPortalReadOnlyWeb3Imports(webRoot).filter((v) =>
    MARKETS_READ_ONLY_GUARD_PATHS.some((p) => v.file === p),
  )
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
    ...scanPortalReadOnlyWeb3Imports(webRoot),
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

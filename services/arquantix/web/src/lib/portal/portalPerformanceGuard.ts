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

/** Écrans portail read-only — pas de SDK Web3 / modales d’exécution statiques (R4.5-F1). */
export const PORTAL_READ_ONLY_GUARD_PATHS = [
  'src/components/portal/academy/PortalAcademyScreen.tsx',
  'src/components/portal/academy/PortalArticleScreen.tsx',
  'src/components/portal/dashboard/PortalDashboardScreen.tsx',
  'src/components/portal/markets/PortalMarketsScreen.tsx',
  'src/components/portal/markets/PortalCryptoBundlesSection.tsx',
  'src/components/portal/markets/PortalAllCryptoScreen.tsx',
  'src/components/portal/markets/PortalInstrumentDetailScreen.tsx',
  'src/components/portal/profile/PortalProfileScreen.tsx',
  'src/components/portal/profile/PortalProfileWalletsSection.tsx',
  'src/components/portal/invest/PortalInvestScreen.tsx',
  'src/components/portal/invest/PortalPlacerView.tsx',
  'src/components/portal/credit-line/PortalCreditLineScreen.tsx',
  'src/components/portal/wallet/PortalCryptoWalletScreen.tsx',
  'src/components/portal/wallet/PortalCryptoWalletDetailScreen.tsx',
  'src/components/portal/wallet/PortalCryptoWalletTransactionsScreen.tsx',
  'src/components/portal/wallet/PortalCryptoWalletBundleDetailScreen.tsx',
  'src/components/portal/wallet/PortalCryptoWalletBundleTransactionDetailScreen.tsx',
  'src/components/portal/wallet/PortalSavingsWalletScreen.tsx',
  'src/components/portal/wallet/PortalSavingsVaultDetailScreen.tsx',
  'src/components/portal/lombard/PortalLombardPositionDetailScreen.tsx',
  'src/lib/portal/usePortalCachedScreen.ts',
] as const

/**
 * Dettes read-only connues — ne pas ajouter d’entrées sans ticket F2–F6.
 * Le guard ignore ces violations jusqu’à retrait de l’exception.
 */
/** Dettes read-only temporaires — vide post F5-B ; ne pas ajouter sans ticket. */
export const PORTAL_READ_ONLY_TEMPORARY_EXCEPTIONS: ReadonlyArray<{ file: string; rule: string }> =
  []

/** Wallet bundle detail — read-only pur (R4.5-F5-B). */
export const PORTAL_WALLET_BUNDLE_DETAIL_GUARD_PATHS = [
  'src/components/portal/wallet/PortalCryptoWalletBundleDetailScreen.tsx',
] as const

export const PORTAL_WALLET_BUNDLE_DETAIL_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'wallet-bundle-no-lifi-invest', pattern: /\buseBundleLifiInvest\b/ },
  { rule: 'wallet-bundle-no-lifi-rebalance', pattern: /\buseBundleLifiRebalance\b/ },
  { rule: 'wallet-bundle-no-allocation-actions-panel', pattern: /\bPortalBundleAllocationActionsPanel\b/ },
]

/**
 * Layouts montant PortalWeb3Boundary (eager) — liste figée ; échec CI si un layout hors liste apparaît.
 * R4.5-F2 : `wallet/layout.tsx` supprimé → boundary limitée à `wallet/(tx)/layout.tsx`.
 */
/** R4.5-F7 : seul layout segment Web3 eager restant — routes tx wallet (swap, create, deposit, withdraw). */
export const PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS = [
  'src/app/app/(shell)/wallet/(tx)/layout.tsx',
] as const

/** R4.5-F5-A — page invest bundle : pas de layout Web3 eager. */
export const PORTAL_BUNDLE_INVEST_PAGE_GUARD_PATHS = [
  'src/app/app/(shell)/invest/bundle/[portfolioId]/page.tsx',
  'src/components/portal/bundles/PortalBundleInvestScreen.tsx',
] as const

export const PORTAL_BUNDLE_INVEST_SETUP_GUARD_PATHS = [
  'src/components/portal/bundles/PortalBundleInvestDialog.tsx',
] as const

export const PORTAL_BUNDLE_INVEST_SETUP_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'bundle-setup-no-lifi-invest', pattern: /\buseBundleLifiInvest\b/ },
  { rule: 'bundle-setup-no-lifi-withdraw', pattern: /\buseBundleLifiWithdraw\b/ },
  { rule: 'bundle-setup-no-lifi-rebalance', pattern: /\buseBundleLifiRebalance\b/ },
]

/** R4.5-F2 — segments read-only : aucun layout ne doit importer PortalWeb3Boundary. */
export const PORTAL_WALLET_READ_SEGMENT_LAYOUT_SCAN_DIR = 'src/app/app/(shell)/wallet/(read)' as const

/**
 * Swap setup (to / from / amount) — BFF-only ; exécution LI.FI via PortalSwapExecutionController (R4.5-F3).
 */
export const PORTAL_SWAP_SETUP_GUARD_PATHS = [
  'src/components/portal/swap/PortalSwapFlow.tsx',
  'src/components/portal/swap/PortalSwapAmountStep.tsx',
  'src/components/portal/swap/PortalSwapFromStep.tsx',
  'src/components/portal/swap/PortalSwapToStep.tsx',
] as const

/** Hooks d’exécution swap interdits pendant le setup (montés dans PortalSwapExecutionController). */
export const PORTAL_SWAP_SETUP_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'swap-setup-no-lifi-execution', pattern: /\buseLifiSwapExecution\b/ },
  { rule: 'swap-setup-no-execution-wallet', pattern: /\buseExecutionWallet\b/ },
  { rule: 'swap-setup-no-portal-tx-signer', pattern: /\busePortalTxSigner\b/ },
  { rule: 'swap-setup-no-privy-live-session', pattern: /\busePrivyLiveSession\b/ },
]

/**
 * Vault setup (amount / continue) — BFF-only ; exécution via PortalVaultExecutionController (R4.5-F4).
 */
export const PORTAL_VAULT_SETUP_GUARD_PATHS = [
  'src/components/portal/invest/PortalDefiVaultInvestFlow.tsx',
  'src/components/portal/wallet/PortalSavingsVaultOperationPanel.tsx',
] as const

export const PORTAL_VAULT_SETUP_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'vault-setup-no-morpho-execution', pattern: /\busePortalMorphoVaultExecution\b/ },
  { rule: 'vault-setup-no-ledgity-execution', pattern: /\busePortalLedgityVaultExecution\b/ },
]

/**
 * Lombard borrow setup (intro / form) — BFF-only ; exécution via PortalLombardExecutionController (R4.5-F6).
 */
export const PORTAL_LOMBARD_SETUP_GUARD_PATHS = [
  'src/components/portal/lombard/PortalLombardFlow.tsx',
] as const

export const PORTAL_LOMBARD_SETUP_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'lombard-setup-no-open-loan-execution', pattern: /\busePortalLombardExecution\b/ },
  { rule: 'lombard-setup-no-portal-tx-signer', pattern: /\busePortalTxSigner\b/ },
  { rule: 'lombard-setup-no-privy-sdk', pattern: /from\s+['"]@privy-io\/react-auth['"]/ },
]

/** R4.5-F6 — routes borrow sans layout Web3 eager. */
export const PORTAL_LOMBARD_BORROW_PAGE_GUARD_PATHS = [
  'src/app/app/(shell)/borrow/page.tsx',
  'src/app/app/(shell)/borrow/position/page.tsx',
] as const

/** R4.5-F7 — redirect /app/wallets → profile#wallets, sans Web3 eager. */
export const PORTAL_WALLETS_REDIRECT_PAGE_GUARD_PATHS = [
  'src/app/app/(shell)/wallets/page.tsx',
] as const

/** Chemins où une boundary Web3 (eager ou lazy) ou Privy auth est légitime. */
export const PORTAL_WEB3_BOUNDARY_ALLOWED_PATHS = [
  'src/app/app/login/layout.tsx',
  'src/app/app/login/page.tsx',
  'src/app/app/login/verify/page.tsx',
  'src/components/portal/PortalAuthPrivyWrapper.tsx',
  'src/components/portal/PortalAuthPrivyGate.tsx',
  'src/components/portal/PrivyPortalProvider.tsx',
  'src/components/portal/web3/PortalWeb3Boundary.tsx',
  'src/components/portal/web3/PortalWeb3BoundaryLazy.tsx',
  'src/components/portal/PortalWeb3Providers.tsx',
  'src/lib/wallet/externalWalletProvider.tsx',
  'src/components/portal/bundles/PortalLazyBundleInvestDialog.tsx',
  'src/components/portal/bundles/PortalBundleExecutionController.tsx',
  'src/components/portal/bundles/PortalLazyBundleWithdrawShell.tsx',
  'src/components/portal/bundles/PortalBundleAllocationActionsPanel.tsx',
  'src/components/portal/bundles/PortalLazyBundleAllocationActions.tsx',
  'src/components/portal/invest/PortalLazyEarnVaultModal.tsx',
  'src/components/portal/invest/PortalLazyLedgityVaultModal.tsx',
  'src/components/portal/profile/PortalProfileExternalWalletConnect.tsx',
  'src/components/portal/invest/PortalVaultExecutionController.tsx',
  'src/components/portal/lombard/PortalLombardExecutionController.tsx',
  'src/app/dev/wallet-sandbox/page.tsx',
  ...PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS,
] as const

/** Surfaces transactionnelles — doivent importer PortalWeb3BoundaryLazy (pas boundary eager). */
export const PORTAL_WEB3_BOUNDARY_LAZY_SURFACES = [
  'src/components/portal/bundles/PortalBundleExecutionController.tsx',
  'src/components/portal/bundles/PortalLazyBundleWithdrawShell.tsx',
  'src/components/portal/bundles/PortalLazyBundleAllocationActions.tsx',
  'src/components/portal/invest/PortalLazyEarnVaultModal.tsx',
  'src/components/portal/invest/PortalLazyLedgityVaultModal.tsx',
  'src/components/portal/profile/PortalProfileExternalWalletConnect.tsx',
  'src/components/portal/lombard/PortalLombardExecutionController.tsx',
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

/** Imports interdits sur écrans read-only en plus du socle (R4.5-F1). */
export const PORTAL_READ_ONLY_EXTRA_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  {
    rule: 'no-portal-web3-boundary-eager',
    pattern: /from\s+['"]@\/components\/portal\/web3\/PortalWeb3Boundary['"]/,
  },
  { rule: 'no-use-portal-tx-signer', pattern: /\busePortalTxSigner\b/ },
  { rule: 'no-use-privy-live-session', pattern: /\busePrivyLiveSession\b/ },
  { rule: 'no-use-privy', pattern: /\busePrivy\b/ },
  { rule: 'no-use-wallets', pattern: /\buseWallets\b/ },
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

const READ_ONLY_STATIC_EXECUTION_IMPORTS: Array<{ rule: string; pattern: RegExp; hint: string }> = [
  ...STATIC_EXECUTION_DIALOG_IMPORTS,
  {
    rule: 'no-static-bundle-allocation-panel',
    pattern:
      /import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*\s,]+)\s+from\s+['"][^'"]*PortalBundleAllocationPanel['"]/,
    hint: 'Lazy-load bundle allocation execution (R4.5-F5)',
  },
]

const PORTAL_SHELL_LAYOUT_PATH = 'src/app/app/(shell)/layout.tsx'
const PORTAL_SHELL_PATH = 'src/components/portal/PortalShell.tsx'
const NAVIGATE_TO_LOGIN_PATH = 'src/lib/portal/navigateToPortalLogin.ts'
const PORTAL_SESSION_ROUTE_HELPERS_PATH = 'src/lib/portal/portalSessionRouteHelpers.ts'

/** Chemins scannés pour interdire le shim supprimé portalWalletRouteHelpers (Phase 3C). */
const PORTAL_WALLET_HELPER_FORBIDDEN_SCAN_DIRS = [
  'src/app/api/portal',
  'src/components',
  'src/lib/portal',
] as const

const PORTAL_WALLET_ROUTE_HELPERS_IMPORT_PATTERN =
  /from\s+['"]@\/lib\/portal\/portalWalletRouteHelpers['"]/

/** Imports vault/Web3 interdits dans les helpers session purs (Phase 3B). */
const PORTAL_SESSION_HELPER_FORBIDDEN_IMPORTS: ForbiddenPattern[] = [
  { rule: 'session-no-viem', pattern: /from\s+['"]viem/ },
  { rule: 'session-no-viem-chains', pattern: /from\s+['"]viem\/chains/ },
  { rule: 'session-no-morpho', pattern: /from\s+['"]@\/lib\/portal\/morpho/ },
  { rule: 'session-no-ledgity', pattern: /from\s+['"]@\/lib\/portal\/ledgity/ },
  { rule: 'session-no-lombard', pattern: /from\s+['"]@\/lib\/portal\/lombard/ },
  { rule: 'session-no-privy', pattern: /from\s+['"]@privy-io/ },
  { rule: 'session-no-base-rpc', pattern: /from\s+['"]@\/lib\/blockchain\/baseRpc/ },
]

function listSourceFilesUnder(webRoot: string, relativeDir: string): string[] {
  const absoluteDir = path.join(webRoot, relativeDir)
  if (!fs.existsSync(absoluteDir)) return []

  const files: string[] = []
  const stack = [absoluteDir]

  while (stack.length > 0) {
    const current = stack.pop()
    if (!current) continue
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name)
      if (entry.isDirectory()) {
        stack.push(absolute)
        continue
      }
      if (/\.(tsx?|jsx?|mjs|cjs)$/.test(entry.name)) {
        files.push(path.relative(webRoot, absolute).split(path.sep).join('/'))
      }
    }
  }

  return files
}

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

export function scanPortalSessionRouteHelpersImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const source = readRelativeFile(root, PORTAL_SESSION_ROUTE_HELPERS_PATH)
  const violations: PortalPerformanceViolation[] = []

  for (const { rule, pattern } of PORTAL_SESSION_HELPER_FORBIDDEN_IMPORTS) {
    if (pattern.test(source)) {
      violations.push({
        rule,
        file: PORTAL_SESSION_ROUTE_HELPERS_PATH,
        detail: 'portalSessionRouteHelpers must not import vault/Web3 dependencies',
      })
    }
  }

  return violations
}

export function scanDeprecatedPortalWalletRouteHelpersImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativeDir of PORTAL_WALLET_HELPER_FORBIDDEN_SCAN_DIRS) {
    for (const relativePath of listSourceFilesUnder(root, relativeDir)) {
      const source = readRelativeFile(root, relativePath)
      if (PORTAL_WALLET_ROUTE_HELPERS_IMPORT_PATTERN.test(source)) {
        violations.push({
          rule: 'no-portal-wallet-route-helpers',
          file: relativePath,
          detail:
            'portalWalletRouteHelpers was removed in Phase 3C; import portalSessionRouteHelpers or portalVaultRouteHelpers',
        })
      }
    }
  }

  return violations
}

function isReadOnlyTemporaryException(file: string, rule: string): boolean {
  return PORTAL_READ_ONLY_TEMPORARY_EXCEPTIONS.some(
    (entry) => entry.file === file && entry.rule === rule,
  )
}

function scanReadOnlyPaths(
  webRoot: string,
  relativePaths: readonly string[],
  rulePrefix: string,
): PortalPerformanceViolation[] {
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of relativePaths) {
    const source = readRelativeFile(webRoot, relativePath)
    const allForbidden = [
      ...PORTAL_WEB3_FORBIDDEN_IMPORTS,
      ...PORTAL_READ_ONLY_EXTRA_FORBIDDEN_IMPORTS,
    ]
    for (const { rule, pattern } of allForbidden) {
      if (pattern.test(source)) {
        const fullRule = `${rulePrefix}-${rule}`
        if (isReadOnlyTemporaryException(relativePath, fullRule)) continue
        violations.push({
          rule: fullRule,
          file: relativePath,
          detail: `Forbidden Web3 import in read-only portal surface`,
        })
      }
    }
    for (const { rule, pattern, hint } of READ_ONLY_STATIC_EXECUTION_IMPORTS) {
      if (pattern.test(source)) {
        const fullRule = `${rulePrefix}-${rule}`
        if (isReadOnlyTemporaryException(relativePath, fullRule)) continue
        violations.push({
          rule: fullRule,
          file: relativePath,
          detail: hint,
        })
      }
    }
  }

  return violations
}

const EAGER_WEB3_BOUNDARY_IMPORT =
  /import\s+[\s\S]*?from\s+['"]@\/components\/portal\/web3\/PortalWeb3Boundary['"]/

function listLayoutFilesUnder(webRoot: string, relativeDir: string): string[] {
  return listSourceFilesUnder(webRoot, relativeDir).filter((f) => f.endsWith('layout.tsx'))
}

/** Liste les layouts `(shell)` qui importent PortalWeb3Boundary (eager). */
export function listPortalWeb3BoundaryEagerLayoutOffenders(webRoot?: string): string[] {
  const root = resolveWebRoot(webRoot)
  const layouts = listLayoutFilesUnder(root, 'src/app/app/(shell)')
  const offenders: string[] = []

  for (const relativePath of layouts) {
    const source = readRelativeFile(root, relativePath)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      offenders.push(relativePath)
    }
  }

  return offenders.sort()
}

/**
 * Échoue si un nouveau layout eager apparaît ou si la liste figée diverge (ajout = régression).
 * Retrait d’un offender (F2+) : mettre à jour PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS + ce test.
 */
export function scanPortalWeb3BoundaryLayoutOffenders(webRoot?: string): PortalPerformanceViolation[] {
  const found = listPortalWeb3BoundaryEagerLayoutOffenders(webRoot)
  const known = [...PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS].sort()
  const violations: PortalPerformanceViolation[] = []

  if (found.length !== known.length) {
    violations.push({
      rule: 'web3-boundary-offender-count-changed',
      file: 'PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS',
      detail: `Expected ${known.length} eager layout offenders, found ${found.length}: ${found.join(', ')}`,
    })
  }

  for (const layoutPath of found) {
    if (!known.includes(layoutPath as (typeof known)[number])) {
      violations.push({
        rule: 'web3-boundary-new-layout-offender',
        file: layoutPath,
        detail:
          'New PortalWeb3Boundary layout detected — add to F2 plan or KNOWN_OFFENDER list with explicit review',
      })
    }
  }

  const foundSet = new Set(found)
  for (const layoutPath of known) {
    if (!foundSet.has(layoutPath)) {
      violations.push({
        rule: 'web3-boundary-known-offender-removed',
        file: layoutPath,
        detail:
          'Layout removed from eager Web3 boundary — update PORTAL_WEB3_BOUNDARY_KNOWN_OFFENDER_LAYOUTS (expected after F2+)',
      })
    }
  }

  return violations
}

/** Les surfaces lazy transactionnelles doivent utiliser PortalWeb3BoundaryLazy. */
/** Wallet read segment — pas de boundary Web3 (R4.5-F2). */
export function scanWalletReadSegmentNoWeb3Boundary(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of listLayoutFilesUnder(root, PORTAL_WALLET_READ_SEGMENT_LAYOUT_SCAN_DIR)) {
    const source = readRelativeFile(root, relativePath)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'wallet-read-layout-no-web3-boundary',
        file: relativePath,
        detail: 'wallet/(read) layouts must not mount PortalWeb3Boundary',
      })
    }
  }

  const legacyWalletLayout = 'src/app/app/(shell)/wallet/layout.tsx'
  if (fs.existsSync(path.join(root, legacyWalletLayout))) {
    const source = readRelativeFile(root, legacyWalletLayout)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'wallet-root-layout-removed-f2',
        file: legacyWalletLayout,
        detail:
          'wallet/layout.tsx must not wrap read-only routes — use wallet/(tx)/layout.tsx only (R4.5-F2)',
      })
    }
  }

  return violations
}

export function scanPortalWeb3BoundaryLazySurfaces(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_WEB3_BOUNDARY_LAZY_SURFACES) {
    const source = readRelativeFile(root, relativePath)
    if (!/PortalWeb3BoundaryLazy/.test(source)) {
      violations.push({
        rule: 'lazy-surface-missing-boundary-lazy',
        file: relativePath,
        detail: 'Transaction lazy surface must wrap children with PortalWeb3BoundaryLazy',
      })
    }
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'lazy-surface-eager-boundary-import',
        file: relativePath,
        detail: 'Do not import eager PortalWeb3Boundary in lazy transaction surfaces',
      })
    }
  }

  return violations
}

export function scanPortalReadOnlyWeb3Imports(webRoot?: string): PortalPerformanceViolation[] {
  return scanReadOnlyPaths(resolveWebRoot(webRoot), PORTAL_READ_ONLY_GUARD_PATHS, 'readonly')
}

/** Swap setup — pas de hooks LI.FI / signer / Privy live (R4.5-F3). */
export function scanPortalSwapSetupExecutionImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_SWAP_SETUP_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    for (const { rule, pattern } of PORTAL_SWAP_SETUP_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule,
          file: relativePath,
          detail: 'Swap setup must stay API/BFF-only; use PortalSwapExecutionController for review+',
        })
      }
    }
  }

  return violations
}

/** Bundle invest setup — pas de hooks LI.FI (R4.5-F5-A). */
export function scanPortalBundleInvestSetupExecutionImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_BUNDLE_INVEST_SETUP_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    for (const { rule, pattern } of PORTAL_BUNDLE_INVEST_SETUP_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule,
          file: relativePath,
          detail: 'Bundle invest setup must stay BFF-only; use PortalBundleExecutionController for review+',
        })
      }
    }
  }

  return violations
}

/** Wallet bundle detail — pas de hooks LI.FI / panel actions statique (R4.5-F5-B). */
export function scanPortalWalletBundleDetailReadOnlyImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_WALLET_BUNDLE_DETAIL_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    for (const { rule, pattern } of PORTAL_WALLET_BUNDLE_DETAIL_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule,
          file: relativePath,
          detail: 'Wallet bundle detail must use PortalBundleAllocationReadOnlyPanel only',
        })
      }
    }
  }

  return violations
}

/** invest/bundle — pas de layout Web3 eager (R4.5-F5-A). */
export function scanPortalBundleInvestPageNoEagerWeb3(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []
  const legacyLayout = 'src/app/app/(shell)/invest/bundle/layout.tsx'

  if (fs.existsSync(path.join(root, legacyLayout))) {
    const source = readRelativeFile(root, legacyLayout)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'bundle-invest-layout-removed-f5a',
        file: legacyLayout,
        detail: 'invest/bundle/layout.tsx must not wrap routes — use PortalBundleExecutionController (F5-A)',
      })
    }
  }

  for (const relativePath of PORTAL_BUNDLE_INVEST_PAGE_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'bundle-invest-page-no-eager-web3',
        file: relativePath,
        detail: 'Bundle invest page/screen must not import eager PortalWeb3Boundary',
      })
    }
  }

  return violations
}

/** Lombard borrow setup — pas de hooks open_loan / Privy au mount (R4.5-F6). */
export function scanPortalLombardSetupExecutionImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_LOMBARD_SETUP_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    for (const { rule, pattern } of PORTAL_LOMBARD_SETUP_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule,
          file: relativePath,
          detail:
            'Lombard borrow setup must stay BFF-only; use PortalLombardExecutionController at processing',
        })
      }
    }
  }

  return violations
}

/** borrow/* — pas de layout Web3 eager (R4.5-F6). */
export function scanPortalLombardBorrowPageNoEagerWeb3(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []
  const legacyLayout = 'src/app/app/(shell)/borrow/layout.tsx'

  if (fs.existsSync(path.join(root, legacyLayout))) {
    const source = readRelativeFile(root, legacyLayout)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'lombard-borrow-layout-removed-f6',
        file: legacyLayout,
        detail:
          'borrow/layout.tsx must not wrap routes — use PortalLombardExecutionController at processing (F6)',
      })
    }
  }

  for (const relativePath of PORTAL_LOMBARD_BORROW_PAGE_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'lombard-borrow-page-no-eager-web3',
        file: relativePath,
        detail: 'Borrow routes must not import eager PortalWeb3Boundary',
      })
    }
  }

  return violations
}

/** /app/wallets — redirect profil sans layout Web3 eager (R4.5-F7). */
export function scanPortalWalletsRedirectNoEagerWeb3(webRoot?: string): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []
  const legacyLayout = 'src/app/app/(shell)/wallets/layout.tsx'

  if (fs.existsSync(path.join(root, legacyLayout))) {
    const source = readRelativeFile(root, legacyLayout)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'wallets-redirect-layout-removed-f7',
        file: legacyLayout,
        detail:
          'wallets/layout.tsx must not wrap routes — connect externe via PortalProfileExternalWalletConnect on profile (F7)',
      })
    }
  }

  for (const relativePath of PORTAL_WALLETS_REDIRECT_PAGE_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    if (EAGER_WEB3_BOUNDARY_IMPORT.test(source)) {
      violations.push({
        rule: 'wallets-redirect-page-no-eager-web3',
        file: relativePath,
        detail: 'Wallets redirect page must not import eager PortalWeb3Boundary',
      })
    }
  }

  return violations
}

/** Vault setup — pas de hooks Morpho/Ledgity execution (R4.5-F4). */
export function scanPortalVaultSetupExecutionImports(
  webRoot?: string,
): PortalPerformanceViolation[] {
  const root = resolveWebRoot(webRoot)
  const violations: PortalPerformanceViolation[] = []

  for (const relativePath of PORTAL_VAULT_SETUP_GUARD_PATHS) {
    const source = readRelativeFile(root, relativePath)
    for (const { rule, pattern } of PORTAL_VAULT_SETUP_FORBIDDEN_IMPORTS) {
      if (pattern.test(source)) {
        violations.push({
          rule,
          file: relativePath,
          detail: 'Vault setup must stay API/BFF-only; use PortalVaultExecutionController for review+',
        })
      }
    }
  }

  return violations
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
    ...scanPortalWeb3BoundaryLayoutOffenders(webRoot),
    ...scanWalletReadSegmentNoWeb3Boundary(webRoot),
    ...scanPortalSwapSetupExecutionImports(webRoot),
    ...scanPortalVaultSetupExecutionImports(webRoot),
    ...scanPortalLombardSetupExecutionImports(webRoot),
    ...scanPortalLombardBorrowPageNoEagerWeb3(webRoot),
    ...scanPortalWalletsRedirectNoEagerWeb3(webRoot),
    ...scanPortalBundleInvestSetupExecutionImports(webRoot),
    ...scanPortalBundleInvestPageNoEagerWeb3(webRoot),
    ...scanPortalWalletBundleDetailReadOnlyImports(webRoot),
    ...scanPortalWeb3BoundaryLazySurfaces(webRoot),
    ...scanPortalSessionRouteHelpersImports(webRoot),
    ...scanDeprecatedPortalWalletRouteHelpersImports(webRoot),
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

/** Lombard V1 beta limits & allowlist (env). */

function readBool(name: string, defaultValue = false): boolean {
  const raw = process.env[name]?.trim().toLowerCase()
  if (!raw) return defaultValue
  return raw === '1' || raw === 'true' || raw === 'yes'
}

function readUsdcToRaw(name: string, defaultUsdc: number): bigint {
  const raw = process.env[name]?.trim()
  const usdc = raw ? Number(raw.replace(',', '.')) : defaultUsdc
  if (!Number.isFinite(usdc) || usdc < 0) return BigInt(Math.round(defaultUsdc * 1_000_000))
  return BigInt(Math.round(usdc * 1_000_000))
}

function readCsv(name: string): string[] {
  const raw = process.env[name]?.trim()
  if (!raw) return []
  return raw
    .split(/[,;\n]/)
    .map((value) => value.trim())
    .filter(Boolean)
}

/** When true, enforce beta borrow caps and optional wallet allowlist. */
export function isLombardV1BetaLimitsEnabled(): boolean {
  if (readBool('LOMBARD_V1_BETA_LIMITS_ENABLED', false)) return true
  return readBool('LOMBARD_V1_BETA_ENABLED', false)
}

export type LombardBetaLimits = {
  maxBorrowUsdcPerWalletRaw: bigint
  maxTotalBorrowUsdcGlobalRaw: bigint
  assetDecimals: number
}

export function getLombardBetaLimits(): LombardBetaLimits {
  return {
    maxBorrowUsdcPerWalletRaw: readUsdcToRaw('LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET', 25_000),
    maxTotalBorrowUsdcGlobalRaw: readUsdcToRaw('LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL', 250_000),
    assetDecimals: 6,
  }
}

export function getLombardBetaLimitsForClient() {
  const limits = getLombardBetaLimits()
  return {
    maxBorrowUsdcPerWallet: Number(limits.maxBorrowUsdcPerWalletRaw) / 1_000_000,
    maxTotalBorrowUsdcGlobal: Number(limits.maxTotalBorrowUsdcGlobalRaw) / 1_000_000,
  }
}

export function getLombardAllowedWallets(): Set<string> {
  return new Set(readCsv('LOMBARD_V1_BETA_ALLOWED_WALLETS').map((addr) => addr.toLowerCase()))
}

export function isLombardWalletAllowlistConfigured(): boolean {
  return getLombardAllowedWallets().size > 0
}

export function isLombardWalletAllowlisted(walletAddress: string): boolean {
  const allowlist = getLombardAllowedWallets()
  if (allowlist.size === 0) return true
  return allowlist.has(walletAddress.trim().toLowerCase())
}

/** Reconciliation tolerance — default 2% (200 bps). */
export function getLombardReconciliationToleranceBps(): number {
  const raw = process.env.LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS?.trim()
  const parsed = raw ? Number(raw) : 200
  if (!Number.isFinite(parsed) || parsed < 0) return 200
  return Math.round(parsed)
}

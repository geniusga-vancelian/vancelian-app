/** Configuration feature flags + beta Ledgity vault (env). */

function readBool(name: string, defaultValue = false): boolean {
  const raw = process.env[name]?.trim().toLowerCase()
  if (!raw) return defaultValue
  return raw === '1' || raw === 'true' || raw === 'yes'
}

function readUsdcToRaw(name: string, defaultUsdc: number): bigint {
  const raw = process.env[name]?.trim()
  const usdc = raw ? Number(raw.replace(',', '.')) : defaultUsdc
  if (!Number.isFinite(usdc) || usdc < 0) return BigInt(defaultUsdc) * BigInt(1_000_000)
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

export function isLedgityVaultsEnabled(): boolean {
  return readBool('LEDGITY_VAULTS_ENABLED', false)
}

export function readLedgityLocalSandboxEnabledRaw(): boolean {
  return readBool('LEDGITY_LOCAL_SANDBOX_ENABLED', false)
}

export function assertLedgityLocalSandboxProductionGuard(): void {
  if (process.env.NODE_ENV === 'production' && readLedgityLocalSandboxEnabledRaw()) {
    throw new Error('LEDGITY_LOCAL_SANDBOX_ENABLED cannot be true in production')
  }
}

export function isLedgityDepositsDisabled(): boolean {
  if (process.env.NODE_ENV !== 'production') {
    const devDefaultOpen =
      readLedgityLocalSandboxEnabledRaw() || isLedgityVaultsEnabled()
    if (devDefaultOpen) {
      return readBool('LEDGITY_DEPOSITS_DISABLED', false)
    }
  }
  return readBool('LEDGITY_DEPOSITS_DISABLED', true)
}

export function isLedgityWithdrawsDisabled(): boolean {
  return readBool('LEDGITY_WITHDRAWS_DISABLED', false)
}

export function isLedgityBetaEnabled(): boolean {
  return readBool('LEDGITY_BETA_ENABLED', false)
}

export function isLedgityBetaIncludeAdmins(): boolean {
  return readBool('LEDGITY_BETA_INCLUDE_ADMINS', false)
}

export function isLedgityBetaAllowAllUsers(): boolean {
  return readBool('LEDGITY_BETA_ALLOW_ALL_USERS', false)
}

export function getLedgityBetaPersonIds(): Set<string> {
  return new Set(readCsv('LEDGITY_BETA_PERSON_IDS').map((id) => id.toLowerCase()))
}

export function getLedgityBetaEmails(): Set<string> {
  return new Set(readCsv('LEDGITY_BETA_EMAILS').map((email) => email.toLowerCase()))
}

export function getLedgityBetaProfileTag(): string | null {
  const tag = process.env.LEDGITY_BETA_PROFILE_TAG?.trim()
  return tag || null
}

function readRawLimit(rawNames: string[], usdcName: string, defaultRaw: bigint): bigint {
  for (const name of rawNames) {
    const raw = process.env[name]?.trim()
    if (!raw) continue
    try {
      const value = BigInt(raw)
      return value >= BigInt(0) ? value : defaultRaw
    } catch {
      continue
    }
  }
  return readUsdcToRaw(usdcName, Number(defaultRaw) / 1_000_000)
}

export type LedgityBetaLimits = {
  minDepositRaw: bigint
  maxDepositRaw: bigint
  maxUserExposureRaw: bigint
  maxGlobalExposureRaw: bigint
  assetDecimals: number
}

/** Plafonds live (beta ou non) — LEDGITY_MAX_*_RAW prioritaire. */
export function getLedgityBetaLimits(): LedgityBetaLimits {
  return {
    minDepositRaw: readRawLimit(
      ['LEDGITY_BETA_MIN_DEPOSIT_RAW', 'LEDGITY_MIN_DEPOSIT_RAW'],
      'LEDGITY_BETA_MIN_DEPOSIT_USDC',
      BigInt(1_000_000),
    ),
    maxDepositRaw: readRawLimit(
      ['LEDGITY_BETA_MAX_DEPOSIT_RAW', 'LEDGITY_MAX_DEPOSIT_RAW'],
      'LEDGITY_BETA_MAX_DEPOSIT_USDC',
      BigInt(10_000_000),
    ),
    maxUserExposureRaw: readRawLimit(
      ['LEDGITY_BETA_MAX_USER_EXPOSURE_RAW', 'LEDGITY_MAX_USER_EXPOSURE_RAW'],
      'LEDGITY_BETA_MAX_USER_EXPOSURE_USDC',
      BigInt(50_000_000),
    ),
    maxGlobalExposureRaw: readRawLimit(
      ['LEDGITY_BETA_MAX_GLOBAL_EXPOSURE_RAW', 'LEDGITY_MAX_GLOBAL_EXPOSURE_RAW'],
      'LEDGITY_BETA_MAX_GLOBAL_EXPOSURE_USDC',
      BigInt(500_000_000),
    ),
    assetDecimals: 6,
  }
}

export const getLedgityLiveLimits = getLedgityBetaLimits

export function getLedgityBetaLimitsForClient() {
  const limits = getLedgityBetaLimits()
  return {
    minDepositUsdc: Number(limits.minDepositRaw) / 1_000_000,
    maxDepositUsdc: Number(limits.maxDepositRaw) / 1_000_000,
    maxUserExposureUsdc: Number(limits.maxUserExposureRaw) / 1_000_000,
    maxGlobalExposureUsdc: Number(limits.maxGlobalExposureRaw) / 1_000_000,
  }
}

/** Configuration beta / kill switch Morpho USDC (env). */

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

export function isMorphoUsdcBetaEnabled(): boolean {
  return readBool('MORPHO_USDC_BETA_ENABLED', false)
}

export function isMorphoUsdcDepositsDisabled(): boolean {
  return readBool('MORPHO_USDC_DEPOSITS_DISABLED', false)
}

export function isMorphoUsdcWithdrawsDisabled(): boolean {
  return readBool('MORPHO_USDC_WITHDRAWS_DISABLED', false)
}

export function isMorphoUsdcBetaIncludeAdmins(): boolean {
  return readBool('MORPHO_USDC_BETA_INCLUDE_ADMINS', false)
}

export function isMorphoUsdcBetaAllowAllUsers(): boolean {
  return readBool('MORPHO_USDC_BETA_ALLOW_ALL_USERS', false)
}

export function getMorphoUsdcBetaPersonIds(): Set<string> {
  return new Set(readCsv('MORPHO_USDC_BETA_PERSON_IDS').map((id) => id.toLowerCase()))
}

export function getMorphoUsdcBetaEmails(): Set<string> {
  return new Set(readCsv('MORPHO_USDC_BETA_EMAILS').map((email) => email.toLowerCase()))
}

export function getMorphoUsdcBetaProfileTag(): string | null {
  const tag = process.env.MORPHO_USDC_BETA_PROFILE_TAG?.trim()
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

export type MorphoUsdcBetaLimits = {
  minDepositRaw: bigint
  maxDepositRaw: bigint
  maxUserExposureRaw: bigint
  maxGlobalExposureRaw: bigint
  assetDecimals: number
}

export function getMorphoUsdcBetaLimits(): MorphoUsdcBetaLimits {
  return {
    minDepositRaw: readRawLimit(
      ['MORPHO_USDC_BETA_MIN_DEPOSIT_RAW', 'MORPHO_USDC_MIN_DEPOSIT_RAW'],
      'MORPHO_USDC_BETA_MIN_DEPOSIT_USDC',
      BigInt(10_000_000),
    ),
    maxDepositRaw: readRawLimit(
      ['MORPHO_USDC_BETA_MAX_DEPOSIT_RAW', 'MORPHO_USDC_MAX_DEPOSIT_RAW'],
      'MORPHO_USDC_BETA_MAX_DEPOSIT_USDC',
      BigInt(100_000_000),
    ),
    maxUserExposureRaw: readRawLimit(
      ['MORPHO_USDC_BETA_MAX_USER_EXPOSURE_RAW', 'MORPHO_USDC_MAX_USER_EXPOSURE_RAW'],
      'MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC',
      BigInt(500_000_000),
    ),
    maxGlobalExposureRaw: readRawLimit(
      ['MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_RAW', 'MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW'],
      'MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC',
      BigInt(10_000_000_000),
    ),
    assetDecimals: 6,
  }
}

export function getMorphoUsdcBetaLimitsForClient() {
  const limits = getMorphoUsdcBetaLimits()
  return {
    minDepositUsdc: Number(limits.minDepositRaw) / 1_000_000,
    maxDepositUsdc: Number(limits.maxDepositRaw) / 1_000_000,
    maxUserExposureUsdc: Number(limits.maxUserExposureRaw) / 1_000_000,
    maxGlobalExposureUsdc: Number(limits.maxGlobalExposureRaw) / 1_000_000,
  }
}

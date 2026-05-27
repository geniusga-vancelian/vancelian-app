/** Lombard V1 local mock mode — dev/test only. */

function readBool(name: string, defaultValue = false): boolean {
  const raw = process.env[name]?.trim().toLowerCase()
  if (!raw) return defaultValue
  return raw === '1' || raw === 'true' || raw === 'yes'
}

function readNumber(name: string, defaultValue: number): number {
  const raw = process.env[name]?.trim()
  const parsed = raw ? Number(raw.replace(',', '.')) : defaultValue
  return Number.isFinite(parsed) ? parsed : defaultValue
}

function readUsdcHuman(name: string, defaultUsdc: number): number {
  return readNumber(name, defaultUsdc)
}

export function readLombardMockEnabledRaw(): boolean {
  return readBool('LOMBARD_V1_MOCK_ENABLED', false)
}

export function isLombardMockPositionEnabled(): boolean {
  return readBool('LOMBARD_V1_MOCK_POSITION_ENABLED', false)
}

/** Throws in production if mock flag is set (called from productionSandboxGuard). */
export function assertLombardMockProductionGuard(): void {
  if (process.env.NODE_ENV === 'production' && readLombardMockEnabledRaw()) {
    throw new Error(
      'LOMBARD_V1_MOCK_ENABLED cannot be true in production. Remove the flag before deploy.',
    )
  }
}

/** Mock actif uniquement en local/dev. */
export function isLombardMockEnabled(): boolean {
  if (process.env.NODE_ENV === 'production') return false
  assertLombardMockProductionGuard()
  return readLombardMockEnabledRaw()
}

export type LombardMockConfig = {
  walletBalanceCbBtc: number
  walletBalanceCbEth: number
  borrowApyBps: number
  lltvBps: number
  marketLiquidityUsdc: number
  collateralUsdPrice: Record<'cbBTC' | 'cbETH', number>
}

export function getLombardMockConfig(): LombardMockConfig {
  return {
    walletBalanceCbBtc: readNumber('LOMBARD_V1_MOCK_WALLET_BALANCE_CBBTC', 0.1),
    walletBalanceCbEth: readNumber('LOMBARD_V1_MOCK_WALLET_BALANCE_CBETH', 1.5),
    borrowApyBps: readNumber('LOMBARD_V1_MOCK_BORROW_APY_BPS', 480),
    lltvBps: readNumber('LOMBARD_V1_MOCK_LLTV_BPS', 8600),
    marketLiquidityUsdc: readUsdcHuman('LOMBARD_V1_MOCK_MARKET_LIQUIDITY_USDC', 1_000_000),
    collateralUsdPrice: {
      cbBTC: 80_000,
      cbETH: 3_000,
    },
  }
}

export function getLombardMockBorrowApyPercent(): number {
  return getLombardMockConfig().borrowApyBps / 100
}

export function getLombardMockLltvPercent(): number {
  return getLombardMockConfig().lltvBps / 100
}

export function getLombardMockLiquidityRaw(): bigint {
  const usdc = getLombardMockConfig().marketLiquidityUsdc
  return BigInt(Math.round(usdc * 1_000_000))
}

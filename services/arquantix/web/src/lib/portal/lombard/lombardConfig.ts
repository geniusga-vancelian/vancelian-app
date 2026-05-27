/** Crypto Lombard V1 — emprunt USDC contre cbBTC ou cbETH via Morpho Blue (Base). */
export const VANCELIAN_LOMBARD_V1 = {
  chain: 'base',
  chainId: 8453,
  protocol: 'morpho',
  borrowAsset: 'USDC',
  maxUserLtv: 0.7,
  poweredByLabel: 'Powered by Morpho',
  markets: [
    {
      collateral: 'cbBTC',
      displayName: 'Bitcoin',
      borrowAsset: 'USDC',
      marketId: '0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
    },
    {
      collateral: 'cbETH',
      displayName: 'Ethereum',
      borrowAsset: 'USDC',
      marketId: '0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
    },
  ],
} as const

export type LombardCollateralSymbol = (typeof VANCELIAN_LOMBARD_V1.markets)[number]['collateral']

export const LOMBARD_INTEGRATION_MODE = 'lombard_v1' as const

export const LOMBARD_WAD = BigInt(10) ** BigInt(18)

export function lombardMaxUserLtvWad(): bigint {
  return BigInt(Math.round(VANCELIAN_LOMBARD_V1.maxUserLtv * 1_000_000)) * (LOMBARD_WAD / BigInt(1_000_000))
}

export function findLombardMarketConfig(collateral: string) {
  const normalized = collateral.trim()
  return (
    VANCELIAN_LOMBARD_V1.markets.find((row) => row.collateral === normalized) ??
    VANCELIAN_LOMBARD_V1.markets.find((row) => row.collateral.toLowerCase() === normalized.toLowerCase()) ??
    null
  )
}

export function findLombardMarketById(marketId: string) {
  const key = marketId.trim().toLowerCase()
  return VANCELIAN_LOMBARD_V1.markets.find((row) => row.marketId.toLowerCase() === key) ?? null
}

export function isLombardV1Enabled(): boolean {
  const raw = process.env.LOMBARD_V1_ENABLED?.trim().toLowerCase()
  if (raw === 'false' || raw === '0') return false
  return true
}

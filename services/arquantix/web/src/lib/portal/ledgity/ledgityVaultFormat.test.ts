import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import type { PortalMorphoVaultConfig } from '@prisma/client'

import {
  computeLedgityYieldDisplay,
  formatPricePerShare,
  mapLedgityVaultPosition,
  mergeLedgityVaultConfigWithCatalog,
} from './ledgityVaultFormat'
import type { PortalLedgityCatalogVault } from './ledgityVaultTypes'

const baseConfig = {
  id: 'cfg-ledgity-1',
  vaultAddress: '0x916f179d5d9b7d8ad815ac2f8570aabf0c6a6e38',
  chainId: 8453,
  integrationMode: 'ledgity_vault',
  privyVaultId: null,
  label: 'Ledgity lyUSDC CMS',
  description: 'Description CMS',
  curator: 'Ledgity',
  sortOrder: 0,
  isPublished: true,
  createdAt: new Date('2026-01-01'),
  updatedAt: new Date('2026-01-01'),
} as unknown as PortalMorphoVaultConfig

const catalogVault: PortalLedgityCatalogVault = {
  address: '0x916f179D5D9B7d8Ad815AC2f8570aabF0C6a6e38',
  name: 'Ledgity lyUSDC',
  symbol: 'lyUSDC',
  listed: true,
  asset: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', symbol: 'USDC', decimals: 6 },
  netApy: 0.09,
  pricePerShare: 1.0578,
  tvlUsd: 12_400_000,
  liquidityUsd: 3_100_000,
  curator: 'Ledgity',
  description: 'Vault on-chain',
}

describe('mergeLedgityVaultConfigWithCatalog', () => {
  it('fusionne label CMS, PPS et APY catalog', () => {
    const merged = mergeLedgityVaultConfigWithCatalog(baseConfig, catalogVault)
    assert.equal(merged.name, 'Ledgity lyUSDC CMS')
    assert.equal(merged.userApyBps, 900)
    assert.equal(merged.pricePerShare, 1.0578)
    assert.equal(merged.tvlUsd, 12_400_000)
    assert.equal(merged.availableLiquidityUsd, 3_100_000)
    assert.equal(merged.integrationMode, 'ledgity_vault')
    assert.equal(merged.provider, 'ledgity')
  })

  it('ne confond pas liquidité et TVL sans liquidityUsd explicite', () => {
    const merged = mergeLedgityVaultConfigWithCatalog(baseConfig, {
      ...catalogVault,
      liquidityUsd: null,
    })
    assert.equal(merged.tvlUsd, 12_400_000)
    assert.equal(merged.availableLiquidityUsd, null)
  })
})

describe('computeLedgityYieldDisplay', () => {
  it('calcule le rendement à partir du principal net', () => {
    const display = computeLedgityYieldDisplay({
      currentAssetsRaw: '1050000',
      principalNetRaw: '1000000',
      asset: { symbol: 'USDC', decimals: 6 },
    })
    assert.equal(display, '0.05 USDC')
  })

  it('indique la synchronisation en cours sans principal', () => {
    const display = computeLedgityYieldDisplay({
      currentAssetsRaw: '1050000',
      principalNetRaw: null,
      asset: { symbol: 'USDC', decimals: 6 },
    })
    assert.equal(display, 'Rendement en cours de synchronisation')
  })
})

describe('mapLedgityVaultPosition', () => {
  it('mappe position avec rendement synchronisé', () => {
    const mapped = mapLedgityVaultPosition(
      {
        assets: '1050000',
        shares: '1000000000000000000',
        assetsUsd: 1.05,
        asset: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', symbol: 'USDC', decimals: 6 },
      },
      baseConfig.vaultAddress,
      { principalNetRaw: '1000000', costBasisUnknown: false },
    )
    assert.equal(mapped.yieldSyncStatus, 'synced')
    assert.equal(mapped.earnedYieldDisplay, '0.05 USDC')
    assert.match(mapped.assetsInVaultDisplay, /USDC/)
  })
})

describe('formatPricePerShare', () => {
  it('formate le PPS sur 4 décimales', () => {
    assert.equal(formatPricePerShare(1.0578), '1.0578')
    assert.equal(formatPricePerShare(null), '—')
  })
})

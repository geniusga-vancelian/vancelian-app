import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  mergeMorphoVaultConfigWithGraphql,
  parseHumanAmountToRaw,
  formatApyFromDecimal,
} from './morphoVaultFormat'
import type { PortalMorphoCatalogVault } from './morphoVaultTypes'

const baseConfig = {
  id: 'cfg-1',
  vaultAddress: '0xbeefe94c8ad530842bfe7d8b397938ffc1cb83b2',
  chainId: 8453,
  integrationMode: 'direct_morpho' as const,
  privyVaultId: null,
  label: 'Mon label CMS',
  description: 'Description CMS',
  curator: 'Steakhouse',
  sortOrder: 0,
  isPublished: true,
  createdAt: new Date('2026-01-01'),
  updatedAt: new Date('2026-01-01'),
}

const gqlVault: PortalMorphoCatalogVault = {
  address: '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2',
  name: 'Steakhouse Prime USDC',
  symbol: 'steakUSDC',
  listed: true,
  version: 'v1',
  asset: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', symbol: 'USDC', decimals: 6 },
  netApy: 0.0459,
  tvlUsd: 458_000_000,
  liquidityUsd: 458_000_000,
  curator: 'Steakhouse',
  description: 'Description Morpho',
}

describe('mergeMorphoVaultConfigWithGraphql', () => {
  it('fusionne label CMS et APY GraphQL', () => {
    const merged = mergeMorphoVaultConfigWithGraphql(baseConfig, gqlVault)
    assert.equal(merged.name, 'Mon label CMS')
    assert.equal(merged.userApyBps, 459)
    assert.equal(merged.integrationMode, 'direct_morpho')
    assert.equal(merged.morphoVaultVersion, 'v1')
    assert.equal(merged.id, baseConfig.vaultAddress)
    assert.equal(merged.asset.symbol, 'USDC')
  })

  it('utilise l’adresse vault comme identifiant', () => {
    const merged = mergeMorphoVaultConfigWithGraphql(baseConfig, gqlVault)
    assert.equal(merged.id, baseConfig.vaultAddress.toLowerCase())
  })
})

describe('parseHumanAmountToRaw', () => {
  it('convertit un montant USDC en raw 6 décimales', () => {
    assert.equal(parseHumanAmountToRaw('1.5', 6), BigInt(1500000))
    assert.equal(parseHumanAmountToRaw('10', 6), BigInt(10000000))
  })

  it('rejette un montant invalide', () => {
    assert.throws(() => parseHumanAmountToRaw('abc', 6))
  })
})

describe('formatApyFromDecimal', () => {
  it('formate un APY décimal Morpho', () => {
    assert.equal(formatApyFromDecimal(0.0459), '4.59%')
  })
})

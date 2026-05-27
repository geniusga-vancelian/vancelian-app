import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  getLombardMockConfig,
  isLombardMockEnabled,
  isLombardMockPositionEnabled,
  readLombardMockEnabledRaw,
} from '@/lib/portal/lombard/lombardMockConfig'
import {
  buildLombardMockQuote,
  fetchLombardMockActivePositionsForWallet,
  getLombardMockMarketSummaries,
} from '@/lib/portal/lombard/mocks/lombardLocalMock'
import {
  collectLombardProdEnvChecks,
  validateLombardProductionEnv,
} from '@/lib/portal/lombard/lombardProdEnvValidation'
import { assertProductionSandboxDisabled } from '@/lib/productionSandboxGuard'

const MOCK_ENV_KEYS = [
  'LOMBARD_V1_MOCK_ENABLED',
  'LOMBARD_V1_MOCK_POSITION_ENABLED',
  'LOMBARD_V1_MOCK_WALLET_BALANCE_CBBTC',
  'LOMBARD_V1_MOCK_WALLET_BALANCE_CBETH',
  'LOMBARD_V1_MOCK_BORROW_APY_BPS',
  'LOMBARD_V1_MOCK_LLTV_BPS',
  'LOMBARD_V1_MOCK_MARKET_LIQUIDITY_USDC',
  'LOMBARD_V1_ENABLED',
  'LOMBARD_V1_BETA_ENABLED',
  'LOMBARD_V1_BETA_LIMITS_ENABLED',
  'LOMBARD_V1_BETA_ALLOWED_WALLETS',
  'LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET',
  'LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL',
  'BASE_RPC_URL',
  'PRIVY_APP_ID',
  'PRIVY_APP_SECRET',
  'NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID',
]

function saveEnv(): Record<string, string | undefined> {
  const saved: Record<string, string | undefined> = {}
  for (const key of MOCK_ENV_KEYS) saved[key] = process.env[key]
  saved.NODE_ENV = process.env.NODE_ENV
  return saved
}

function restoreEnv(saved: Record<string, string | undefined>): void {
  for (const key of MOCK_ENV_KEYS) {
    if (saved[key] === undefined) delete process.env[key]
    else process.env[key] = saved[key]
  }
  if (saved.NODE_ENV === undefined) delete process.env.NODE_ENV
  else process.env.NODE_ENV = saved.NODE_ENV
}

describe('lombardMockConfig', () => {
  it('reads default mock balances and APY', () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      process.env.NODE_ENV = 'development'
      const cfg = getLombardMockConfig()
      assert.equal(cfg.walletBalanceCbBtc, 0.1)
      assert.equal(cfg.walletBalanceCbEth, 1.5)
      assert.equal(cfg.borrowApyBps, 480)
      assert.equal(cfg.lltvBps, 8600)
      assert.equal(cfg.marketLiquidityUsdc, 1_000_000)
    } finally {
      restoreEnv(saved)
    }
  })

  it('forbids mock mode in production runtime', () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      process.env.NODE_ENV = 'production'
      assert.equal(isLombardMockEnabled(), false)
    } finally {
      restoreEnv(saved)
    }
  })

  it('production sandbox guard rejects LOMBARD_V1_MOCK_ENABLED', () => {
    const saved = saveEnv()
    try {
      process.env.NODE_ENV = 'production'
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      assert.throws(() => assertProductionSandboxDisabled(), /LOMBARD_V1_MOCK_ENABLED/)
    } finally {
      restoreEnv(saved)
    }
  })
})

describe('lombardLocalMock', () => {
  it('returns two configured mock markets', () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      process.env.NODE_ENV = 'development'
      const markets = getLombardMockMarketSummaries()
      assert.equal(markets.length, 2)
      assert.equal(markets[0]?.borrowApyPercent, 4.8)
      assert.equal(markets[0]?.liquidationLltvPercent, 86)
    } finally {
      restoreEnv(saved)
    }
  })

  it('builds mock quote without Morpho GraphQL', async () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      process.env.NODE_ENV = 'development'
      const wallet = '0x1111111111111111111111111111111111111111'
      const quote35 = await buildLombardMockQuote({
        collateral: 'cbBTC',
        borrowAmount: '100',
        walletAddress: wallet,
        targetLtvPercent: 35,
      })
      const quote70 = await buildLombardMockQuote({
        collateral: 'cbBTC',
        borrowAmount: '100',
        walletAddress: wallet,
        targetLtvPercent: 70,
      })
      assert.equal(quote35.collateral, 'cbBTC')
      assert.equal(quote35.borrowAmount, '100')
      assert.equal(quote35.targetLtvPercent, 35)
      assert.ok(Number(quote35.guaranteeAmountRaw) > 0)
      assert.ok(quote35.projectedLtvPercent <= 35.01)
      assert.ok(Number(quote35.guaranteeAmountRaw) > Number(quote70.guaranteeAmountRaw))
    } finally {
      restoreEnv(saved)
    }
  })

  it('returns empty mock positions when position flag disabled', async () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      process.env.LOMBARD_V1_MOCK_POSITION_ENABLED = 'false'
      process.env.NODE_ENV = 'development'
      const rows = await fetchLombardMockActivePositionsForWallet(
        '0x1111111111111111111111111111111111111111',
      )
      assert.deepEqual(rows, [])
    } finally {
      restoreEnv(saved)
    }
  })
})

describe('lombardProdEnvValidation', () => {
  it('flags missing prod vars when Lombard enabled', () => {
    const saved = saveEnv()
    try {
      for (const key of MOCK_ENV_KEYS) delete process.env[key]
      process.env.LOMBARD_V1_ENABLED = 'true'
      const result = validateLombardProductionEnv({ lombardEnabled: true })
      assert.equal(result.ok, false)
      assert.ok(result.missing.includes('LOMBARD_V1_BETA_ENABLED'))
      assert.equal(result.missing.includes('LOMBARD_V1_BETA_ALLOWED_WALLETS'), false)
    } finally {
      restoreEnv(saved)
    }
  })

  it('passes when Lombard disabled', () => {
    const saved = saveEnv()
    try {
      for (const key of MOCK_ENV_KEYS) delete process.env[key]
      process.env.LOMBARD_V1_MOCK_ENABLED = 'false'
      const checks = collectLombardProdEnvChecks({ lombardEnabled: false })
      assert.ok(checks.every((row) => row.ok || !row.required))
    } finally {
      restoreEnv(saved)
    }
  })

  it('requires mock flag unset in prod checklist', () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      const checks = collectLombardProdEnvChecks({ lombardEnabled: true })
      const mockCheck = checks.find((row) => row.name === 'LOMBARD_V1_MOCK_ENABLED')
      assert.ok(mockCheck)
      assert.equal(mockCheck?.ok, false)
    } finally {
      restoreEnv(saved)
    }
  })
})

describe('lombard mock flags', () => {
  it('position flag defaults false', () => {
    const saved = saveEnv()
    try {
      delete process.env.LOMBARD_V1_MOCK_POSITION_ENABLED
      assert.equal(isLombardMockPositionEnabled(), false)
    } finally {
      restoreEnv(saved)
    }
  })

  it('readLombardMockEnabledRaw reflects env', () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
      assert.equal(readLombardMockEnabledRaw(), true)
    } finally {
      restoreEnv(saved)
    }
  })
})

import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  getLombardAllowedWallets,
  getLombardBetaLimits,
  isLombardV1BetaLimitsEnabled,
  isLombardWalletAllowlisted,
} from '@/lib/portal/lombard/lombardBetaConfig'
import { assertLombardBaseChain } from '@/lib/portal/lombard/lombardBetaLimits'
import { LombardBetaError } from '@/lib/portal/lombard/lombardBetaErrors'
import { buildHighLtvWarning } from '@/lib/portal/lombard/lombardSafetyChecks'
import {
  computeLombardRelativeDeltaBps,
  evaluateLombardReconciliation,
} from '@/lib/portal/lombard/lombardReconciliation'
import { aggregateLombardMonitoringStats } from '@/lib/portal/lombard/lombardMonitoring'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'

const BETA_ENV_KEYS = [
  'LOMBARD_V1_BETA_ENABLED',
  'LOMBARD_V1_BETA_LIMITS_ENABLED',
  'LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET',
  'LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL',
  'LOMBARD_V1_BETA_ALLOWED_WALLETS',
  'LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS',
]

function saveEnv(): Record<string, string | undefined> {
  const saved: Record<string, string | undefined> = {}
  for (const key of BETA_ENV_KEYS) saved[key] = process.env[key]
  return saved
}

function restoreEnv(saved: Record<string, string | undefined>): void {
  for (const key of BETA_ENV_KEYS) {
    if (saved[key] === undefined) delete process.env[key]
    else process.env[key] = saved[key]
  }
}

describe('lombardBetaConfig', () => {
  it('exposes default beta limits', () => {
    const saved = saveEnv()
    try {
      for (const key of BETA_ENV_KEYS) delete process.env[key]
      const limits = getLombardBetaLimits()
      assert.equal(limits.maxBorrowUsdcPerWalletRaw, BigInt(25_000_000_000))
      assert.equal(limits.maxTotalBorrowUsdcGlobalRaw, BigInt(250_000_000_000))
    } finally {
      restoreEnv(saved)
    }
  })

  it('enables beta limits from LOMBARD_V1_BETA_ENABLED', () => {
    const saved = saveEnv()
    try {
      delete process.env.LOMBARD_V1_BETA_LIMITS_ENABLED
      process.env.LOMBARD_V1_BETA_ENABLED = 'true'
      assert.equal(isLombardV1BetaLimitsEnabled(), true)
    } finally {
      restoreEnv(saved)
    }
  })

  it('parses wallet allowlist from env', () => {
    const saved = saveEnv()
    try {
      process.env.LOMBARD_V1_BETA_ALLOWED_WALLETS = '0xAbC,0xdef'
      const allowlist = getLombardAllowedWallets()
      assert.equal(allowlist.has('0xabc'), true)
      assert.equal(allowlist.has('0xdef'), true)
      assert.equal(isLombardWalletAllowlisted('0xABC'), true)
      assert.equal(isLombardWalletAllowlisted('0x999'), false)
    } finally {
      restoreEnv(saved)
    }
  })

  it('allows all wallets when allowlist empty', () => {
    const saved = saveEnv()
    try {
      delete process.env.LOMBARD_V1_BETA_ALLOWED_WALLETS
      assert.equal(isLombardWalletAllowlisted('0xabc'), true)
    } finally {
      restoreEnv(saved)
    }
  })
})

describe('lombardSafetyChecks', () => {
  it('warns above 60% projected LTV', () => {
    const warning = buildHighLtvWarning(65)
    assert.ok(warning)
    assert.equal(warning?.code, 'lombard.high_ltv_warning')
  })

  it('does not warn at 55% projected LTV', () => {
    assert.equal(buildHighLtvWarning(55), null)
  })

  it('does not warn at 48% projected LTV', () => {
    assert.equal(buildHighLtvWarning(48), null)
  })
})

describe('lombardBetaLimits chain guard', () => {
  it('accepts Base chain id', () => {
    assert.doesNotThrow(() => assertLombardBaseChain(8453))
  })

  it('rejects non-Base chain id', () => {
    assert.throws(
      () => assertLombardBaseChain(1),
      (error: unknown) => error instanceof LombardBetaError && error.code === 'lombard.unsupported_chain',
    )
  })
})

describe('lombardReconciliation', () => {
  it('marks confirmed when within tolerance', () => {
    const result = evaluateLombardReconciliation({
      expectedBorrowRaw: BigInt(10_000_000_000),
      expectedCollateralRaw: BigInt(25_000_000),
      actualBorrowRaw: BigInt(10_010_000_000),
      actualCollateralRaw: BigInt(25_010_000),
      toleranceBps: 200,
    })
    assert.equal(result.status, 'confirmed')
    assert.equal(result.delta, null)
  })

  it('marks confirmed_with_delta above tolerance', () => {
    const result = evaluateLombardReconciliation({
      expectedBorrowRaw: BigInt(10_000_000_000),
      expectedCollateralRaw: BigInt(25_000_000),
      actualBorrowRaw: BigInt(9_000_000_000),
      actualCollateralRaw: BigInt(25_000_000),
      toleranceBps: 200,
    })
    assert.equal(result.status, 'confirmed_with_delta')
    assert.ok(result.delta)
  })

  it('computeLombardRelativeDeltaBps', () => {
    assert.equal(computeLombardRelativeDeltaBps(BigInt(1000), BigInt(1090)), 900)
  })
})

describe('lombardMonitoring aggregation', () => {
  const sample: LombardActivePosition = {
    marketId: '0xabc',
    collateralSymbol: 'cbBTC',
    collateralDisplayName: 'Bitcoin',
    collateralAmount: '0.25',
    collateralAmountRaw: '25000000',
    collateralUsdValue: '20000',
    borrowSymbol: 'USDC',
    borrowAmount: '15000',
    borrowAmountRaw: '15000000000',
    currentLtvPercent: 65,
    maxUserLtvPercent: 70,
    morphoLltvPercent: 86,
    healthStatus: 'risky',
    healthLabel: 'High risk',
    healthMessage: 'Consider repaying part of your loan or adding more guarantee.',
    borrowApyPercent: 4.8,
    borrowApyLabel: '4.8% variable',
    liquidationPrice: null,
    protocolLabel: 'Powered by Morpho',
    chainId: 8453,
  }

  it('aggregates totals and LTV bands', () => {
    const snapshot = aggregateLombardMonitoringStats({
      featureEnabled: true,
      betaLimitsEnabled: false,
      allowlistConfigured: false,
      ledger: {
        pendingCount: 1,
        failedCount: 0,
        revertedCount: 0,
        successCount: 3,
        confirmedWithDeltaCount: 1,
      },
      positions: [{ walletAddress: '0x1', position: sample }],
    })

    assert.equal(snapshot.totals.activePositions, 1)
    assert.equal(snapshot.totals.totalBorrowedUsdc, '15000.00')
    assert.equal(snapshot.totals.positionsAbove60Ltv, 1)
    assert.equal(snapshot.totals.positionsAbove70Ltv, 0)
    assert.equal(snapshot.ledger.pendingCount, 1)
    assert.equal(snapshot.ledger.confirmedWithDeltaCount, 1)
  })

  it('counts positions above 70% LTV', () => {
    const risky = { ...sample, currentLtvPercent: 72 }
    const snapshot = aggregateLombardMonitoringStats({
      featureEnabled: true,
      betaLimitsEnabled: true,
      allowlistConfigured: true,
      ledger: {
        pendingCount: 0,
        failedCount: 1,
        revertedCount: 0,
        successCount: 1,
        confirmedWithDeltaCount: 0,
      },
      positions: [{ walletAddress: '0x1', position: risky }],
    })

    assert.equal(snapshot.totals.positionsAbove70Ltv, 1)
    assert.equal(snapshot.betaLimitsEnabled, true)
    assert.ok(snapshot.betaLimits)
  })
})

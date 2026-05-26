import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  applyWalletRowAccess,
  buildWalletRows,
  hasEuroCashAccount,
  isRegistrationComplete,
  resolveCryptoPortfolioTotal,
  resolveDashboardCryptoSummary,
  resolveSavingsPortfolioTotal,
  shouldShowRegistrationResume,
  shouldShowUnlockEuroBanner,
} from './dashboardFormat'
import type { PortalDashboardCash, PortalDashboardProfile } from './dashboardTypes'

const freshCryptoUser: PortalDashboardProfile = {
  client_status: 'pending',
  registration_derived_progress_percent: 0,
  registration_derived_completed_count: 0,
  registration_derived_total_count: 13,
  registration_missing_steps: ['phone'],
  registration_macro_stage: 'pe_client_linked',
}

const registeredUser: PortalDashboardProfile = {
  client_status: 'ACTIVE',
  registration_derived_progress_percent: 100,
  registration_derived_completed_count: 13,
  registration_derived_total_count: 13,
  registration_missing_steps: [],
  registration_macro_stage: 'active_client',
  registration_completion_ratio: 1,
}

describe('shouldShowRegistrationResume', () => {
  it('returns true for fresh Privy signup', () => {
    assert.equal(shouldShowRegistrationResume(freshCryptoUser), true)
    assert.equal(isRegistrationComplete(freshCryptoUser), false)
    assert.equal(shouldShowUnlockEuroBanner(freshCryptoUser), true)
  })

  it('returns false when registration is complete', () => {
    assert.equal(shouldShowRegistrationResume(registeredUser), false)
    assert.equal(isRegistrationComplete(registeredUser), true)
    assert.equal(shouldShowUnlockEuroBanner(registeredUser), false)
  })
})

describe('resolveCryptoPortfolioTotal', () => {
  it('sums position estimated values in reference currency', () => {
    const total = resolveCryptoPortfolioTotal(
      {
        summary: { total_value_eur: 999, positions_count: 2 },
        positions: [
          { estimated_value_eur: 86.24, portfolio_scope: 'privy' },
          { estimated_value_eur: 13.76, portfolio_scope: 'privy' },
        ],
      },
      'EUR',
    )
    assert.equal(total, 100)
  })

  it('falls back to summary when positions are empty', () => {
    const total = resolveCryptoPortfolioTotal(
      { summary: { total_value_eur: 42.5, positions_count: 0 }, positions: [] },
      'EUR',
    )
    assert.equal(total, 42.5)
  })
})

describe('resolveSavingsPortfolioTotal', () => {
  it('sums vault position values in reference currency', () => {
    const total = resolveSavingsPortfolioTotal(
      {
        positions_count: 2,
        positions: [
          { estimatedValueEur: 100, estimatedValueUsd: 110 } as never,
          { estimatedValueEur: 50, estimatedValueUsd: 55 } as never,
        ],
      },
      'EUR',
    )
    assert.equal(total, 150)
  })
})

describe('buildWalletRows', () => {
  it('formats savings balance from vault positions', () => {
    const rows = buildWalletRows(
      null,
      null,
      null,
      {
        positions_count: 1,
        positions: [
          {
            estimatedValueEur: 920,
            estimatedValueUsd: 1000,
          } as never,
        ],
      },
      'EUR',
    )
    const savings = rows.find((r) => r.id === 'savings')
    assert.equal(savings?.numericBalance, 920)
    assert.match(savings?.subtitle ?? '', /1 vault/)
  })

  it('formats crypto balance in reference currency', () => {
    const rows = buildWalletRows(
      null,
      {
        summary: { total_value_usd: 110, positions_count: 1 },
        positions: [{ estimated_value_usd: 110, portfolio_scope: 'privy' }],
      },
      null,
      null,
      'USD',
    )
    const crypto = rows.find((r) => r.id === 'crypto')
    assert.equal(crypto?.numericBalance, 110)
    assert.match(crypto?.balance ?? '', /\$/)
  })
})

describe('resolveDashboardCryptoSummary', () => {
  const privyRaw = {
    balances: [
      {
        asset: 'USDC',
        balance: 12,
        available_balance: 12,
        chain_id: 8453,
        chain_type: 'ethereum',
      },
    ],
  }

  it('uses privy hub valuation for privy-only wallets', () => {
    const cryptoPositionsRaw = {
      summary: { total_value_eur: 99, positions_count: 1 },
      positions: [
        {
          asset: 'USDC',
          estimated_value_eur: 99,
          portfolio_scope: 'privy',
          chain_id: 8453,
        },
      ],
    }

    const summary = resolveDashboardCryptoSummary(cryptoPositionsRaw, privyRaw, null, 'EUR')
    assert.ok(Math.abs((summary?.positions?.[0]?.estimated_value_eur as number) - 11.04) < 0.01)
  })

  it('keeps merged platform+privy totals from crypto-positions', () => {
    const cryptoPositionsRaw = {
      summary: { total_value_eur: 150, positions_count: 1 },
      positions: [
        {
          asset: 'USDC',
          estimated_value_eur: 150,
          portfolio_scope: 'merged',
          chain_id: 8453,
        },
      ],
    }

    const summary = resolveDashboardCryptoSummary(cryptoPositionsRaw, privyRaw, null, 'EUR')
    assert.equal(summary?.positions?.[0]?.estimated_value_eur, 150)
  })
})

describe('applyWalletRowAccess', () => {
  const baseRows = buildWalletRows(null, { summary: { total_value_eur: 120, positions_count: 1 } }, null, null, 'EUR')

  it('keeps crypto and other rows visible for fresh signup', () => {
    const rows = applyWalletRowAccess(baseRows, freshCryptoUser, null)
    assert.equal(rows.find((r) => r.id === 'crypto')?.locked, undefined)
    assert.equal(rows.find((r) => r.id === 'savings')?.locked, undefined)
    assert.equal(rows.find((r) => r.id === 'offers')?.locked, undefined)
    assert.equal(rows.find((r) => r.id === 'portfolio')?.locked, undefined)
  })

  it('locks euro row with CTA before registration completes', () => {
    const rows = applyWalletRowAccess(baseRows, freshCryptoUser, null)
    const euro = rows.find((r) => r.id === 'euro')
    assert.equal(euro?.locked, true)
    assert.equal(euro?.ctaLabel, 'Complete registration')
    assert.equal(euro?.balance, '—')
  })

  it('unlocks euro row after registration completes', () => {
    const rows = applyWalletRowAccess(baseRows, registeredUser, null)
    const euro = rows.find((r) => r.id === 'euro')
    assert.equal(euro?.locked, false)
    assert.match(euro?.balance ?? '', /0,00/)
  })

  it('unlocks euro row when custody account already exists', () => {
    const cash: PortalDashboardCash = {
      cash_account: {
        available_balance: 50,
        currency: 'EUR',
      },
    }
    assert.equal(hasEuroCashAccount(cash), true)
    const rowsWithCash = buildWalletRows(
      cash,
      { summary: { total_value_eur: 120, positions_count: 1 } },
      null,
      null,
      'EUR',
    )
    const rows = applyWalletRowAccess(rowsWithCash, freshCryptoUser, cash)
    const euro = rows.find((r) => r.id === 'euro')
    assert.equal(euro?.locked, false)
    assert.match(euro?.balance ?? '', /50/)
  })
})

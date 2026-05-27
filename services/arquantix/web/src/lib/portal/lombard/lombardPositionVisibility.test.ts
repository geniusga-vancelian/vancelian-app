import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import {
  resolveLombardAssetDetailLoanPosition,
  shouldShowLombardActiveLoanCard,
  shouldShowLombardAssetDetailLoanCard,
  shouldShowLombardEmptyState,
  shouldShowLombardWalletDashboardCard,
} from '@/lib/portal/lombard/lombardPositionVisibility'

const samplePosition: LombardActivePosition = {
  marketId: '0xabc',
  collateralSymbol: 'cbBTC',
  collateralDisplayName: 'Bitcoin',
  collateralAmount: '0.25',
  collateralAmountRaw: '25000000',
  collateralUsdValue: '20000',
  borrowSymbol: 'USDC',
  borrowAmount: '15000',
  borrowAmountRaw: '15000000000',
  currentLtvPercent: 48,
  maxUserLtvPercent: 70,
  morphoLltvPercent: 86,
  healthStatus: 'comfortable',
  healthLabel: 'Comfortable',
  healthMessage: 'Your position has a strong safety margin.',
  borrowApyPercent: 4.8,
  borrowApyLabel: '4.8% variable',
  liquidationPrice: null,
  protocolLabel: 'Powered by Morpho',
  chainId: 8453,
}

describe('lombardPositionVisibility', () => {
  it('wallet dashboard card gating', () => {
    assert.equal(
      shouldShowLombardWalletDashboardCard({ lombardEnabled: true, chain: 'base', loading: false }),
      true,
    )
    assert.equal(
      shouldShowLombardWalletDashboardCard({ lombardEnabled: false, chain: 'base', loading: false }),
      false,
    )
    assert.equal(
      shouldShowLombardWalletDashboardCard({ lombardEnabled: true, chain: 'ethereum', loading: false }),
      false,
    )
  })

  it('active loan card visibility', () => {
    assert.equal(shouldShowLombardActiveLoanCard([samplePosition]), true)
    assert.equal(shouldShowLombardActiveLoanCard([]), false)
  })

  it('empty state when eligible guarantee exists', () => {
    assert.equal(
      shouldShowLombardEmptyState({
        positions: [],
        walletPositions: [{ asset: 'CBBTC', name: 'Bitcoin', balance: 0.4, availableBalance: 0.4, iconKey: 'btc' }],
      }),
      true,
    )
    assert.equal(
      shouldShowLombardEmptyState({
        positions: [samplePosition],
        walletPositions: [{ asset: 'CBBTC', name: 'Bitcoin', balance: 0.4, availableBalance: 0.4, iconKey: 'btc' }],
      }),
      false,
    )
  })

  it('asset detail card visibility', () => {
    assert.equal(
      shouldShowLombardAssetDetailLoanCard({
        asset: 'CBBTC',
        lombardEnabled: true,
        chain: 'base',
        position: samplePosition,
      }),
      true,
    )
    assert.equal(
      shouldShowLombardAssetDetailLoanCard({
        asset: 'USDC',
        lombardEnabled: true,
        chain: 'base',
        position: samplePosition,
      }),
      false,
    )
  })

  it('resolve asset detail position by ticker alias', () => {
    const row = resolveLombardAssetDetailLoanPosition([samplePosition], 'CBBTC')
    assert.equal(row?.collateralSymbol, 'cbBTC')
  })
})

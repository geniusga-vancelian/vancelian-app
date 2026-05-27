import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { PortalCryptoPosition, PortalCryptoPositionsSummary } from '@/lib/portal/cryptoWalletTypes'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import {
  applyLombardWalletBalanceOverlay,
  formatLombardPositionSubtitle,
} from '@/lib/portal/lombard/lombardWalletBalanceOverlay'

const cbBtcPosition: PortalCryptoPosition = {
  asset: 'CBBTC',
  name: 'Bitcoin',
  balance: 5.3,
  availableBalance: 5.3,
  priceUsd: 80_000,
  estimatedValueUsd: 5.3 * 80_000,
  iconKey: 'cbbtc',
  portfolioScope: 'privy',
  privyBalance: 5.3,
  platformBalance: 0,
}

const summary: PortalCryptoPositionsSummary = {
  totalValueEur: 0,
  totalValueUsd: 5.3 * 80_000,
  positionsCount: 1,
  positions: [cbBtcPosition],
}

const lombardLoan: LombardActivePosition = {
  marketId: '0xmarket',
  collateralSymbol: 'cbBTC',
  collateralDisplayName: 'Bitcoin',
  collateralAmount: '0.017857',
  collateralAmountRaw: '1785700',
  collateralUsdValue: '1428.56',
  borrowSymbol: 'USDC',
  borrowAmount: '1000',
  borrowAmountRaw: '1000000000',
  currentLtvPercent: 70,
  maxUserLtvPercent: 70,
  morphoLltvPercent: 86,
  healthStatus: 'high_risk',
  healthLabel: 'High risk',
  healthMessage: 'High risk',
  borrowApyPercent: 4.8,
  borrowApyLabel: '4.8% variable',
  liquidationPrice: null,
  protocolLabel: 'Powered by Morpho',
  chainId: 8453,
}

describe('lombardWalletBalanceOverlay', () => {
  it('mock mode splits cbBTC into available and locked without losing total exposure', () => {
    const next = applyLombardWalletBalanceOverlay({
      summary,
      lombardPositions: [lombardLoan],
      simulatePrivyBalances: true,
    })

    const cbBtc = next.positions.find((row) => row.asset === 'CBBTC')
    assert.ok(cbBtc)
    assert.equal(cbBtc.balance, 5.3)
    assert.ok(Math.abs(cbBtc.availableBalance - (5.3 - 0.017857)) < 0.000001)
    assert.equal(cbBtc.lombard?.lockedCollateralAmount, 0.017857)

    const usdc = next.positions.find((row) => row.asset === 'USDC')
    assert.ok(usdc)
    assert.equal(usdc.balance, 1000)
    assert.equal(usdc.chainId, 8453)
    assert.equal(usdc.lombard?.borrowedUsdcAmount, 1000)
  })

  it('live mode keeps wallet free balance and adds locked metadata', () => {
    const liveSummary: PortalCryptoPositionsSummary = {
      ...summary,
      positions: [
        {
          ...cbBtcPosition,
          balance: 5.282143,
          availableBalance: 5.282143,
          privyBalance: 5.282143,
          estimatedValueUsd: 5.282143 * 80_000,
        },
      ],
    }

    const next = applyLombardWalletBalanceOverlay({
      summary: liveSummary,
      lombardPositions: [lombardLoan],
      simulatePrivyBalances: false,
    })

    const cbBtc = next.positions.find((row) => row.asset === 'CBBTC')
    assert.ok(cbBtc)
    assert.equal(cbBtc.availableBalance, 5.282143)
    assert.ok(Math.abs(cbBtc.balance - 5.3) < 0.000001)
  })

  it('formats position subtitles for locked collateral and borrowed USDC', () => {
    const lockedPosition: PortalCryptoPosition = {
      ...cbBtcPosition,
      availableBalance: 5.282143,
      lombard: {
        lockedCollateralAmount: 0.017857,
        lockedCollateralSymbol: 'cbBTC',
        borrowedUsdcAmount: 1000,
        simulatePrivyCredit: true,
      },
    }
    assert.match(formatLombardPositionSubtitle(lockedPosition) ?? '', /available · .* locked/)

    const usdcPosition: PortalCryptoPosition = {
      asset: 'USDC',
      name: 'USD Coin',
      balance: 1000,
      availableBalance: 1000,
      iconKey: 'usdc',
      lombard: {
        lockedCollateralAmount: 0,
        lockedCollateralSymbol: 'USDC',
        borrowedUsdcAmount: 1000,
        simulatePrivyCredit: true,
      },
    }
    assert.match(formatLombardPositionSubtitle(usdcPosition) ?? '', /1000 USDC Lombard/)
  })
})

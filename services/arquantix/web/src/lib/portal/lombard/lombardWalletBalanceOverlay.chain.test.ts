import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { filterCryptoPositionsByPortalChain } from '@/lib/portal/portalChainFilter'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { applyLombardWalletBalanceOverlay } from '@/lib/portal/lombard/lombardWalletBalanceOverlay'

const lombardLoan: LombardActivePosition = {
  marketId: '0xmarket',
  collateralSymbol: 'cbBTC',
  collateralDisplayName: 'Bitcoin',
  collateralAmount: '0.017857',
  collateralAmountRaw: '1785700',
  collateralUsdValue: null,
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

describe('lombardWalletBalanceOverlay chain filter', () => {
  it('synthetic USDC survives Base navbar filter', () => {
    const next = applyLombardWalletBalanceOverlay({
      summary: {
        totalValueEur: 0,
        positions: [
          {
            asset: 'CBBTC',
            name: 'Bitcoin',
            balance: 5.3,
            availableBalance: 5.3,
            iconKey: 'cbbtc',
            chainType: 'evm',
            chainId: 8453,
          },
        ],
        positionsCount: 1,
      },
      lombardPositions: [lombardLoan],
      simulatePrivyBalances: true,
    })

    const filtered = filterCryptoPositionsByPortalChain(next.positions, 'base')
    const usdc = filtered.find((row) => row.asset === 'USDC')
    assert.ok(usdc, 'USDC row should remain visible on Base')
  })

  it('adds Base USDC row when Privy USDC is tagged Ethereum mainnet', () => {
    const next = applyLombardWalletBalanceOverlay({
      summary: {
        totalValueEur: 0,
        positions: [
          {
            asset: 'CBBTC',
            name: 'Bitcoin',
            balance: 5.3,
            availableBalance: 5.3,
            iconKey: 'cbbtc',
            chainType: 'evm',
            chainId: 8453,
          },
          {
            asset: 'USDC',
            name: 'USD Coin',
            balance: 0,
            availableBalance: 0,
            iconKey: 'usdc',
            chainType: 'evm',
            chainId: 1,
            privyBalance: 0,
          },
        ],
        positionsCount: 2,
      },
      lombardPositions: [lombardLoan],
      simulatePrivyBalances: true,
    })

    const onBase = filterCryptoPositionsByPortalChain(next.positions, 'base')
    const onEthereum = filterCryptoPositionsByPortalChain(next.positions, 'ethereum')
    const baseUsdc = onBase.filter((row) => row.asset === 'USDC')
    assert.equal(baseUsdc.length, 1)
    assert.equal(baseUsdc[0]?.chainId, 8453)
    assert.equal(baseUsdc[0]?.balance, 1000)
    assert.equal(onEthereum.filter((row) => row.asset === 'USDC').length, 1)
  })
})

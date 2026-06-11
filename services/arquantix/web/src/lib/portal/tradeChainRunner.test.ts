import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { PortfolioRebalancingPayload } from '@/lib/portal/bundleClient'
import {
  rebalanceLegFromAsset,
  rebalanceLegSnapshot,
  runSequentialTrades,
} from '@/lib/portal/tradeChainRunner'

function buyLegFixture(
  asset: string,
  status: string,
  swapId: string | null,
  qty: number,
) {
  return {
    asset,
    status,
    swap_id: swapId,
    amount_usdc: '30',
    amount_in: '30',
    estimated_receive: String(qty),
    from_asset: 'USDC',
    entry_asset_spent: 30,
    quantity_bought: qty,
  }
}

const basePayload = (overrides?: Partial<PortfolioRebalancingPayload>): PortfolioRebalancingPayload => ({
  portfolio_id: 'portfolio-1',
  status: 'running',
  v3_status: 'RUNNING',
  rebalance_execution_id: 'exec-1',
  sell_results: [],
  buy_results: [
    buyLegFixture('cbBTC', 'pending', 'swap-btc', 0.0004),
    {
      asset: 'cbETH',
      status: 'planned',
      swap_id: null,
      amount_usdc: '30',
    },
  ],
  asset_lines: [],
  ...overrides,
})

describe('rebalanceLegSnapshot', () => {
  it('vente : amount_in crypto, pas amount_usdc', () => {
    const snap = rebalanceLegSnapshot({
      asset: 'AAVE',
      side: 'sell',
      status: 'pending',
      swap_id: 'swap-aave',
      amount_usdc: '4.33',
      amount_in: '0.068',
      estimated_receive: '4.31',
      from_asset: 'AAVE',
      to_asset: 'USDC',
      quantity_sold: 0.068,
      entry_asset_received: 4.31,
    })
    assert.equal(snap.review_amount_in, '0.068')
    assert.equal(snap.review_estimated_receive, '4.31')
  })

  it('achat : amount_in USDC', () => {
    const snap = rebalanceLegSnapshot({
      asset: 'ETH',
      side: 'buy',
      status: 'pending',
      swap_id: 'swap-eth',
      amount_usdc: '30',
      amount_in: '30',
      estimated_receive: '0.01',
      from_asset: 'USDC',
      to_asset: 'ETH',
      entry_asset_spent: 30,
      quantity_bought: 0.01,
    })
    assert.equal(snap.review_amount_in, '30')
    assert.equal(snap.review_estimated_receive, '0.01')
  })
})

describe('rebalanceLegFromAsset', () => {
  it('vente utilise l’actif vendu', () => {
    assert.equal(
      rebalanceLegFromAsset({ asset: 'AAVE', side: 'sell', status: 'pending', from_asset: 'AAVE' }),
      'AAVE',
    )
  })

  it('achat utilise l’entry asset', () => {
    assert.equal(
      rebalanceLegFromAsset({ asset: 'ETH', side: 'buy', status: 'pending' }, 'USDC'),
      'USDC',
    )
  })
})

describe('runSequentialTrades', () => {
  it('continue après un leg en échec et reprend via resume', async () => {
    const executed: string[] = []
    let resumeCalls = 0

    const result = await runSequentialTrades({
      initial: basePayload(),
      tradeDeps: {
        signAndSubmit: async () => '0xabc',
        pollUntilTerminal: async () => ({ status: 'CONFIRMED', tx_hash: '0xabc' }),
      },
      executeLeg: async (swapId) => {
        executed.push(swapId)
        if (swapId === 'swap-btc') {
          throw new Error('signal timed out')
        }
      },
      resumeFn: async () => {
        resumeCalls += 1
        return basePayload({
          buy_results: [
            buyLegFixture('cbBTC', 'expired', 'swap-btc', 0.0004),
            buyLegFixture('cbETH', 'pending', 'swap-eth', 0.01),
          ],
          v3_status: resumeCalls >= 2 ? 'COMPLETED_WITH_RESIDUAL_CASH' : 'RUNNING',
        })
      },
    })

    assert.deepEqual(executed, ['swap-btc', 'swap-eth'])
    assert.ok(resumeCalls >= 1)
    assert.equal(result.legOutcomes.length, 2)
    assert.equal(result.legOutcomes[0]?.status, 'failed')
    assert.equal(result.legOutcomes[1]?.status, 'completed')
    assert.equal(result.payload.v3_status, 'COMPLETED_WITH_RESIDUAL_CASH')
  })

  it('retry resume une fois avant de sortir proprement', async () => {
    let resumeCalls = 0
    const result = await runSequentialTrades({
      initial: basePayload({
        buy_results: [
          {
            asset: 'cbBTC',
            status: 'completed',
            swap_id: 'swap-btc',
            amount_usdc: '30',
          },
        ],
        v3_status: 'RUNNING',
      }),
      tradeDeps: {
        signAndSubmit: async () => '0xabc',
        pollUntilTerminal: async () => ({ status: 'CONFIRMED', tx_hash: '0xabc' }),
      },
      resumeFn: async () => {
        resumeCalls += 1
        if (resumeCalls < 2) {
          throw new Error('Internal Server Error')
        }
        if (resumeCalls === 2) {
          return basePayload({
            buy_results: [
              buyLegFixture('cbBTC', 'completed', 'swap-btc', 0.0004),
              buyLegFixture('cbETH', 'pending', 'swap-eth', 0.01),
            ],
          })
        }
        return basePayload({
          v3_status: 'COMPLETED',
          buy_results: [
            buyLegFixture('cbBTC', 'completed', 'swap-btc', 0.0004),
            buyLegFixture('cbETH', 'completed', 'swap-eth', 0.01),
          ],
        })
      },
      executeLeg: async (swapId) => {
        if (swapId === 'swap-eth') return
        throw new Error('unexpected')
      },
    })

    assert.ok(resumeCalls >= 2)
    assert.equal(result.resumeOutcomes[0]?.status, 'ok')
    assert.equal(result.lastResumeError, null)
    assert.equal(result.legOutcomes.some((o) => o.swapId === 'swap-eth'), true)
  })

  it('ne throw pas quand resume échoue après retry — lastResumeError renseigné', async () => {
    const result = await runSequentialTrades({
      initial: basePayload({
        buy_results: [
          {
            asset: 'cbBTC',
            status: 'completed',
            swap_id: 'swap-btc',
            amount_usdc: '30',
          },
        ],
        v3_status: 'RUNNING',
      }),
      tradeDeps: {
        signAndSubmit: async () => '0xabc',
        pollUntilTerminal: async () => ({ status: 'CONFIRMED', tx_hash: '0xabc' }),
      },
      resumeFn: async () => {
        throw new Error('Internal Server Error')
      },
    })

    assert.match(result.lastResumeError ?? '', /Service temporairement indisponible/)
    assert.equal(result.resumeOutcomes[0]?.status, 'failed')
    assert.equal(result.resumeOutcomes[0]?.attempts, 2)
  })

  it('un swap unitaire par tour — resume quote le leg suivant', async () => {
    const executed: string[] = []
    let resumeCalls = 0

    const result = await runSequentialTrades({
      initial: basePayload({
        buy_results: [
          buyLegFixture('cbBTC', 'pending', 'swap-btc', 0.0004),
          buyLegFixture('cbETH', 'pending', 'swap-eth', 0.01),
        ],
      }),
      tradeDeps: {
        signAndSubmit: async () => '0xabc',
        pollUntilTerminal: async () => ({ status: 'CONFIRMED', tx_hash: '0xabc' }),
      },
      executeLeg: async (swapId) => {
        executed.push(swapId)
      },
      resumeFn: async () => {
        resumeCalls += 1
        if (resumeCalls === 1) {
          return basePayload({
            buy_results: [
              buyLegFixture('cbBTC', 'completed', 'swap-btc', 0.0004),
              buyLegFixture('cbETH', 'pending', 'swap-eth', 0.01),
            ],
          })
        }
        return basePayload({
          v3_status: 'COMPLETED',
          buy_results: [
            buyLegFixture('cbBTC', 'completed', 'swap-btc', 0.0004),
            buyLegFixture('cbETH', 'completed', 'swap-eth', 0.01),
          ],
        })
      },
    })

    assert.deepEqual(executed, ['swap-btc', 'swap-eth'])
    assert.ok(resumeCalls >= 2)
    assert.equal(result.legOutcomes.length, 2)
  })

  it('ne bloque pas quand tous les legs du batch échouent', async () => {
    const result = await runSequentialTrades({
      initial: basePayload({
        buy_results: [buyLegFixture('cbBTC', 'pending', 'swap-btc', 0.0004)],
        v3_status: 'RUNNING',
      }),
      tradeDeps: {
        signAndSubmit: async () => '0xabc',
        pollUntilTerminal: async () => ({ status: 'CONFIRMED', tx_hash: '0xabc' }),
      },
      executeLeg: async () => {
        throw new Error('confirm failed')
      },
      resumeFn: async () =>
        basePayload({
          v3_status: 'COMPLETED_WITH_RESIDUAL_CASH',
          buy_results: [buyLegFixture('cbBTC', 'expired', 'swap-btc', 0.0004)],
        }),
    })

    assert.equal(result.legOutcomes[0]?.status, 'failed')
    assert.equal(result.payload.v3_status, 'COMPLETED_WITH_RESIDUAL_CASH')
  })

  it('passe fromAsset par leg à executeLeg', async () => {
    const fromAssets: string[] = []
    await runSequentialTrades({
      initial: basePayload({
        sell_results: [
          {
            asset: 'AAVE',
            status: 'pending',
            swap_id: 'swap-aave',
            amount_usdc: '4.33',
            amount_in: '0.068',
            estimated_receive: '4.31',
            from_asset: 'AAVE',
            quantity_sold: 0.068,
            entry_asset_received: 4.31,
          },
        ],
        buy_results: [],
      }),
      entryAsset: 'USDC',
      tradeDeps: {
        signAndSubmit: async () => '0xabc',
        pollUntilTerminal: async () => ({ status: 'CONFIRMED', tx_hash: '0xabc' }),
      },
      executeLeg: async (_swapId, _snap, deps) => {
        fromAssets.push(deps.fromAsset ?? '')
      },
      resumeFn: async () =>
        basePayload({
          v3_status: 'COMPLETED',
          sell_results: [
            {
              asset: 'AAVE',
              status: 'completed',
              swap_id: 'swap-aave',
              amount_usdc: '4.33',
            },
          ],
        }),
    })
    assert.deepEqual(fromAssets, ['AAVE'])
  })
})

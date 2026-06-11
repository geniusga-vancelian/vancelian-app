import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { PortfolioRebalancingPayload } from '@/lib/portal/bundleClient'
import { runSequentialTrades } from '@/lib/portal/tradeChainRunner'

const basePayload = (overrides?: Partial<PortfolioRebalancingPayload>): PortfolioRebalancingPayload => ({
  portfolio_id: 'portfolio-1',
  status: 'running',
  v3_status: 'RUNNING',
  rebalance_execution_id: 'exec-1',
  sell_results: [],
  buy_results: [
    {
      asset: 'cbBTC',
      status: 'pending',
      swap_id: 'swap-btc',
      amount_usdc: '30',
      quantity_bought: 0.0004,
    },
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
            {
              asset: 'cbBTC',
              status: 'expired',
              swap_id: 'swap-btc',
              amount_usdc: '30',
            },
            {
              asset: 'cbETH',
              status: 'pending',
              swap_id: 'swap-eth',
              amount_usdc: '30',
              quantity_bought: 0.01,
            },
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
              {
                asset: 'cbBTC',
                status: 'completed',
                swap_id: 'swap-btc',
                amount_usdc: '30',
              },
              {
                asset: 'cbETH',
                status: 'pending',
                swap_id: 'swap-eth',
                amount_usdc: '30',
                quantity_bought: 0.01,
              },
            ],
          })
        }
        return basePayload({
          v3_status: 'COMPLETED',
          buy_results: [
            {
              asset: 'cbBTC',
              status: 'completed',
              swap_id: 'swap-btc',
              amount_usdc: '30',
            },
            {
              asset: 'cbETH',
              status: 'completed',
              swap_id: 'swap-eth',
              amount_usdc: '30',
            },
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
          {
            asset: 'cbBTC',
            status: 'pending',
            swap_id: 'swap-btc',
            amount_usdc: '30',
            quantity_bought: 0.0004,
          },
          {
            asset: 'cbETH',
            status: 'pending',
            swap_id: 'swap-eth',
            amount_usdc: '30',
            quantity_bought: 0.01,
          },
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
              {
                asset: 'cbBTC',
                status: 'completed',
                swap_id: 'swap-btc',
                amount_usdc: '30',
              },
              {
                asset: 'cbETH',
                status: 'pending',
                swap_id: 'swap-eth',
                amount_usdc: '30',
                quantity_bought: 0.01,
              },
            ],
          })
        }
        return basePayload({
          v3_status: 'COMPLETED',
          buy_results: [
            {
              asset: 'cbBTC',
              status: 'completed',
              swap_id: 'swap-btc',
              amount_usdc: '30',
            },
            {
              asset: 'cbETH',
              status: 'completed',
              swap_id: 'swap-eth',
              amount_usdc: '30',
            },
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
        buy_results: [
          {
            asset: 'cbBTC',
            status: 'pending',
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
      executeLeg: async () => {
        throw new Error('confirm failed')
      },
      resumeFn: async () =>
        basePayload({
          v3_status: 'COMPLETED_WITH_RESIDUAL_CASH',
          buy_results: [
            {
              asset: 'cbBTC',
              status: 'expired',
              swap_id: 'swap-btc',
              amount_usdc: '30',
            },
          ],
        }),
    })

    assert.equal(result.legOutcomes[0]?.status, 'failed')
    assert.equal(result.payload.v3_status, 'COMPLETED_WITH_RESIDUAL_CASH')
  })
})

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  consolidateSwapTransactions,
  groupCryptoTransactionsByDay,
  isCryptoSwapTransaction,
  mapCryptoTransactionToHistoryItem,
  parseSwapAssetsFromTitle,
} from './cryptoTransactionHistoryFormat'
import type { PortalCryptoWalletTransaction } from './cryptoWalletTypes'

const baseTx: PortalCryptoWalletTransaction = {
  id: '1',
  side: 'deposit',
  asset: 'USDC',
  amountCrypto: '100',
  amountFiat: '0',
  price: '0',
  currency: 'EUR',
  status: 'confirmed',
  createdAt: '2026-05-22T10:00:00.000Z',
  title: 'Dépôt USDC',
  subtitle: 'Wallet Privy',
  direction: 'credit',
  transactionKind: 'privy_deposit_in',
}

describe('parseSwapAssetsFromTitle', () => {
  it('parses Échange USDC → CBBTC', () => {
    assert.deepEqual(parseSwapAssetsFromTitle('Échange USDC → CBBTC'), {
      fromAsset: 'USDC',
      toAsset: 'CBBTC',
    })
  })
})

describe('isCryptoSwapTransaction', () => {
  it('detects LI.FI swap rows', () => {
    assert.equal(
      isCryptoSwapTransaction({
        ...baseTx,
        side: 'swap',
        transactionKind: 'crypto_swap',
        fromAsset: 'USDC',
        toAsset: 'ETH',
      }),
      true,
    )
  })

  it('detects privy swap title without from/to fields', () => {
    assert.equal(
      isCryptoSwapTransaction({
        ...baseTx,
        transactionKind: 'crypto_swap',
        title: 'Échange USDC → CBBTC',
      }),
      true,
    )
  })

  it('ignores fiat buy orders', () => {
    assert.equal(
      isCryptoSwapTransaction({
        ...baseTx,
        side: 'buy',
        fromAsset: 'EUR',
        toAsset: 'BTC',
      }),
      false,
    )
  })
})

describe('consolidateSwapTransactions', () => {
  it('merges privy debit/credit legs sharing tx hash', () => {
    const merged = consolidateSwapTransactions([
      {
        ...baseTx,
        id: 'credit',
        asset: 'CBBTC',
        amountCrypto: '0.15',
        direction: 'credit',
        transactionKind: 'crypto_swap',
        title: 'Échange USDC → CBBTC',
        txHash: '0xabc',
      },
      {
        ...baseTx,
        id: 'debit',
        asset: 'USDC',
        amountCrypto: '250',
        direction: 'debit',
        transactionKind: 'crypto_swap',
        title: 'Échange USDC → CBBTC',
        txHash: '0xabc',
      },
    ])

    assert.equal(merged.length, 1)
    assert.equal(merged[0]?.swapAmountFrom, '250')
    assert.equal(merged[0]?.swapAmountTo, '0.15')
    assert.equal(merged[0]?.fromAsset, 'USDC')
    assert.equal(merged[0]?.toAsset, 'CBBTC')
  })
})

describe('groupCryptoTransactionsByDay', () => {
  it('groups transactions by day and filters by month', () => {
    const sections = groupCryptoTransactionsByDay(
      [
        {
          ...baseTx,
          id: '1',
          createdAt: '2026-05-24T10:00:00.000Z',
          title: 'Dépôt USDC',
        },
        {
          ...baseTx,
          id: '2',
          createdAt: '2026-05-22T10:00:00.000Z',
          title: 'Retrait USDC',
          direction: 'debit',
        },
        {
          ...baseTx,
          id: '3',
          createdAt: '2026-04-10T10:00:00.000Z',
          title: 'Dépôt USDC',
        },
      ],
      'EUR',
      '2026-05',
    )

    assert.equal(sections.length, 2)
    assert.equal(sections[0]?.items.length, 1)
    assert.equal(sections[1]?.items.length, 1)
  })
})

describe('mapCryptoTransactionToHistoryItem', () => {
  it('maps deposit to flow row with arrow-down avatar direction', () => {
    const row = mapCryptoTransactionToHistoryItem(baseTx, 'EUR')
    assert.equal(row.variant, 'flow')
    assert.equal(row.flowDirection, 'in')
    assert.match(row.amount, /^\+/)
  })

  it('maps crypto swap to exchange row with date left and source amount right', () => {
    const row = mapCryptoTransactionToHistoryItem(
      {
        ...baseTx,
        side: 'swap',
        asset: 'CBBTC',
        transactionKind: 'crypto_swap',
        fromAsset: 'USDC',
        toAsset: 'CBBTC',
        swapAmountFrom: '250',
        swapAmountTo: '0.15',
        title: 'Échange USDC → CBBTC',
      },
      'EUR',
    )
    assert.equal(row.variant, 'swap')
    assert.equal(row.title, 'Échange · USDC → CBBTC')
    assert.equal(row.fromAsset, 'USDC')
    assert.equal(row.toAsset, 'CBBTC')
    assert.match(row.subtitle ?? '', /22 mai/)
    assert.match(row.meta ?? '', /^−/)
    assert.match(row.meta ?? '', /USDC/)
    assert.match(row.amount, /^\+/)
    assert.match(row.amount, /CBBTC/)
  })

  it('maps privy swap title-only row after consolidation fields are set', () => {
    const row = mapCryptoTransactionToHistoryItem(
      {
        ...baseTx,
        side: 'swap',
        asset: 'CBBTC',
        transactionKind: 'crypto_swap',
        fromAsset: 'USDC',
        toAsset: 'CBBTC',
        swapAmountFrom: '250',
        swapAmountTo: '0.15',
        title: 'Échange USDC → CBBTC',
        subtitle: '+0.15 CBBTC · Base',
      },
      'EUR',
    )
    assert.equal(row.variant, 'swap')
    assert.equal(row.title, 'Échange · USDC → CBBTC')
    assert.equal(row.fromAsset, 'USDC')
    assert.equal(row.toAsset, 'CBBTC')
    assert.match(row.subtitle ?? '', /22 mai/)
    assert.match(row.meta ?? '', /USDC/)
  })

  it('maps privy credit-only swap leg with title parse to exchange row', () => {
    const row = mapCryptoTransactionToHistoryItem(
      {
        ...baseTx,
        side: 'deposit',
        asset: 'CBBTC',
        amountCrypto: '0.15',
        transactionKind: 'crypto_swap',
        title: 'Échange USDC → CBBTC',
        subtitle: '+0.15 CBBTC · Base',
        direction: 'credit',
      },
      'EUR',
    )
    assert.equal(row.variant, 'swap')
    assert.equal(row.title, 'Échange · USDC → CBBTC')
    assert.equal(row.fromAsset, 'USDC')
    assert.equal(row.toAsset, 'CBBTC')
    assert.match(row.subtitle ?? '', /22 mai/)
    assert.equal(row.meta, undefined)
    assert.match(row.amount, /^\+/)
    assert.match(row.amount, /CBBTC/)
  })

  it('maps withdraw to outgoing flow row', () => {
    const row = mapCryptoTransactionToHistoryItem(
      {
        ...baseTx,
        side: 'withdraw',
        direction: 'debit',
        title: 'Retrait USDC',
      },
      'EUR',
    )
    assert.equal(row.variant, 'flow')
    assert.equal(row.flowDirection, 'out')
    assert.match(row.amount, /^−/)
  })

  it('maps lombard borrow to exchange-style borrow row', () => {
    const row = mapCryptoTransactionToHistoryItem(
      {
        ...baseTx,
        id: 'lombard-borrow-1',
        transactionKind: 'lombard_borrow',
        sourceSystem: 'lombard_v1',
        title: 'Emprunt · cbBTC → USDC',
        subtitle: 'Morpho · Base',
        fromAsset: 'CBBTC',
        toAsset: 'USDC',
        swapAmountFrom: '0.017857',
        swapAmountTo: '1000',
        amountCrypto: '1000',
      },
      'EUR',
    )
    assert.equal(row.variant, 'borrow')
    assert.equal(row.title, 'Emprunt · cbBTC → USDC')
    assert.equal(row.subtitle, 'Morpho · Base')
    assert.equal(row.fromAsset, 'CBBTC')
    assert.equal(row.toAsset, 'USDC')
    assert.match(row.amount, /1\s?000/)
    assert.match(row.amount, /USDC/)
    assert.match(row.meta ?? '', /Garantie · 0,017857 CBBTC/)
  })
})

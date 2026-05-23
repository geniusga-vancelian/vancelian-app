import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  formatCryptoTransactionAmount,
  isIncomingCryptoTransaction,
  mergeCryptoWalletTransactions,
  parsePrivyWalletDeposits,
} from './cryptoWalletFormat'

describe('parsePrivyWalletDeposits', () => {
  it('maps credit direction to deposit side', () => {
    const txs = parsePrivyWalletDeposits({
      deposits: [
        {
          id: '881d952b-f7ae-4cc3-ac06-232fa02644b7',
          direction: 'credit',
          asset: 'USDC',
          amount: '100',
          status: 'confirmed',
          created_at: '2026-05-23T06:44:39.933943Z',
          title: 'Dépôt USDC',
          subtitle: '+100 USDC',
          transaction_kind: 'privy_deposit_in',
        },
      ],
    })
    assert.equal(txs.length, 1)
    assert.equal(txs[0]?.side, 'deposit')
    assert.equal(isIncomingCryptoTransaction(txs[0]!), true)
  })
})

describe('mergeCryptoWalletTransactions', () => {
  it('deduplicates platform and privy sources by id', () => {
    const txs = mergeCryptoWalletTransactions(
      {
        transactions: [
          {
            id: '881d952b-f7ae-4cc3-ac06-232fa02644b7',
            side: 'deposit',
            asset: 'EURC',
            amount_crypto: '250',
            amount_fiat: '0',
            price: '0',
            currency: 'EUR',
            status: 'confirmed',
            created_at: '2026-05-23T15:30:09.436492Z',
            title: 'Dépôt EURC',
            subtitle: '+250 EURC',
            direction: 'credit',
            source_system: 'privy',
          },
        ],
      },
      {
        deposits: [
          {
            id: '881d952b-f7ae-4cc3-ac06-232fa02644b7',
            direction: 'credit',
            asset: 'EURC',
            amount: '250',
            status: 'confirmed',
            created_at: '2026-05-23T15:30:09.436492Z',
            title: 'Dépôt EURC',
            subtitle: '+250 EURC',
          },
        ],
      },
    )
    assert.equal(txs.length, 1)
  })
})

describe('formatCryptoTransactionAmount', () => {
  it('prefers crypto amount when fiat is zero placeholder', () => {
    const label = formatCryptoTransactionAmount({
      id: '1',
      side: 'deposit',
      asset: 'USDC',
      amountCrypto: '100',
      amountFiat: '0',
      price: '0',
      currency: 'EUR',
      status: 'confirmed',
      createdAt: '2026-05-23T06:44:39Z',
      title: 'Dépôt USDC',
      subtitle: '+100 USDC',
      direction: 'credit',
    })
    assert.equal(label, '100 USDC')
  })
})

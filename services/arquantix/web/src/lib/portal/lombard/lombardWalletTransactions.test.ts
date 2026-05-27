import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { PortalCryptoWalletTransaction } from '../cryptoWalletTypes'
import {
  collectLombardHiddenPrivyDepositKeys,
  shouldHidePrivyDepositForLombardBorrow,
} from './lombardWalletTransactions'

describe('lombardWalletTransactions helpers', () => {
  const lombardBorrow: PortalCryptoWalletTransaction = {
    id: 'lombard-borrow-abc',
    side: 'deposit',
    asset: 'USDC',
    amountCrypto: '1000',
    amountFiat: '',
    price: '',
    currency: 'EUR',
    status: 'success',
    createdAt: '2026-05-27T11:43:32.303Z',
    title: 'Emprunt · cbBTC → USDC',
    subtitle: 'Morpho · Base',
    direction: 'credit',
    transactionKind: 'lombard_borrow',
    sourceSystem: 'lombard_v1',
    fromAsset: 'CBBTC',
    toAsset: 'USDC',
    swapAmountFrom: '0.017857',
    swapAmountTo: '1000',
    txHash: '0x40bb82a9e77382ea8e2f00c60aa976756167fe5deba98e40708be690192df584',
  }

  it('collects hash and amount keys for dedup', () => {
    const keys = collectLombardHiddenPrivyDepositKeys([lombardBorrow])
    assert.equal(
      keys.has('hash:0x40bb82a9e77382ea8e2f00c60aa976756167fe5deba98e40708be690192df584'),
      true,
    )
    assert.equal(keys.has('amount:1000'), true)
  })

  it('hides generic privy deposit when lombard borrow matches amount', () => {
    const keys = collectLombardHiddenPrivyDepositKeys([lombardBorrow])
    const privyDeposit: PortalCryptoWalletTransaction = {
      ...lombardBorrow,
      id: 'privy-deposit-1',
      title: 'Dépôt USDC',
      transactionKind: 'privy_deposit_in',
      sourceSystem: 'privy',
      txHash: '0xsimf71c7d9972594b5294b282b40cb347579e9ebf58d0cb48a38cb01394',
    }

    assert.equal(shouldHidePrivyDepositForLombardBorrow(privyDeposit, keys), true)
  })

  it('keeps swap transactions visible', () => {
    const keys = collectLombardHiddenPrivyDepositKeys([lombardBorrow])
    const swap: PortalCryptoWalletTransaction = {
      ...lombardBorrow,
      id: 'swap-1',
      title: 'Échange USDC → AAVE',
      transactionKind: 'crypto_swap',
      sourceSystem: 'lifi_swap',
      amountCrypto: '15',
    }

    assert.equal(shouldHidePrivyDepositForLombardBorrow(swap, keys), false)
  })
})

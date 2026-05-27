import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  alignCryptoWalletDetailWithScopedPosition,
  buildCryptoWalletDetailFromScopedPosition,
  buildPrivyWalletPositionsSummary,
  formatCryptoTransactionAmount,
  formatDetailVolumeAmount,
  isIncomingCryptoTransaction,
  mergeCryptoWalletTransactions,
  parsePrivyWalletDeposits,
  resolvePositionSubtitle,
  resolveScopedPrivyPositionForAsset,
} from './cryptoWalletFormat'

describe('buildPrivyWalletPositionsSummary', () => {
  it('values CBBTC using BTC market quote', () => {
    const summary = buildPrivyWalletPositionsSummary(
      {
        balances: [
          {
            asset: 'CBBTC',
            name: 'CBBTC',
            balance: '0.3',
            available_balance: '0.3',
            icon_key: 'cbbtc',
            chain_type: 'ethereum',
            chain_id: 8453,
          },
        ],
      },
      {
        summaries: [
          {
            symbol: 'BTCUSDT',
            price: '100000',
            price_eur: '92000',
            change_24h_pct: '1.5',
          },
        ],
      },
      'EUR',
    )
    assert.equal(summary.positions.length, 1)
    const pos = summary.positions[0]
    assert.equal(pos?.asset, 'CBBTC')
    assert.equal(pos?.priceEur, 92000)
    assert.equal(pos?.estimatedValueEur, 27600)
    assert.equal(pos?.performance1dPct, 1.5)
    assert.equal(summary.totalValueEur, 27600)
  })

  it('includes dedicated Solana wallet at zero balance', () => {
    const summary = buildPrivyWalletPositionsSummary(
      {
        summary: { positions_count: 1, wallet_count: 1 },
        balances: [
          {
            asset: 'SOL',
            name: 'Solana',
            balance: '0',
            available_balance: '0',
            icon_key: 'sol',
            chain_type: 'solana',
            dedicated_wallet: true,
            wallet_address: 'G3LsoYMqDp3NAEHG5DQT9SB3JfouXH9heUGLLmHLd6QR',
          },
        ],
      },
      null,
      'EUR',
    )
    assert.equal(summary.positions.length, 1)
    assert.equal(summary.positions[0]?.asset, 'SOL')
    assert.equal(summary.positions[0]?.balance, 0)
    assert.equal(summary.positions[0]?.dedicatedWallet, true)
    assert.match(resolvePositionSubtitle(summary.positions[0]!), /Wallet Solana · 0\.0000 SOL/)
  })
})

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

describe('alignCryptoWalletDetailWithScopedPosition', () => {
  it('remplace un volume agrégé par le solde Privy scopé Base', () => {
    const summary = buildPrivyWalletPositionsSummary(
      {
        balances: [
          {
            asset: 'ETH',
            name: 'Ethereum',
            balance: '0.00857064',
            available_balance: '0.00857064',
            icon_key: 'eth',
            chain_type: 'ethereum',
            chain_id: 8453,
            wallet_address: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
          },
        ],
      },
      {
        summaries: [
          {
            symbol: 'ETHUSDT',
            price: '2131.29',
            price_eur: '1960.00',
          },
        ],
      },
      'USD',
    )

    const scoped = resolveScopedPrivyPositionForAsset(
      summary,
      'ETH',
      'base',
      {
        id: 'privy:test',
        kind: 'privy_embedded',
        label: 'Privy',
        shortLabel: 'Privy',
        address: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
        chainType: 'evm',
      },
    )

    const aligned = alignCryptoWalletDetailWithScopedPosition(
      {
        asset: 'ETH',
        name: 'Ethereum',
        iconKey: 'eth',
        volume: '0.030000000000000000',
        totalValueEur: 55.81,
        totalValueUsd: 63.94,
        realizedGainEur: 0,
        realizedGains: 0,
        portfolioScope: 'privy',
      },
      scoped,
    )

    assert.equal(aligned.volume, formatDetailVolumeAmount(0.00857064, 'ETH'))
    assert.ok((aligned.totalValueUsd ?? 0) < 20)
  })

  it('construit un détail depuis le hub Privy si crypto-positions est vide', () => {
    const summary = buildPrivyWalletPositionsSummary(
      {
        balances: [
          {
            asset: 'ETH',
            name: 'Ethereum',
            balance: '0.00857064',
            available_balance: '0.00857064',
            icon_key: 'eth',
            chain_type: 'ethereum',
            chain_id: 8453,
          },
        ],
      },
      {
        summaries: [{ symbol: 'ETHUSDT', price: '2131.29', price_eur: '1960.00' }],
      },
      'USD',
    )

    const scoped = resolveScopedPrivyPositionForAsset(summary, 'ETH', 'base', null)
    assert.ok(scoped)
    const detail = buildCryptoWalletDetailFromScopedPosition(scoped!)
    assert.equal(detail.volume, formatDetailVolumeAmount(0.00857064, 'ETH'))
    assert.equal(detail.asset, 'ETH')
  })
})

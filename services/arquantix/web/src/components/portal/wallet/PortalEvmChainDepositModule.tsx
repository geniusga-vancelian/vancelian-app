'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { ChainDepositQr } from '@/components/portal/wallet/ChainDepositQr'
import {
  CHAIN_FLOW_ASSETS,
  ChainFlowAssetGlyph,
  ChainFlowPill,
  chainFlowNetworkLabel,
  resolveChainNetworkMeta,
} from '@/components/portal/wallet/chainFlowShared'
import {
  formatEvmNetworkShort,
  resolveEvmExplorerAddressUrl,
} from '@/lib/portal/evmNetworkLabel'
import type { PortalPersonCryptoWallet } from '@/lib/portal/privyWalletClient'
import { cn } from '@/lib/utils'

type Props = {
  wallets: PortalPersonCryptoWallet[]
  activeWallet: PortalPersonCryptoWallet | null
  onSelectWallet: (wallet: PortalPersonCryptoWallet) => void
  loading?: boolean
  error?: string
  onRefresh?: () => void
  refreshing?: boolean
}

export function PortalEvmChainDepositModule({
  wallets,
  activeWallet,
  onSelectWallet,
  loading = false,
  error = '',
  onRefresh,
  refreshing = false,
}: Props) {
  const [assetId, setAssetId] = useState('usdc')
  const [copied, setCopied] = useState(false)

  const asset = CHAIN_FLOW_ASSETS.find((row) => row.id === assetId) ?? CHAIN_FLOW_ASSETS[0]!
  const chainId = activeWallet?.chain_id ?? 1
  const networkLabel = chainFlowNetworkLabel(chainId)
  const networkShort = formatEvmNetworkShort(chainId)
  const networkMeta = resolveChainNetworkMeta(chainId)
  const address = activeWallet?.address?.trim() ?? ''
  const addressReady = Boolean(address) && !loading
  const explorerUrl = activeWallet
    ? resolveEvmExplorerAddressUrl(activeWallet.address, activeWallet.chain_id)
    : null

  const howSteps = useMemo(
    () => [
      {
        title: 'Select asset and network',
        body: 'The network must match the one used by your external source (exchange or wallet).',
      },
      {
        title: 'Send to the address above',
        body: `From your external source, transfer ${asset.sym} to this address — it only accepts ${asset.sym} on ${networkLabel}.`,
      },
      {
        title: 'Credited after confirmation',
        body: `Funds appear in your balance after ${networkMeta.confirmations} confirmation${networkMeta.confirmations > 1 ? 's' : ''} (${networkMeta.time}).`,
      },
    ],
    [asset.sym, networkLabel, networkMeta.confirmations, networkMeta.time],
  )

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1600)
    return () => window.clearTimeout(timer)
  }, [copied])

  const copyAddress = useCallback(async () => {
    if (!address) return
    try {
      await navigator.clipboard.writeText(address)
      setCopied(true)
    } catch {
      /* clipboard blocked */
    }
  }, [address])

  return (
    <div className="chain">
      <header className="chain__head">
        <div>
          <h1 className="chain__title">Deposit via blockchain</h1>
          <p className="chain__sub">
            Send {asset.sym} on your selected network to the address below. Your Vancelian
            embedded wallet (Privy) is non-custodial.
          </p>
        </div>
        {onRefresh ? (
          <button
            type="button"
            className="inv-head__btn"
            aria-label="Refresh"
            disabled={refreshing}
            onClick={onRefresh}
          >
            <KalaiIcon name="update" size={16} />
          </button>
        ) : null}
      </header>

      <div className="chain__body">
        <div>
          <p className="chain__eyebrow">
            <span className="num">1</span>
            Asset to deposit
          </p>
          <div className="chain__pills">
            {CHAIN_FLOW_ASSETS.map((row) => (
              <ChainFlowPill
                key={row.id}
                active={row.id === assetId}
                onClick={() => setAssetId(row.id)}
                label={row.sym}
                glyph={<ChainFlowAssetGlyph sym={row.sym} />}
              />
            ))}
          </div>
        </div>

        <div>
          <p className="chain__eyebrow">
            <span className="num">2</span>
            Deposit network
          </p>
          <div className="chain__pills">
            {wallets.length > 0 ? (
              wallets.map((wallet) => {
                const walletChainId = wallet.chain_id ?? 1
                const meta = resolveChainNetworkMeta(walletChainId)
                return (
                  <ChainFlowPill
                    key={wallet.id}
                    active={activeWallet?.id === wallet.id}
                    onClick={() => onSelectWallet(wallet)}
                    label={chainFlowNetworkLabel(walletChainId)}
                    sub={meta.short}
                  />
                )
              })
            ) : (
              <ChainFlowPill
                active
                onClick={() => undefined}
                label={networkLabel}
                sub={networkShort}
                disabled
              />
            )}
          </div>
        </div>

        <div>
          <p className="chain__eyebrow">
            <span className="num">3</span>
            Deposit address
          </p>
          <div className="chain-addr">
            <div className="chain-addr__qr">
              {addressReady ? (
                <ChainDepositQr value={address} />
              ) : (
                <span className="portal-shimmer h-full w-full rounded-v-input" aria-hidden />
              )}
            </div>
            <div className="chain-addr__body">
              <p className="chain-addr__label">
                {asset.sym} · {networkLabel}
              </p>
              {addressReady ? (
                <p className="chain-addr__value">{address}</p>
              ) : (
                <span className="portal-shimmer block h-[52px] w-full rounded-v-input" aria-hidden />
              )}
              <div className="chain-addr__actions">
                <button
                  type="button"
                  className={cn('chain-addr__btn', copied && 'is-copied')}
                  disabled={!addressReady}
                  onClick={() => void copyAddress()}
                >
                  <KalaiIcon name={copied ? 'check' : 'exchange'} size={16} />
                  {copied ? 'Address copied' : 'Copy address'}
                </button>
                {explorerUrl ? (
                  <a
                    className="chain-addr__btn chain-addr__btn--ghost"
                    href={explorerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <KalaiIcon name="arrow-up-right" size={16} />
                    View on explorer
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        <div className="chain-meta">
          <div className="chain-meta__cell">
            <span className="chain-meta__k">Estimated time</span>
            <span className="chain-meta__v">{networkMeta.time}</span>
          </div>
          <div className="chain-meta__cell">
            <span className="chain-meta__k">Confirmations</span>
            <span className="chain-meta__v">{networkMeta.confirmations}</span>
          </div>
          <div className="chain-meta__cell">
            <span className="chain-meta__k">Wallet type</span>
            <span className="chain-meta__v">Privy · EVM</span>
          </div>
        </div>

        <div className="chain-warn">
          <KalaiIcon name="info" size={16} className="shrink-0 text-[#C99A2E]" aria-hidden />
          <span>
            Only send <b>{asset.sym}</b> on the <b>{networkLabel}</b> network. Any other asset or
            network may result in permanent loss of funds.
          </span>
        </div>

        <div className="chain-how">
          <h2 className="chain-how__title">
            <KalaiIcon name="info" size={16} aria-hidden />
            How it works
          </h2>
          <ol className="chain-how__list">
            {howSteps.map((step) => (
              <li key={step.title} className="chain-how__item">
                <div>
                  <b>{step.title}</b>
                  <span>{step.body}</span>
                </div>
              </li>
            ))}
          </ol>
        </div>

        {error ? <p className="m-0 font-ui text-[14px] text-v-error">{error}</p> : null}
      </div>
    </div>
  )
}

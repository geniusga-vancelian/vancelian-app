'use client'

import { useMemo, useState } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  CHAIN_FLOW_ASSETS,
  ChainFlowAssetGlyph,
  ChainFlowPill,
  EVM_ADDRESS_PATTERN,
  chainFlowAddressPlaceholder,
  chainFlowNetworkLabel,
  formatChainFlowAmount,
  parseChainFlowAmountInput,
  resolveChainNetworkMeta,
} from '@/components/portal/wallet/chainFlowShared'
import type { PortalPersonCryptoWallet } from '@/lib/portal/privyWalletClient'

type Props = {
  wallets: PortalPersonCryptoWallet[]
  activeWallet: PortalPersonCryptoWallet | null
  onSelectWallet: (wallet: PortalPersonCryptoWallet) => void
  balances: Record<string, number>
  loading?: boolean
  error?: string
  onCancel?: () => void
  onRefresh?: () => void
  refreshing?: boolean
}

export function PortalEvmChainWithdrawModule({
  wallets,
  activeWallet,
  onSelectWallet,
  balances,
  loading = false,
  error = '',
  onCancel,
  onRefresh,
  refreshing = false,
}: Props) {
  const [assetId, setAssetId] = useState('usdc')
  const [destinationAddress, setDestinationAddress] = useState('')
  const [amountInput, setAmountInput] = useState('')

  const asset = CHAIN_FLOW_ASSETS.find((row) => row.id === assetId) ?? CHAIN_FLOW_ASSETS[0]!
  const chainId = activeWallet?.chain_id ?? 1
  const networkLabel = chainFlowNetworkLabel(chainId)
  const networkMeta = resolveChainNetworkMeta(chainId)
  const availableBalance = balances[asset.sym.toUpperCase()] ?? 0
  const numericAmount = parseChainFlowAmountInput(amountInput)
  const networkFee = 0
  const willReceive = Math.max(numericAmount - networkFee, 0)

  const addressValid = useMemo(() => {
    if (!destinationAddress.trim()) return null
    return EVM_ADDRESS_PATTERN.test(destinationAddress.trim())
  }, [destinationAddress])

  const amountOk = numericAmount > 0 && numericAmount <= availableBalance
  const canSubmit = amountOk && addressValid === true && !loading

  const howSteps = useMemo(
    () => [
      {
        title: 'Enter the destination address',
        body: `The address must belong to your external wallet on the ${networkLabel} network.`,
      },
      {
        title: 'Enter the amount',
        body: 'Network fees are deducted from the amount sent.',
      },
      {
        title: 'Review and confirm',
        body: `The withdrawal is broadcast on ${networkLabel}. Funds are available at the destination after ${networkMeta.confirmations} confirmation${networkMeta.confirmations > 1 ? 's' : ''} (${networkMeta.time}).`,
      },
    ],
    [networkLabel, networkMeta.confirmations, networkMeta.time],
  )

  const pasteAddress = async () => {
    try {
      const text = await navigator.clipboard.readText()
      setDestinationAddress(text.trim())
    } catch {
      /* clipboard blocked */
    }
  }

  const setMaxAmount = () => {
    setAmountInput(formatChainFlowAmount(availableBalance, asset.id))
  }

  const placeholderAddress = chainFlowAddressPlaceholder(
    activeWallet?.address ?? '0x0000000000000000000000000000000000000000',
    networkLabel,
  )

  return (
    <div className="chain">
      <header className="chain__head">
        <div>
          <h1 className="chain__title">Withdraw via blockchain</h1>
          <p className="chain__sub">
            Send {asset.sym} from your Vancelian balance to an external address.
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
        ) : onCancel ? (
          <button type="button" className="chain__close" aria-label="Close" onClick={onCancel}>
            <KalaiIcon name="close" size={16} />
          </button>
        ) : null}
      </header>

      <div className="chain__body">
        <div>
          <p className="chain__eyebrow chain__eyebrow--split">
            <span className="chain__eyebrow-main">
              <span className="num">1</span>
              Asset to withdraw
            </span>
            <span className="chain__eyebrow-extra">
              Available balance · {formatChainFlowAmount(availableBalance, asset.id)} {asset.sym}
            </span>
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
            Withdrawal network
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
                sub={networkMeta.short}
                disabled
              />
            )}
          </div>
        </div>

        <div className="chain-field">
          <p className="chain__eyebrow chain__eyebrow--split chain__eyebrow--flush">
            <span className="chain__eyebrow-main">
              <span className="num">3</span>
              Destination address
            </span>
            <button type="button" className="chain-field__paste" onClick={() => void pasteAddress()}>
              Paste from clipboard
            </button>
          </p>
          <textarea
            className="chain-field__textarea"
            rows={2}
            value={destinationAddress}
            onChange={(event) => setDestinationAddress(event.target.value)}
            placeholder={placeholderAddress}
            aria-invalid={addressValid === false}
          />
          {addressValid === true ? (
            <span className="chain-field__hint chain-field__hint--ok">
              <KalaiIcon name="check" size={16} aria-hidden />
              Valid {networkLabel} address
            </span>
          ) : null}
          {addressValid === false ? (
            <span className="chain-field__hint chain-field__hint--ko">
              <KalaiIcon name="info" size={16} aria-hidden />
              Invalid {networkLabel} address format
            </span>
          ) : null}
          {addressValid === null ? (
            <span className="chain-field__hint">
              Double-check the address network before withdrawing.
            </span>
          ) : null}
        </div>

        <div className="chain-field">
          <p className="chain__eyebrow chain__eyebrow--flush">
            <span className="num">4</span>
            Amount to withdraw
          </p>
          <div className="chain-amt">
            <input
              className="chain-amt__input"
              inputMode="decimal"
              value={amountInput}
              onChange={(event) => setAmountInput(event.target.value)}
              placeholder="0.00"
              aria-invalid={numericAmount > availableBalance}
            />
            <span className="chain-amt__unit">{asset.sym}</span>
            <button type="button" className="btn--max" onClick={setMaxAmount}>
              Max
            </button>
          </div>
          {numericAmount > availableBalance ? (
            <span className="chain-field__hint chain-field__hint--ko">
              <KalaiIcon name="info" size={16} aria-hidden />
              Amount exceeds your available balance
            </span>
          ) : null}

          <div className="chain-sum">
            <div className="chain-sum__row">
              <span>Amount sent</span>
              <span>
                {numericAmount > 0 ? `${formatChainFlowAmount(numericAmount, asset.id)} ${asset.sym}` : '—'}
              </span>
            </div>
            <div className="chain-sum__row">
              <span>Network fee ({networkLabel})</span>
              <span>{networkMeta.feeLabel ?? '—'}</span>
            </div>
            <div className="chain-sum__row is-total">
              <span>Amount received at address</span>
              <span>
                {numericAmount > 0
                  ? `${formatChainFlowAmount(willReceive, asset.id)} ${asset.sym}`
                  : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="chain-warn">
          <KalaiIcon name="info" size={16} className="shrink-0 text-[#C99A2E]" aria-hidden />
          <span>
            Verify the destination address and selected network.{' '}
            <b>Any mistake is irreversible.</b> Vancelian cannot recover funds sent to an incorrect
            address.
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

      <div className="chain__foot">
        <button type="button" className="btn btn--secondary btn--lg" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn btn--primary btn--lg" disabled={!canSubmit}>
          {canSubmit
            ? `Withdraw ${formatChainFlowAmount(numericAmount, asset.id)} ${asset.sym}`
            : 'Withdraw'}
        </button>
      </div>
    </div>
  )
}

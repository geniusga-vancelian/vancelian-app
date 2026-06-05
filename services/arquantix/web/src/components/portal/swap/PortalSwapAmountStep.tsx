'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalInvestFlowDom } from '@/components/portal/invest/PortalInvestFlowDom'
import { PortalInvestChip } from '@/components/portal/invest/PortalInvestFlowParts'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalSwapAssetSelector } from '@/components/portal/swap/PortalSwapAssetSelector'
import { PortalSwapTechDetails } from '@/components/portal/swap/PortalSwapTechDetails'
import { isSwapAmountOverPrivyBalance } from '@/lib/portal/swapAmountValidation'
import {
  formatSwapMinAmountError,
  isSwapAmountBelowCatalogMin,
} from '@/lib/portal/swapMinAmount'
import {
  formatSwapCryptoAmount,
  swapAssetChipMeta,
  type SwapFromOption,
  type SwapToOption,
} from '@/lib/portal/swapFlowFormat'
import { formatSwapFeeLine } from '@/lib/portal/swapFlowSteps'
import { requestSwapQuote, type SwapQuotePayload } from '@/lib/portal/swapClient'
import {
  buildSwapSigningWalletQuoteParams,
} from '@/lib/portal/swapSigningWallet'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

type Props = {
  fromAsset: string
  toAsset: string
  fromChain: string
  toChain: string
  sourceBalance: number
  /** Solde wallet encore en cours de chargement (évite d'afficher 0 prématurément). */
  sourceBalancePending?: boolean
  /** `min_amount` catalogue API pour l'actif source (garde-fou UI avant quote). */
  minAmount?: string | null
  fromOptions: SwapFromOption[]
  toOptions: SwapToOption[]
  onChangeFrom: (option: SwapFromOption) => void
  onChangeTo: (option: SwapToOption) => void
  onContinue: (amount: string, quote: SwapQuotePayload) => void
  onBack: () => void
}

export function PortalSwapAmountStep({
  fromAsset,
  toAsset,
  fromChain,
  toChain,
  sourceBalance,
  sourceBalancePending = false,
  minAmount,
  fromOptions,
  toOptions,
  onChangeFrom,
  onChangeTo,
  onContinue,
  onBack,
}: Props) {
  const { executionAddress, isExternalWallet, scopeLoading } = usePortalExecutionScope()
  const signingMode = isExternalWallet ? 'external_evm' : 'privy_embedded'

  const [amount, setAmount] = useState('')
  const [quote, setQuote] = useState<SwapQuotePayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scene, setScene] = useState<'form' | 'selector'>('form')
  const [field, setField] = useState<'from' | 'to' | null>(null)
  const [popKey, setPopKey] = useState({ from: 0, to: 0 })

  const fromChip = useMemo(() => swapAssetChipMeta(fromAsset), [fromAsset])
  const toChip = useMemo(() => swapAssetChipMeta(toAsset), [toAsset])
  const canPickFrom = fromOptions.length > 1
  const canPickTo = toOptions.length > 1

  const parsed = Number(amount.replace(',', '.'))
  const usesPrivyBalance = !isExternalWallet
  const overBalance = usesPrivyBalance && isSwapAmountOverPrivyBalance(parsed, sourceBalance)
  const belowMin =
    parsed > 0 && minAmount != null && isSwapAmountBelowCatalogMin(parsed, minAmount)
  const minAmountError =
    belowMin && minAmount ? formatSwapMinAmountError(fromAsset, minAmount) : null
  const canContinue =
    parsed > 0 && !overBalance && !belowMin && quote !== null && !loading && !scopeLoading

  const fetchQuote = useCallback(async () => {
    if (parsed <= 0) {
      setQuote(null)
      setError(null)
      return
    }

    if (minAmount && isSwapAmountBelowCatalogMin(parsed, minAmount)) {
      setQuote(null)
      setError(formatSwapMinAmountError(fromAsset, minAmount))
      return
    }

    if (scopeLoading) return

    setLoading(true)
    setError(null)
    try {
      const signing = buildSwapSigningWalletQuoteParams({
        mode: signingMode,
        privyEmbeddedAddress: !isExternalWallet ? executionAddress : null,
        externalWalletAddress: isExternalWallet ? executionAddress : null,
      })
      const result = await requestSwapQuote({
        from_asset: fromAsset,
        to_asset: toAsset,
        amount: String(parsed),
        from_chain: fromChain,
        to_chain: toChain,
        ...signing,
      })
      setQuote(result)
    } catch (e) {
      setQuote(null)
      setError(e instanceof Error ? e.message : 'Quote unavailable')
    } finally {
      setLoading(false)
    }
  }, [
    fromAsset,
    fromChain,
    minAmount,
    executionAddress,
    isExternalWallet,
    parsed,
    signingMode,
    toAsset,
    toChain,
    scopeLoading,
  ])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchQuote()
    }, 500)
    return () => window.clearTimeout(timer)
  }, [fetchQuote])

  useEffect(() => {
    setAmount('')
    setQuote(null)
    setError(null)
  }, [fromAsset, toAsset, fromChain, toChain])

  const receiveLabel = quote
    ? formatSwapCryptoAmount(quote.estimated_receive, toAsset)
    : loading
      ? '…'
      : '0'

  const openSelector = (next: 'from' | 'to') => {
    if (next === 'from' && !canPickFrom) return
    if (next === 'to' && !canPickTo) return
    setField(next)
    setScene('selector')
  }

  const closeSelector = () => {
    setScene('form')
  }

  const pickFrom = (option: SwapFromOption) => {
    onChangeFrom(option)
    setPopKey((p) => ({ ...p, from: p.from + 1 }))
    closeSelector()
  }

  const pickTo = (option: SwapToOption) => {
    onChangeTo(option)
    setPopKey((p) => ({ ...p, to: p.to + 1 }))
    closeSelector()
  }

  const applyMax = () => {
    if (sourceBalance <= 0) return
    setAmount(formatSwapCryptoAmount(sourceBalance, fromAsset))
  }

  const ctaLabel =
    parsed > 0
      ? `Continue · ${formatSwapCryptoAmount(parsed, fromAsset)} ${fromAsset}`
      : 'Enter an amount'

  return (
    <PortalInvestFlowDom
      scene={scene}
      form={
        <div className="inv-pane">
          <header className="inv-head">
            <h2 className="inv-head__title">Swap</h2>
            <div className="inv-head__actions">
              <button type="button" className="inv-head__btn" onClick={onBack} aria-label="Close">
                <KalaiIcon name="close" size={16} />
              </button>
            </div>
          </header>

          <div className="inv-iowrap">
            <div className="inv-io">
              <div className="inv-io__top">
                <span className="inv-io__label">You pay</span>
                <span className="inv-io__balance">
                  {usesPrivyBalance ? (
                    sourceBalancePending ? (
                      <>Balance …</>
                    ) : (
                      <>
                        Balance {formatSwapCryptoAmount(sourceBalance, fromAsset)} {fromAsset}
                        {sourceBalance > 0 ? (
                          <button type="button" className="inv-io__max" onClick={applyMax}>
                            Max
                          </button>
                        ) : null}
                      </>
                    )
                  ) : (
                    <>Wallet balance</>
                  )}
                </span>
              </div>
              <div className="inv-io__row">
                <input
                  type="text"
                  inputMode="decimal"
                  className={`inv-io__amount${overBalance ? ' inv-io__amount--muted' : ''}`}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0"
                  aria-label="Amount to swap"
                />
                <PortalInvestChip
                  asset={fromChip}
                  popKey={popKey.from}
                  selectable={canPickFrom}
                  onClick={() => openSelector('from')}
                />
              </div>
            </div>

            <div className="inv-divider" aria-hidden="true" />

            <div className="inv-io">
              <div className="inv-io__top">
                <span className="inv-io__label">You receive</span>
                <span className="inv-io__balance">
                  {loading ? (
                    <span className="inline-flex items-center gap-1.5">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Estimating…
                    </span>
                  ) : (
                    <>≈ {receiveLabel} {toAsset}</>
                  )}
                </span>
              </div>
              <div className="inv-io__row">
                <input
                  type="text"
                  className="inv-io__amount"
                  value={receiveLabel}
                  readOnly
                  aria-label="Estimated receive amount"
                />
                <PortalInvestChip
                  asset={toChip}
                  popKey={popKey.to}
                  selectable={canPickTo}
                  onClick={() => openSelector('to')}
                />
              </div>
            </div>
          </div>

          {quote ? (
            <div className="inv-summary">
              {quote.exchange_rate ? (
                <div className="inv-summary__row">
                  <span className="k">Exchange rate</span>
                  <span className="v">
                    1 {fromAsset} ≈ {formatSwapCryptoAmount(quote.exchange_rate, toAsset)} {toAsset}
                  </span>
                </div>
              ) : null}
              <div className="inv-summary__row">
                <span className="k">Minimum receive</span>
                <span className="v">
                  {formatSwapCryptoAmount(quote.estimated_receive_min, toAsset)} {toAsset}
                </span>
              </div>
              <div className="inv-summary__row">
                <span className="k">Vancelian fees</span>
                <span className="v v--accent">Waived</span>
              </div>
              <div className="inv-summary__row">
                <span className="k">Network fees</span>
                <span className="v">{formatSwapFeeLine(quote)}</span>
              </div>
            </div>
          ) : null}

          {overBalance ? (
            <p className="inv-feedback inv-feedback--error">
              {sourceBalance > 0
                ? `Amount exceeds available balance (${formatSwapCryptoAmount(sourceBalance, fromAsset)} ${fromAsset}).`
                : `Insufficient ${fromAsset} balance.`}
            </p>
          ) : null}

          {minAmountError ?? error ? (
            <p className="inv-feedback inv-feedback--error">{minAmountError ?? error}</p>
          ) : null}

          <button
            type="button"
            className="btn btn--primary btn--lg inv-cta"
            disabled={!canContinue}
            onClick={() => quote && onContinue(amount, quote)}
          >
            {loading && parsed > 0 ? (
              <span className="inline-flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Updating quote…
              </span>
            ) : (
              ctaLabel
            )}
          </button>

          {quote ? <PortalSwapTechDetails quote={quote} /> : null}
        </div>
      }
      selector={
        scene === 'selector' && field ? (
          <PortalSwapAssetSelector
            field={field}
            fromAsset={fromAsset}
            toAsset={toAsset}
            fromOptions={fromOptions}
            toOptions={toOptions}
            onPickFrom={pickFrom}
            onPickTo={pickTo}
            onClose={closeSelector}
          />
        ) : null
      }
    />
  )
}

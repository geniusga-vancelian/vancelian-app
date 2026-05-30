'use client'

import { useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalInvestChip } from '@/components/portal/invest/PortalInvestFlowParts'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalSwapExecutionProgress } from '@/components/portal/swap/PortalSwapExecutionProgress'
import { PortalSwapTechDetails } from '@/components/portal/swap/PortalSwapTechDetails'
import {
  formatSwapCryptoAmount,
  swapAssetChipMeta,
} from '@/lib/portal/swapFlowFormat'
import { formatSwapFeeLine, swapConfirmCtaLabel } from '@/lib/portal/swapFlowSteps'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'

type Props = {
  fromAsset: string
  toAsset: string
  amount: string
  quote: SwapQuotePayload
  executionPhase: SwapExecutionPhase
  executing: boolean
  error: string | null
  onConfirm: () => void
  onBack: () => void
}

export function PortalSwapConfirmStep({
  fromAsset,
  toAsset,
  amount,
  quote,
  executionPhase,
  executing,
  error,
  onConfirm,
  onBack,
}: Props) {
  const [acknowledged, setAcknowledged] = useState(false)

  const fromChip = useMemo(() => swapAssetChipMeta(fromAsset), [fromAsset])
  const toChip = useMemo(() => swapAssetChipMeta(toAsset), [toAsset])

  const parsed = Number(amount.replace(',', '.'))
  const payAmount = formatSwapCryptoAmount(parsed > 0 ? parsed : quote.amount_in)
  const receiveAmount = formatSwapCryptoAmount(quote.estimated_receive)

  const ctaLabel = swapConfirmCtaLabel({
    executing,
    executionPhase,
    amount: payAmount,
    fromAsset,
    quote,
  })

  return (
    <div className="inv-pane">
      <header className="inv-head">
        <h2 className="inv-head__title">Confirm swap</h2>
        {!executing ? (
          <div className="inv-head__actions">
            <button type="button" className="inv-head__btn" onClick={onBack} aria-label="Back">
              <KalaiIcon name="close" size={16} />
            </button>
          </div>
        ) : null}
      </header>

      <div className="inv-iowrap">
        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">You pay</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={payAmount}
              readOnly
              aria-label="Amount to pay"
            />
            <PortalInvestChip asset={fromChip} selectable={false} />
          </div>
        </div>

        <div className="inv-divider" aria-hidden="true" />

        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">You receive</span>
            <span className="inv-io__balance">≈ {receiveAmount} {toAsset}</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={receiveAmount}
              readOnly
              aria-label="Estimated receive amount"
            />
            <PortalInvestChip asset={toChip} selectable={false} />
          </div>
        </div>
      </div>

      {!executing ? (
        <div className="inv-summary">
          {quote.exchange_rate ? (
            <div className="inv-summary__row">
              <span className="k">Exchange rate</span>
              <span className="v">
                1 {fromAsset} ≈ {formatSwapCryptoAmount(quote.exchange_rate)} {toAsset}
              </span>
            </div>
          ) : null}
          <div className="inv-summary__row">
            <span className="k">Minimum receive</span>
            <span className="v">
              {formatSwapCryptoAmount(quote.estimated_receive_min)} {toAsset}
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
      ) : (
        <PortalSwapExecutionProgress phase={executionPhase} />
      )}

      {!executing ? (
        <label className="inv-ack">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
          />
          <span>
            I accept that this swap will execute at the estimated price. The final amount may vary
            slightly based on market and network conditions.
          </span>
        </label>
      ) : null}

      {error ? <p className="inv-feedback inv-feedback--error">{error}</p> : null}

      <button
        type="button"
        className="btn btn--primary btn--lg inv-cta"
        disabled={executing || !acknowledged}
        onClick={onConfirm}
      >
        {executing ? (
          <span className="inline-flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            {ctaLabel}
          </span>
        ) : (
          ctaLabel
        )}
      </button>

      {!executing ? <PortalSwapTechDetails quote={quote} /> : null}
    </div>
  )
}

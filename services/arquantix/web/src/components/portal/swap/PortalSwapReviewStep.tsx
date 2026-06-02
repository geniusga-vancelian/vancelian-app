'use client'

import { useMemo } from 'react'

import { PortalInvestChip } from '@/components/portal/invest/PortalInvestFlowParts'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { buildSwapTechnicalDetailRows } from '@/components/portal/transaction/mappers/swapSteps'
import { SWAP_REVIEW_UI } from '@/components/portal/transaction/mappers/swapUiCopy'
import {
  formatSwapCryptoAmount,
  swapAssetChipMeta,
} from '@/lib/portal/swapFlowFormat'
import { formatSwapFeeLine } from '@/lib/portal/swapFlowSteps'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'

type Props = {
  fromAsset: string
  toAsset: string
  amount: string
  quote: SwapQuotePayload
  onConfirm: () => void
  onBack: () => void
}

/** Swap Review — recap only, no execution (R4.5-C). */
export function PortalSwapReviewStep({
  fromAsset,
  toAsset,
  amount,
  quote,
  onConfirm,
  onBack,
}: Props) {
  const fromChip = useMemo(() => swapAssetChipMeta(fromAsset), [fromAsset])
  const toChip = useMemo(() => swapAssetChipMeta(toAsset), [toAsset])

  const parsed = Number(amount.replace(',', '.'))
  const payAmount = formatSwapCryptoAmount(parsed > 0 ? parsed : quote.amount_in)
  const receiveAmount = formatSwapCryptoAmount(quote.estimated_receive)
  const networkLabel = SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain

  const techRows = useMemo(() => buildSwapTechnicalDetailRows(quote), [quote])

  return (
    <TransactionReviewPage
      title={SWAP_REVIEW_UI.title}
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={SWAP_REVIEW_UI.backButton}
      primaryAction={{
        label: SWAP_REVIEW_UI.confirmCta,
        onClick: onConfirm,
      }}
    >
      <div className="inv-iowrap">
        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">{SWAP_REVIEW_UI.youPay}</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={payAmount}
              readOnly
              aria-label={SWAP_REVIEW_UI.amountPaidAria}
            />
            <PortalInvestChip asset={fromChip} selectable={false} />
          </div>
        </div>

        <div className="inv-divider" aria-hidden="true" />

        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">{SWAP_REVIEW_UI.youReceive}</span>
            <span className="inv-io__balance">≈ {receiveAmount} {toAsset}</span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={receiveAmount}
              readOnly
              aria-label={SWAP_REVIEW_UI.amountReceiveAria}
            />
            <PortalInvestChip asset={toChip} selectable={false} />
          </div>
        </div>
      </div>

      <div className="inv-summary">
        {quote.exchange_rate ? (
          <div className="inv-summary__row">
            <span className="k">{SWAP_REVIEW_UI.exchangeRate}</span>
            <span className="v">
              1 {fromAsset} ≈ {formatSwapCryptoAmount(quote.exchange_rate)} {toAsset}
            </span>
          </div>
        ) : null}
        <div className="inv-summary__row">
          <span className="k">{SWAP_REVIEW_UI.minimumReceive}</span>
          <span className="v">
            {formatSwapCryptoAmount(quote.estimated_receive_min)} {toAsset}
          </span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{SWAP_REVIEW_UI.vancelianFees}</span>
          <span className="v v--accent">{SWAP_REVIEW_UI.vancelianFeesWaived}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{SWAP_REVIEW_UI.networkFees}</span>
          <span className="v">{formatSwapFeeLine(quote)}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{SWAP_REVIEW_UI.network}</span>
          <span className="v">{networkLabel}</span>
        </div>
      </div>

      <TransactionTechnicalDetails rows={techRows} title={SWAP_REVIEW_UI.technicalDetailsTitle} />
    </TransactionReviewPage>
  )
}

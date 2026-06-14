'use client'

import { useCallback, useMemo, useState } from 'react'

import { TransactionConfirmStepsPreview } from '@/components/portal/transaction/TransactionConfirmStepsPreview'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import {
  buildSwapReviewPreviewSteps,
  buildSwapTechnicalDetailRows,
} from '@/components/portal/transaction/mappers/swapSteps'
import { SWAP_REVIEW_UI } from '@/components/portal/transaction/mappers/swapUiCopy'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import { formatSwapFeeLine } from '@/lib/portal/swapFlowSteps'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'
import type { SwapProcessingContext } from '@/components/portal/transaction/mappers/swapSteps'

type Props = {
  fromAsset: string
  toAsset: string
  amount: string
  quote: SwapQuotePayload
  swapProcessingContext: SwapProcessingContext
  onConfirm: () => void
  onBack: () => void
}

/** Swap Review — récap handoff InvestConfirm, sans exécution (R4.5-C). */
export function PortalSwapReviewStep({
  fromAsset,
  toAsset,
  amount,
  quote,
  swapProcessingContext,
  onConfirm,
  onBack,
}: Props) {
  // PR4 — anti double-clic : verrouille le CTA dès la première confirmation.
  const [submitting, setSubmitting] = useState(false)
  const handleConfirm = useCallback(() => {
    if (submitting) return
    setSubmitting(true)
    onConfirm()
  }, [onConfirm, submitting])

  const parsed = Number(amount.replace(',', '.'))
  const payAmount = formatSwapCryptoAmount(parsed > 0 ? parsed : quote.amount_in, fromAsset)
  const receiveAmount = formatSwapCryptoAmount(quote.estimated_receive, toAsset)
  const networkLabel = SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain

  const previewSteps = useMemo(
    () => buildSwapReviewPreviewSteps(swapProcessingContext),
    [swapProcessingContext],
  )

  const techRows = useMemo(() => buildSwapTechnicalDetailRows(quote), [quote])

  const summaryRows = useMemo(() => {
    const rows: Array<{ k: string; v: string; accent?: boolean }> = [
      { k: SWAP_REVIEW_UI.youExchange, v: `${payAmount} ${fromAsset}` },
      { k: SWAP_REVIEW_UI.youReceive, v: `${receiveAmount} ${toAsset}` },
    ]
    if (quote.exchange_rate) {
      rows.push({
        k: SWAP_REVIEW_UI.exchangeRate,
        v: `1 ${fromAsset} ≈ ${formatSwapCryptoAmount(quote.exchange_rate, toAsset)} ${toAsset}`,
      })
    }
    rows.push({
      k: SWAP_REVIEW_UI.minimumReceive,
      v: `${formatSwapCryptoAmount(quote.estimated_receive_min, toAsset)} ${toAsset}`,
    })
    rows.push({ k: SWAP_REVIEW_UI.vancelianFees, v: SWAP_REVIEW_UI.vancelianFeesWaived, accent: true })
    rows.push({ k: SWAP_REVIEW_UI.networkFees, v: formatSwapFeeLine(quote) })
    rows.push({ k: SWAP_REVIEW_UI.network, v: networkLabel })
    return rows
  }, [fromAsset, networkLabel, payAmount, quote, receiveAmount, toAsset])

  return (
    <TransactionReviewPage
      title={SWAP_REVIEW_UI.title}
      layout="confirm"
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={SWAP_REVIEW_UI.modifierCta}
      primaryAction={{
        label: SWAP_REVIEW_UI.confirmCta,
        onClick: handleConfirm,
        disabled: submitting,
      }}
    >
      <p className="inv-confirm__lead">
        Vous êtes sur le point d&apos;échanger{' '}
        <b className="v-tnum">
          {payAmount} {fromAsset}
        </b>{' '}
        contre {receiveAmount} {toAsset}. Vérifiez les détails avant de lancer.
      </p>

      <div className="inv-summary inv-confirm__sum">
        {summaryRows.map((row) => (
          <div className="inv-summary__row" key={row.k}>
            <span className="k">{row.k}</span>
            <span className={`v${row.accent ? ' v--accent' : ''}`}>{row.v}</span>
          </div>
        ))}
      </div>

      <TransactionConfirmStepsPreview steps={previewSteps} />

      <TransactionTechnicalDetails rows={techRows} title={SWAP_REVIEW_UI.technicalDetailsTitle} />
    </TransactionReviewPage>
  )
}

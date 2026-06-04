'use client'

import { useMemo } from 'react'

import { TransactionConfirmStepsPreview } from '@/components/portal/transaction/TransactionConfirmStepsPreview'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { buildBundleWithdrawReviewPreviewSteps } from '@/components/portal/transaction/mappers/bundleSteps'
import {
  BUNDLE_WITHDRAW_FLOW_UI,
  BUNDLE_WITHDRAW_REVIEW_UI,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'
import { formatCryptoMoney } from '@/lib/portal/cryptoWalletFormat'

export type PortalBundleWithdrawReviewContext = {
  portfolioName: string
  entryAsset: string
  currency: string
  amountLabel: string
  fullWithdraw: boolean
  maxAmount: number
  cashCoversWithdraw: boolean
}

type Props = {
  context: PortalBundleWithdrawReviewContext
  onConfirm: () => void
  onBack: () => void
  confirmDisabled?: boolean
}

/** Confirmation retrait bundle — pas d’allocation cible, destination USDC. */
export function PortalBundleWithdrawReviewStep({
  context,
  onConfirm,
  onBack,
  confirmDisabled,
}: Props) {
  const {
    portfolioName,
    entryAsset,
    currency,
    amountLabel,
    fullWithdraw,
    maxAmount,
    cashCoversWithdraw,
  } = context

  const processingContext = useMemo(
    () => ({
      amountLabel,
      bundleLabel: portfolioName,
      activeAllocationAsset: null as string | null,
    }),
    [amountLabel, portfolioName],
  )

  const previewSteps = useMemo(
    () => buildBundleWithdrawReviewPreviewSteps(processingContext),
    [processingContext],
  )

  const summaryRows = useMemo(
    () => [
      {
        k: BUNDLE_WITHDRAW_REVIEW_UI.youWithdraw,
        v: fullWithdraw
          ? `Total (${formatCryptoMoney(maxAmount, currency)})`
          : `${amountLabel} ${entryAsset}`,
      },
      { k: BUNDLE_WITHDRAW_REVIEW_UI.bundle, v: portfolioName },
      { k: BUNDLE_WITHDRAW_REVIEW_UI.destination, v: BUNDLE_WITHDRAW_REVIEW_UI.destinationLabel },
      { k: BUNDLE_WITHDRAW_REVIEW_UI.network, v: BUNDLE_WITHDRAW_REVIEW_UI.networkLabel },
    ],
    [amountLabel, currency, entryAsset, fullWithdraw, maxAmount, portfolioName],
  )

  const lead = (
    <>
      Vous êtes sur le point de retirer{' '}
      <b className="v-tnum">{amountLabel}</b> depuis {portfolioName}. Les fonds seront versés en{' '}
      <b>{entryAsset}</b> sur Mon Trading.
    </>
  )

  return (
    <TransactionReviewPage
      title={BUNDLE_WITHDRAW_REVIEW_UI.title}
      layout="confirm"
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={BUNDLE_WITHDRAW_REVIEW_UI.modifierCta}
      primaryAction={{
        label: BUNDLE_WITHDRAW_REVIEW_UI.confirmCta,
        onClick: onConfirm,
        disabled: confirmDisabled,
      }}
    >
      <p className="inv-confirm__lead">{lead}</p>

      <p
        className={`inv-feedback${cashCoversWithdraw ? '' : ' inv-feedback--warn'}`}
        role="status"
      >
        {cashCoversWithdraw
          ? BUNDLE_WITHDRAW_FLOW_UI.cashOnlyNote
          : BUNDLE_WITHDRAW_FLOW_UI.unwindNote}
      </p>

      <div className="inv-summary inv-confirm__sum">
        {summaryRows.map((row) => (
          <div className="inv-summary__row" key={row.k}>
            <span className="k">{row.k}</span>
            <span className="v">{row.v}</span>
          </div>
        ))}
      </div>

      <TransactionConfirmStepsPreview steps={previewSteps} />

      <TransactionTechnicalDetails
        rows={[{ label: BUNDLE_WITHDRAW_REVIEW_UI.network, value: BUNDLE_WITHDRAW_REVIEW_UI.networkLabel }]}
        title={BUNDLE_WITHDRAW_REVIEW_UI.technicalDetailsTitle}
      />
    </TransactionReviewPage>
  )
}

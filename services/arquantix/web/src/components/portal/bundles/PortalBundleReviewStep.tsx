'use client'

import { useMemo } from 'react'

import {
  PortalBundleTargetAllocation,
  type PortalBundleAllocationRow,
} from '@/components/portal/bundles/PortalBundleTargetAllocation'
import { TransactionConfirmStepsPreview } from '@/components/portal/transaction/TransactionConfirmStepsPreview'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { buildBundleReviewPreviewSteps } from '@/components/portal/transaction/mappers/bundleSteps'
import { BUNDLE_REVIEW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'

export type PortalBundleReviewContext = {
  bundleTitle: string
  fundingAsset: string
  amount: number
  targetAllocationRows: PortalBundleAllocationRow[]
}

type Props = {
  context: PortalBundleReviewContext
  onConfirm: () => void
  onBack: () => void
  confirmDisabled?: boolean
}

/** Bundle invest Confirmation — allocation cible théorique + étapes (handoff InvestConfirm panier). */
export function PortalBundleReviewStep({ context, onConfirm, onBack, confirmDisabled }: Props) {
  const { bundleTitle, fundingAsset, amount, targetAllocationRows } = context
  const amountLabel = formatBundleUsdcAmount(amount)

  const processingContext = useMemo(
    () => ({
      amountLabel: `${amountLabel} ${fundingAsset}`,
      bundleLabel: bundleTitle,
      activeAllocationAsset: null as string | null,
    }),
    [amountLabel, bundleTitle, fundingAsset],
  )

  const previewSteps = useMemo(
    () => buildBundleReviewPreviewSteps(processingContext),
    [processingContext],
  )

  const techRows = useMemo(
    () => [{ label: BUNDLE_REVIEW_UI.network, value: BUNDLE_REVIEW_UI.networkLabel }],
    [],
  )

  const summaryRows = useMemo(() => {
    const rows: Array<{ k: string; v: string; accent?: boolean }> = [
      { k: BUNDLE_REVIEW_UI.youInvest, v: `${amountLabel} ${fundingAsset}` },
      { k: BUNDLE_REVIEW_UI.bundle, v: bundleTitle },
      { k: BUNDLE_REVIEW_UI.vancelianFees, v: BUNDLE_REVIEW_UI.vancelianFeesWaived, accent: true },
      { k: BUNDLE_REVIEW_UI.network, v: BUNDLE_REVIEW_UI.networkLabel },
      { k: BUNDLE_REVIEW_UI.liquidity, v: BUNDLE_REVIEW_UI.liquidityPilot },
    ]
    return rows
  }, [amountLabel, bundleTitle, fundingAsset])

  const lead = (
    <>
      Vous êtes sur le point d&apos;investir{' '}
      <b className="v-tnum">
        {amountLabel} {fundingAsset}
      </b>{' '}
      sur {bundleTitle}. Vérifiez l&apos;allocation cible avant de lancer la transaction.
    </>
  )

  return (
    <TransactionReviewPage
      title={BUNDLE_REVIEW_UI.title}
      layout="confirm"
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={BUNDLE_REVIEW_UI.modifierCta}
      primaryAction={{
        label: BUNDLE_REVIEW_UI.confirmCta,
        onClick: onConfirm,
        disabled: confirmDisabled,
      }}
    >
      <p className="inv-confirm__lead">{lead}</p>

      <PortalBundleTargetAllocation
        rows={targetAllocationRows}
        title={BUNDLE_REVIEW_UI.targetAllocation}
        className="inv-confirm__alloc"
      />

      <div className="inv-summary inv-confirm__sum">
        {summaryRows.map((row) => (
          <div className="inv-summary__row" key={row.k}>
            <span className="k">{row.k}</span>
            <span className={`v${row.accent ? ' v--accent' : ''}`}>{row.v}</span>
          </div>
        ))}
      </div>

      <TransactionConfirmStepsPreview steps={previewSteps} />

      <TransactionTechnicalDetails rows={techRows} title={BUNDLE_REVIEW_UI.technicalDetailsTitle} />
    </TransactionReviewPage>
  )
}

'use client'

import { useMemo } from 'react'

import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { BUNDLE_FLOW_UI, BUNDLE_REVIEW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import type { BundleInvestPreviewPayload } from '@/lib/portal/bundleClient'
import {
  displayBundleAssetSymbol,
  formatBundleTargetWeight,
  formatBundleUsdcAmount,
} from '@/lib/portal/bundleFormat'
import { formatBundleInvestPreviewWarnings } from '@/lib/portal/bundleInvestPreviewFormat'

export type PortalBundleReviewContext = {
  bundleTitle: string
  fundingAsset: string
  amount: number
  preview: BundleInvestPreviewPayload
}

type Props = {
  context: PortalBundleReviewContext
  onConfirm: () => void
  onBack: () => void
  confirmDisabled?: boolean
}

/** Bundle invest Review — récap + allocation, pas d’exécution (R4.5-E). */
export function PortalBundleReviewStep({ context, onConfirm, onBack, confirmDisabled }: Props) {
  const { bundleTitle, fundingAsset, amount, preview } = context
  const entryAssetLabel = preview.entry_asset_used ?? fundingAsset
  const amountLabel = formatBundleUsdcAmount(amount)

  const previewWarning = useMemo(() => {
    if (preview.preview_status === 'ok') return null
    return formatBundleInvestPreviewWarnings(preview.warnings)
  }, [preview.preview_status, preview.warnings])

  const techRows = useMemo(() => {
    const rows: Array<{ label: string; value: string }> = [
      {
        label: 'Entrée estimée',
        value: `${formatBundleUsdcAmount(preview.estimated_entry_asset_amount)} ${entryAssetLabel}`,
      },
      { label: BUNDLE_REVIEW_UI.network, value: BUNDLE_REVIEW_UI.networkLabel },
      { label: 'Statut prévisualisation', value: preview.preview_status },
    ]
    if (previewWarning) {
      rows.push({ label: BUNDLE_REVIEW_UI.previewWarningTitle, value: previewWarning })
    }
    return rows
  }, [entryAssetLabel, preview.estimated_entry_asset_amount, preview.preview_status, previewWarning])

  return (
    <TransactionReviewPage
      title={BUNDLE_REVIEW_UI.title}
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={BUNDLE_REVIEW_UI.backButton}
      primaryAction={{
        label: BUNDLE_REVIEW_UI.confirmCta,
        onClick: onConfirm,
        disabled: confirmDisabled,
      }}
    >
      <div className="inv-summary">
        <div className="inv-summary__row">
          <span className="k">{BUNDLE_REVIEW_UI.youInvest}</span>
          <span className="v">
            {amountLabel} {fundingAsset}
          </span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{BUNDLE_REVIEW_UI.bundle}</span>
          <span className="v">{bundleTitle}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{BUNDLE_REVIEW_UI.vancelianFees}</span>
          <span className="v v--accent">{BUNDLE_REVIEW_UI.vancelianFeesWaived}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{BUNDLE_REVIEW_UI.network}</span>
          <span className="v">{BUNDLE_REVIEW_UI.networkLabel}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{BUNDLE_REVIEW_UI.liquidity}</span>
          <span className="v">{BUNDLE_REVIEW_UI.liquidityPilot}</span>
        </div>
      </div>

      <div className="inv-summary">
        <p className="m-0 mb-2 font-ui text-[13px] font-medium text-v-fg">{BUNDLE_REVIEW_UI.targetAllocation}</p>
        <ul className="m-0 list-none space-y-1 p-0">
          {(preview.allocations ?? []).map((row) => {
            const label = row.asset_display?.trim() || displayBundleAssetSymbol(row.asset)
            return (
              <li
                key={`${row.asset}-${row.target_weight}`}
                className="flex justify-between gap-3 font-ui text-[13px] text-v-fg"
              >
                <span>
                  {label}{' '}
                  <span className="text-v-fg-muted">({formatBundleTargetWeight(row.target_weight)})</span>
                </span>
                <span className="shrink-0 tabular-nums text-v-fg-muted">
                  {formatBundleUsdcAmount(row.estimated_input_amount)} {entryAssetLabel}
                </span>
              </li>
            )
          })}
        </ul>
      </div>

      {preview.preview_status === 'partial' ? (
        <p className="m-0 rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 font-ui text-[13px] text-amber-950">
          {BUNDLE_FLOW_UI.partialPreviewNote}
        </p>
      ) : null}

      {techRows.length > 0 ? (
        <TransactionTechnicalDetails rows={techRows} title={BUNDLE_REVIEW_UI.technicalDetailsTitle} />
      ) : null}
    </TransactionReviewPage>
  )
}

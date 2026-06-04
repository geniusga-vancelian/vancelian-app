'use client'

import { useMemo } from 'react'

import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { LOMBARD_REVIEW_UI } from '@/components/portal/transaction/mappers/lombardReviewUiCopy'
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'

type Props = {
  recap: LombardBorrowRecap
  onConfirm: () => void
  onBack: () => void
  confirmDisabled?: boolean
}

/** Lombard borrow Review — récap avant exécution (O4, aligné TransactionReviewPage). */
export function PortalLombardBorrowReviewStep({
  recap,
  onConfirm,
  onBack,
  confirmDisabled = false,
}: Props) {
  const techRows = useMemo(
    () => [
      { label: 'Garantie', value: `${recap.guaranteeAmount} ${recap.collateral}` },
      { label: 'Produit', value: VANCELIAN_LOMBARD_V1.poweredByLabel },
      { label: 'Intégration', value: recap.marketLabel },
    ],
    [recap.collateral, recap.guaranteeAmount, recap.marketLabel],
  )

  return (
    <TransactionReviewPage
      title={LOMBARD_REVIEW_UI.title}
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={LOMBARD_REVIEW_UI.backButton}
      primaryAction={{
        label: LOMBARD_REVIEW_UI.confirmCta,
        onClick: onConfirm,
        disabled: confirmDisabled,
      }}
    >
      <div className="inv-summary">
        <div className="inv-summary__row">
          <span className="k">{LOMBARD_REVIEW_UI.youBorrow}</span>
          <span className="v">
            {recap.borrowAmountLabel} USDC
          </span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{LOMBARD_REVIEW_UI.guarantee}</span>
          <span className="v">
            {recap.guaranteeAmount} {recap.collateralLabel}
          </span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{LOMBARD_REVIEW_UI.targetLtv}</span>
          <span className="v">{recap.targetLtvPercent} %</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{LOMBARD_REVIEW_UI.safety}</span>
          <span className="v">{recap.safetyLabel}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{LOMBARD_REVIEW_UI.interest}</span>
          <span className="v">{recap.interestLabel}</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">{LOMBARD_REVIEW_UI.market}</span>
          <span className="v">{recap.marketLabel}</span>
        </div>
      </div>

      <TransactionTechnicalDetails
        rows={techRows}
        title={LOMBARD_REVIEW_UI.technicalDetailsTitle}
      />
    </TransactionReviewPage>
  )
}

'use client'

import { useMemo } from 'react'

import { TransactionConfirmStepsPreview } from '@/components/portal/transaction/TransactionConfirmStepsPreview'
import { TransactionReviewPage } from '@/components/portal/transaction/TransactionReviewPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { buildLombardReviewPreviewSteps } from '@/components/portal/transaction/mappers/lombardSteps'
import { LOMBARD_REVIEW_UI } from '@/components/portal/transaction/mappers/lombardReviewUiCopy'
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'

type Props = {
  recap: LombardBorrowRecap
  onConfirm: () => void
  onBack: () => void
  confirmDisabled?: boolean
}

/** Lombard borrow — confirmation avant exécution blockchain (handoff portfolio.html). */
export function PortalLombardBorrowReviewStep({
  recap,
  onConfirm,
  onBack,
  confirmDisabled = false,
}: Props) {
  const previewSteps = useMemo(() => buildLombardReviewPreviewSteps(recap), [recap])

  const techRows = useMemo(
    () => [
      { label: 'Garantie', value: `${recap.guaranteeAmount} ${recap.collateral}` },
      { label: 'Produit', value: VANCELIAN_LOMBARD_V1.poweredByLabel },
      { label: 'Intégration', value: recap.marketLabel },
      { label: LOMBARD_REVIEW_UI.network, value: LOMBARD_REVIEW_UI.networkLabel },
    ],
    [recap.collateral, recap.guaranteeAmount, recap.marketLabel],
  )

  const lead = (
    <>
      Vous êtes sur le point d&apos;emprunter{' '}
      <b className="v-tnum">
        {recap.borrowAmountLabel} USDC
      </b>
      . Vérifiez les étapes ci-dessous avant de lancer la transaction.
    </>
  )

  return (
    <TransactionReviewPage
      title={LOMBARD_REVIEW_UI.title}
      layout="confirm"
      onBack={onBack}
      onClose={onBack}
      backButtonLabel={LOMBARD_REVIEW_UI.modifierCta}
      primaryAction={{
        label: LOMBARD_REVIEW_UI.confirmCta,
        onClick: onConfirm,
        disabled: confirmDisabled,
      }}
    >
      <p className="inv-confirm__lead">{lead}</p>

      <TransactionConfirmStepsPreview steps={previewSteps} title={LOMBARD_REVIEW_UI.stepsTitle} />

      <section className="txn-sum inv-confirm__sum">
        <h2 className="txn-sum__title">{LOMBARD_REVIEW_UI.summaryTitle}</h2>
        <div className="txn-sum__list">
          <div className="txn-sum__row">
            <span className="txn-sum__k">{LOMBARD_REVIEW_UI.youBorrow}</span>
            <span className="txn-sum__v v-tnum">
              {recap.borrowAmountLabel} USDC
            </span>
          </div>
          <div className="txn-sum__row">
            <span className="txn-sum__k">{LOMBARD_REVIEW_UI.guarantee}</span>
            <span className="txn-sum__v v-tnum">
              {recap.guaranteeAmount} {recap.collateralLabel}
            </span>
          </div>
          <div className="txn-sum__row">
            <span className="txn-sum__k">{LOMBARD_REVIEW_UI.targetLtv}</span>
            <span className="txn-sum__v v-tnum">{recap.targetLtvLabel}</span>
          </div>
          <div className="txn-sum__row">
            <span className="txn-sum__k">{LOMBARD_REVIEW_UI.interest}</span>
            <span className="txn-sum__v">{recap.interestLabel}</span>
          </div>
          <div className="txn-sum__row">
            <span className="txn-sum__k">{LOMBARD_REVIEW_UI.market}</span>
            <span className="txn-sum__v">{recap.marketLabel}</span>
          </div>
        </div>
      </section>

      <TransactionTechnicalDetails
        rows={techRows}
        title={LOMBARD_REVIEW_UI.technicalDetailsTitle}
      />
    </TransactionReviewPage>
  )
}

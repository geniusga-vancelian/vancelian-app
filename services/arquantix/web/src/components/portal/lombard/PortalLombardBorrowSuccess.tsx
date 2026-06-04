'use client'

import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import { parseBorrowAmountInput, formatBorrowAmountFr } from '@/lib/portal/lombard/lombardBorrowUi'

type Props = {
  recap: LombardBorrowRecap
  onViewLoans: () => void
  onClose?: () => void
}

/** Lombard borrow success — délégué à TransactionResultPage (R4.5-B). */
export function PortalLombardBorrowSuccess({ recap, onViewLoans, onClose }: Props) {
  const borrowLabel =
    recap.borrowAmountLabel ||
    formatBorrowAmountFr(parseBorrowAmountInput(recap.borrowAmount), 2)

  const steps = [
    {
      name: 'Autorisation de la garantie',
      body: (
        <p className="txn-step__amount">
          Morpho autorisé à utiliser votre {recap.collateral} comme garantie.
        </p>
      ),
    },
    {
      name: 'Garantie déposée',
      body: (
        <p className="txn-step__amount">
          <span className="v-tnum">{recap.guaranteeAmount}</span> {recap.collateral} bloqués sur le marché
          Morpho.
        </p>
      ),
    },
    {
      name: 'Emprunt ouvert',
      body: (
        <p className="txn-step__amount">
          <span className="v-tnum">{borrowLabel}</span> USDC empruntés à {recap.targetLtvPercent} % de niveau
          d&apos;emprunt.
        </p>
      ),
    },
    {
      name: 'USDC reçus sur votre wallet',
      body: <p className="txn-step__amount">Disponibles immédiatement sur votre wallet Vancelian.</p>,
    },
  ]

  const summary = [
    { k: 'Montant emprunté', v: `${borrowLabel} USDC` },
    { k: 'Garantie déposée', v: `${recap.guaranteeAmount} ${recap.collateral}` },
    { k: "Niveau d'emprunt", v: `${recap.targetLtvPercent} % · ${recap.safetyLabel}` },
    { k: "Taux d'intérêt", v: recap.interestLabel },
    { k: 'Marché', v: recap.marketLabel },
  ]

  return (
    <TransactionResultPage
      variant="success"
      title="Emprunt effectué"
      lead={
        <>
          <b className="v-tnum">{borrowLabel} USDC</b> ont été crédités sur votre wallet. Votre{' '}
          {recap.collateralLabel} reste votre garantie.
        </>
      }
      steps={steps}
      summary={summary}
      note={
        <>
          <KalaiIcon name="info" size={16} className="ic" />
          Vous remboursez à votre rythme. Une alerte est envoyée si votre garantie approche du seuil de
          liquidation.
        </>
      }
      primaryAction={{
        label: 'Voir mon USDC',
        onClick: onViewLoans,
        icon: <KalaiIcon name="wallet" size={16} />,
      }}
      onClose={onClose}
    />
  )
}

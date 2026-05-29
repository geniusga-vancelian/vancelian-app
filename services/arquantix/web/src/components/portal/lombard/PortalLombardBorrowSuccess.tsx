'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import { parseBorrowAmountInput, formatBorrowAmountFr } from '@/lib/portal/lombard/lombardBorrowUi'

type Props = {
  recap: LombardBorrowRecap
  onViewLoans: () => void
  onClose?: () => void
}

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
    <div className="brw brw-succ v-card">
      {onClose ? (
        <button
          type="button"
          className="inv-head__btn brw-dismiss"
          aria-label="Fermer"
          onClick={onClose}
          style={{ width: 32 }}
        >
          <KalaiIcon name="close" size={16} />
        </button>
      ) : null}

      <div className="brw-succ__hero">
        <span className="brw-succ__badge" aria-hidden>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <h3 className="brw-succ__title">Emprunt effectué</h3>
        <p className="brw-succ__lead">
          <b className="v-tnum">{borrowLabel} USDC</b> ont été crédités sur votre wallet. Votre{' '}
          {recap.collateralLabel} reste votre garantie.
        </p>
      </div>

      <section className="txn-step brw-succ__step">
        <h2 className="txn-step__title">Étapes de votre emprunt</h2>
        <ol className="txn-step__list">
          {steps.map((step, i) => (
            <li key={step.name} className="txn-step__item">
              <span className="txn-step__badge" aria-hidden>
                {i + 1}
              </span>
              <div className="txn-step__body">
                <h3 className="txn-step__name">{step.name}</h3>
                {step.body}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="txn-sum brw-succ__sum">
        <h2 className="txn-sum__title">Récapitulatif</h2>
        <div className="txn-sum__list">
          {summary.map((row) => (
            <div className="txn-sum__row" key={row.k}>
              <span className="txn-sum__k">{row.k}</span>
              <span className="txn-sum__v v-tnum">{row.v}</span>
            </div>
          ))}
        </div>
      </section>

      <p className="brw-succ__note">
        <KalaiIcon name="info" size={14} className="ic" />
        Vous remboursez à votre rythme. Une alerte est envoyée si votre garantie approche du seuil de
        liquidation.
      </p>

      <div className="brw-foot brw-succ__foot">
        <button type="button" className="btn btn--primary btn--lg brw-foot__cta" onClick={onViewLoans}>
          <KalaiIcon name="wallet" size={16} />
          Voir mes emprunts
        </button>
      </div>
    </div>
  )
}

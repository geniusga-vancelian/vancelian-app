'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Props = {
  onContinue: () => void
  onClose?: () => void
}

const POINTS = [
  {
    icon: 'lock' as const,
    title: 'Vos cryptos restent en garantie',
    text: 'Vous déposez du Bitcoin ou de l\'Ethereum en gage sur Morpho et recevez des USDC. Vous ne vendez rien : vos cryptos restent les vôtres.',
  },
  {
    icon: 'trending-up' as const,
    title: 'Un intérêt qui rembourse votre emprunt',
    text: 'La crypto mise en gage génère un intérêt qui rembourse, petit à petit, la somme empruntée. Votre dette diminue d\'elle-même au fil du temps.',
  },
  {
    icon: 'clock' as const,
    title: 'Remboursement libre, à tout moment',
    text: 'Aucune échéance imposée. Vous remboursez tout ou partie de votre emprunt quand vous le souhaitez, sans frais.',
  },
] as const

export function PortalLombardBorrowIntro({ onContinue, onClose }: Props) {
  return (
    <div className="brw brw-intro v-card">
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

      <div className="brw-intro__head">
        <h3 className="brw__title">Avant de commencer</h3>
        <p className="brw__lead">
          L&apos;avance de liquidité vous permet d&apos;emprunter des USDC tout en gardant vos cryptos.
          Voici l&apos;essentiel à comprendre.
        </p>
      </div>

      <div className="brw-intro__points">
        {POINTS.map((p) => (
          <div className="brw-intro__point" key={p.title}>
            <span className="brw-intro__ico" aria-hidden>
              <KalaiIcon name={p.icon} size={20} />
            </span>
            <div className="brw-intro__text">
              <h4 className="brw-intro__pt-title">{p.title}</h4>
              <p className="brw-intro__pt-body">{p.text}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="brw-intro__risk" role="note" aria-label="Risques associés">
        <div className="brw-intro__risk-head">
          <span className="brw-intro__risk-ico" aria-hidden>
            <KalaiIcon name="shield-good" size={20} />
          </span>
          <h4 className="brw-intro__risk-title">Risques associés — à lire attentivement</h4>
        </div>
        <ul className="brw-intro__risk-list">
          <li>
            <b>Liquidation.</b> Si la valeur de votre garantie baisse trop, une partie de votre crypto est
            vendue automatiquement pour rembourser l&apos;emprunt. Vous la perdez définitivement.
          </li>
          <li>
            <b>Taux variable.</b> Le taux d&apos;intérêt évolue selon le marché et peut ralentir le
            remboursement automatique.
          </li>
          <li>
            <b>Volatilité.</b> Le cours du Bitcoin et de l&apos;Ethereum peut chuter fortement et rapidement.
          </li>
        </ul>
      </div>

      <div className="brw-foot brw-intro__foot">
        <button type="button" className="btn btn--primary btn--lg brw-foot__cta" onClick={onContinue}>
          J&apos;ai compris
        </button>
      </div>
    </div>
  )
}

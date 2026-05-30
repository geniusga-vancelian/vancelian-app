import { KalaiIcon } from '@/components/ui/KalaiIcon'

const POINTS = [
  {
    icon: 'lock' as const,
    title: 'Vos cryptos restent en garantie',
    text: "Vous déposez du Bitcoin ou de l'Ethereum en gage sur Morpho et recevez des USDC sur votre wallet. Vous ne vendez rien : vos cryptos restent les vôtres et continuent de suivre leur cours.",
  },
  {
    icon: 'trending-up' as const,
    title: 'Un intérêt qui rembourse votre emprunt',
    text: "La crypto mise en gage génère un intérêt qui vient rembourser, petit à petit, la somme empruntée. Votre dette diminue d'elle-même au fil du temps, sans action de votre part.",
  },
  {
    icon: 'clock' as const,
    title: 'Remboursement libre, à tout moment',
    text: 'Aucune échéance imposée. Vous pouvez rembourser tout ou partie de votre emprunt quand vous le souhaitez, sans frais ni pénalité.',
  },
] as const

/** Bloc pédagogique emprunts — handoff `.brw-explain`. */
export function AppBorrowExplainerSection() {
  return (
    <section className="brw-explain">
      <h3 className="brw-explain__title">Comment fonctionne l&apos;avance de liquidité</h3>
      <div className="brw-explain__points">
        {POINTS.map((point) => (
          <div className="brw-explain__point" key={point.title}>
            <span className="brw-explain__ico" aria-hidden="true">
              <KalaiIcon name={point.icon} size={20} />
            </span>
            <div className="brw-explain__text">
              <h4 className="brw-explain__pt-title">{point.title}</h4>
              <p className="brw-explain__pt-body">{point.text}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="brw-risk" role="note" aria-label="Risques associés">
        <div className="brw-risk__head">
          <span className="brw-risk__ico" aria-hidden="true">
            <KalaiIcon name="shield-good" size={20} />
          </span>
          <h4 className="brw-risk__title">Risques associés — à lire attentivement</h4>
        </div>
        <p className="brw-risk__lead">
          Emprunter contre vos cryptos comporte un risque de perte. Avant d&apos;ouvrir une position,
          assurez-vous de comprendre les points suivants.
        </p>
        <ul className="brw-risk__list">
          <li>
            <b>Liquidation.</b> Si la valeur de votre garantie baisse trop, une partie de votre crypto
            est automatiquement vendue pour rembourser l&apos;emprunt. Vous perdez alors définitivement
            cette part.
          </li>
          <li>
            <b>Taux variable.</b> Le taux d&apos;intérêt évolue selon le marché Morpho. Il peut augmenter
            et ralentir le remboursement automatique de votre dette.
          </li>
          <li>
            <b>Volatilité.</b> Le cours du Bitcoin et de l&apos;Ethereum peut chuter fortement et
            rapidement, rapprochant votre position du seuil de liquidation.
          </li>
        </ul>
        <p className="brw-risk__foot">
          Surveillez régulièrement votre niveau d&apos;emprunt. Une alerte vous est envoyée si votre
          garantie approche du seuil de liquidation.
        </p>
      </div>
    </section>
  )
}

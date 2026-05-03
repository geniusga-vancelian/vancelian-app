import { offerFundingTokens } from '@/components/design-system/offerFunding/tokens'

export type OfferFundingProgressBarProps = {
  /** 0–100 */
  percentage: number
  /** Couleur de remplissage (défaut : jeton DS offre). */
  color?: string
  /** Affiche la partie non financée en gris (comme l’extrait Figma `showRemaining`). */
  showRemaining?: boolean
}

/**
 * Barre horizontale 4 px, coins arrondis — extrait du DS Figma (ProgressBar).
 */
export function OfferFundingProgressBar({
  percentage,
  color = offerFundingTokens.accent,
  showRemaining = false,
}: OfferFundingProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, percentage))

  if (showRemaining) {
    return (
      <div className="flex h-1 w-full shrink-0 items-start overflow-hidden rounded-[20px]">
        <div className="h-full shrink-0 rounded-[20px]" style={{ width: `${clamped}%`, backgroundColor: color }} />
        <div
          className="h-full min-h-px min-w-px flex-[1_0_0]"
          style={{ backgroundColor: offerFundingTokens.progressRemainingMuted }}
        />
      </div>
    )
  }

  return (
    <div
      className="h-1 w-full shrink-0 overflow-hidden rounded-[20px]"
      style={{ backgroundColor: offerFundingTokens.progressTrack }}
    >
      <div className="h-full rounded-[20px]" style={{ width: `${clamped}%`, backgroundColor: color }} />
    </div>
  )
}

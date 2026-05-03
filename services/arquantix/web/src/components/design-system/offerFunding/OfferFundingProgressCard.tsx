import { cn } from '@/lib/utils'
import { offerFundingTokens } from '@/components/design-system/offerFunding/tokens'
import { OFFER_FUNDING_BLOC_CHIFFRE_PADDING_CLASS, OFFER_FUNDING_TITLE_SMALL_TYPO } from '@/components/design-system/offerFunding/offerFundingTypography'
import { OfferFundingProgressBar } from '@/components/design-system/offerFunding/OfferFundingProgressBar'

export type OfferFundingProgressCardProps = {
  className?: string
  /** 0–100 */
  percentage: number
  /** Libellé à gauche (ex. Financé / Funded). */
  fundedLabel: string
  /** Couleur d’accent (barre + texte lorsque 100 %). */
  accentColor?: string
  /** Fond de la carte. */
  background?: string
  /**
   * Comportement Figma : barre avec segment « reste » atténué quand &lt; 100 %.
   * Sinon piste grise + remplissage.
   */
  showRemaining?: boolean
}

/**
 * Carte « Bloc chiffre » / Financé — Figma Arquantix Branding `node-id=319-4776` :
 * 16px entre la ligne Financé | % et la barre ; la barre reste en bas de carte (alignement valeurs Taux/Total).
 */
export function OfferFundingProgressCard({
  className,
  percentage,
  fundedLabel,
  accentColor = offerFundingTokens.accent,
  background = offerFundingTokens.cardSurface,
  showRemaining = false,
}: OfferFundingProgressCardProps) {
  const pct = Math.min(100, Math.max(0, Math.round(percentage)))
  const textColor = !showRemaining && pct === 100 ? accentColor : '#000000'
  const labelColor = showRemaining ? '#000000' : textColor

  return (
    <div
      className={cn(
        'relative flex h-full min-h-0 w-full min-w-0 flex-col rounded-[10px]',
        className,
      )}
      style={{ backgroundColor: background }}
    >
      <div
        className={cn(
          'flex h-full min-h-0 flex-col overflow-clip rounded-[inherit]',
          OFFER_FUNDING_BLOC_CHIFFRE_PADDING_CLASS,
        )}
      >
        <div className="flex w-full shrink-0 items-center justify-between gap-4 whitespace-nowrap">
          <p className={cn('min-w-0 shrink', OFFER_FUNDING_TITLE_SMALL_TYPO)} style={{ color: labelColor }}>
            {fundedLabel}
          </p>
          <p className={cn('shrink-0 tabular-nums', OFFER_FUNDING_TITLE_SMALL_TYPO)} style={{ color: textColor }}>
            {pct}%
          </p>
        </div>
        {/* 16px — spec Figma (équivalent `gap-4` / token OFFER_FUNDING_CARD_INNER_GAP_CLASS) */}
        <div className="h-4 w-full shrink-0" aria-hidden />
        <div className="flex min-h-0 flex-1 flex-col justify-end">
          <div className="w-full shrink-0">
            <OfferFundingProgressBar percentage={pct} color={accentColor} showRemaining={showRemaining} />
          </div>
        </div>
      </div>
    </div>
  )
}

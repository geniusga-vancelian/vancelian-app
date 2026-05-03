import { cn } from '@/lib/utils'
import { offerFundingTokens } from '@/components/design-system/offerFunding/tokens'
import {
  OFFER_FUNDING_CARD_INNER_GAP_CLASS,
  OFFER_FUNDING_CARD_PADDING_CLASS,
} from '@/components/design-system/offerFunding/offerFundingTypography'
import { OfferFundingStatLabel } from '@/components/design-system/offerFunding/OfferFundingStatLabel'
import { OfferFundingStatValue } from '@/components/design-system/offerFunding/OfferFundingStatValue'

export type OfferFundingStatCardProps = {
  className?: string
  label: string
  value: string | number
  /** Fond carte (défaut jeton DS). */
  background?: string
}

/**
 * Carte Taux ou Total — libellé puis valeur avec **16px** fixes entre les deux (Figma `gap-4`).
 */
export function OfferFundingStatCard({
  className,
  label,
  value,
  background = offerFundingTokens.cardSurface,
}: OfferFundingStatCardProps) {
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
          'flex h-full min-h-0 flex-col justify-start',
          OFFER_FUNDING_CARD_INNER_GAP_CLASS,
          OFFER_FUNDING_CARD_PADDING_CLASS,
        )}
      >
        <OfferFundingStatLabel>{label}</OfferFundingStatLabel>
        <OfferFundingStatValue>{value}</OfferFundingStatValue>
      </div>
    </div>
  )
}

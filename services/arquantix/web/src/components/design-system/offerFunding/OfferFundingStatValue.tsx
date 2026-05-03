import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'
import {
  OFFER_FUNDING_TITLE_LARGE_TYPO,
  OFFER_FUNDING_TITLE_SMALL_TYPO,
} from '@/components/design-system/offerFunding/offerFundingTypography'

export type OfferFundingStatValueProps = {
  children: ReactNode
  size?: 'default' | 'large'
}

/**
 * Valeur chiffrée — Figma « Title small » (24px Heavy 800) ou variante 32px.
 */
export function OfferFundingStatValue({ children, size = 'default' }: OfferFundingStatValueProps) {
  return (
    <div className="relative flex w-full shrink-0 justify-start">
      <p
        className={cn(
          'relative min-h-px min-w-0 max-w-full text-left not-italic tabular-nums',
          size === 'large' ? OFFER_FUNDING_TITLE_LARGE_TYPO : OFFER_FUNDING_TITLE_SMALL_TYPO,
        )}
      >
        {children}
      </p>
    </div>
  )
}

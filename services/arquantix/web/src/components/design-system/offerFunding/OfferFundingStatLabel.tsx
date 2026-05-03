import type { ReactNode } from 'react'

import { OFFER_FUNDING_PARAGRAPH_LARGE_TYPO } from '@/components/design-system/offerFunding/offerFundingTypography'

export type OfferFundingStatLabelProps = {
  children: ReactNode
}

/**
 * Libellé carte stat — Figma « Paragraph Large » (18px Roman 400, interligne 160 %).
 */
export function OfferFundingStatLabel({ children }: OfferFundingStatLabelProps) {
  return (
    <p className={`w-full shrink-0 ${OFFER_FUNDING_PARAGRAPH_LARGE_TYPO}`}>{children}</p>
  )
}

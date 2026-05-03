'use client'

import { OfferFundingStatsRow } from '@/components/design-system/offerFunding'
import { vaultCommonCta } from '@/lib/i18n/vaultCommonCta'

export type FundingModuleProps = {
  /** 0–100 — barre + pourcentage affiché */
  fundedPercent: number
  /** Ex. `12,50%` ou `12.50%` */
  rateDisplay: string
  /** Montant cible formaté (ex. `5 000 000`) */
  totalDisplay: string
  locale: string
  className?: string
}

function labels(locale: string) {
  return {
    funded: vaultCommonCta(locale, 'funding_funded'),
    rate: vaultCommonCta(locale, 'funding_rate'),
    total: vaultCommonCta(locale, 'funding_total'),
  }
}

/**
 * Bandeau financement — page détail offre.
 * Composé à partir du DS (`OfferFundingStatsRow`) aligné sur l’extrait Figma « Funding / StatCard ».
 */
export function FundingModule({
  fundedPercent,
  rateDisplay,
  totalDisplay,
  locale,
  className,
}: FundingModuleProps) {
  const L = labels(locale)

  return (
    <OfferFundingStatsRow
      fundedPercent={fundedPercent}
      fundedLabel={L.funded}
      rateLabel={L.rate}
      totalLabel={L.total}
      rateDisplay={rateDisplay}
      totalDisplay={totalDisplay}
      className={className}
    />
  )
}

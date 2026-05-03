import { cn } from '@/lib/utils'
import { OfferFundingProgressCard } from '@/components/design-system/offerFunding/OfferFundingProgressCard'
import { OfferFundingStatCard } from '@/components/design-system/offerFunding/OfferFundingStatCard'

export type OfferFundingStatsRowProps = {
  fundedPercent: number
  fundedLabel: string
  rateLabel: string
  totalLabel: string
  rateDisplay: string
  totalDisplay: string
  /** Barre style Figma « reste » visible (recommandé si &lt; 100 %). */
  showRemainingBar?: boolean
  className?: string
}

/**
 * Grille 4 colonnes : carte Financé sur 2 colonnes, puis Taux, puis Total (extrait App Figma).
 */
export function OfferFundingStatsRow({
  fundedPercent,
  fundedLabel,
  rateLabel,
  totalLabel,
  rateDisplay,
  totalDisplay,
  showRemainingBar,
  className,
}: OfferFundingStatsRowProps) {
  const pct = Math.min(100, Math.max(0, Math.round(fundedPercent)))
  const showRemaining = showRemainingBar ?? pct < 100

  return (
    <div
      className={cn(
        'grid size-full grid-cols-1 gap-2 md:grid-cols-4 md:items-stretch md:gap-x-2 md:gap-y-2',
        className,
      )}
    >
      <div className="flex min-h-0 min-w-0 md:col-span-2 md:col-start-1 md:row-start-1">
        <OfferFundingProgressCard
          className="min-h-0 flex-1"
          percentage={pct}
          fundedLabel={fundedLabel}
          showRemaining={showRemaining}
        />
      </div>
      <div className="flex min-h-0 min-w-0 md:col-start-3 md:row-start-1">
        <OfferFundingStatCard className="flex-1" label={rateLabel} value={rateDisplay} />
      </div>
      <div className="flex min-h-0 min-w-0 md:col-start-4 md:row-start-1">
        <OfferFundingStatCard className="flex-1" label={totalLabel} value={totalDisplay} />
      </div>
    </div>
  )
}

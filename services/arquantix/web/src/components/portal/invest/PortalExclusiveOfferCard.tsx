'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { OfferFundingProgressBar } from '@/components/design-system/offerFunding/OfferFundingProgressBar'
import { Button } from '@/components/ui/button'
import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'
import { cn } from '@/lib/utils'

type Props = {
  offer: PortalExclusiveOffer
  className?: string
}

export function PortalExclusiveOfferCard({ offer, className }: Props) {
  return (
    <article
      className={cn(
        'flex h-full flex-col overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle',
        className,
      )}
    >
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-v-fg-05">
        {offer.coverUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={offer.coverUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-ui text-[13px] text-v-fg-muted">
            Vancelian
          </div>
        )}
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <span className="rounded-v-tag bg-white/95 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-v-fg">
            {offer.category}
          </span>
          <span className="rounded-v-tag bg-v-fg px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-white">
            {offer.isFunded ? 'Funded' : 'Live'}
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4 sm:p-5">
        <div className="min-w-0">
          <h3 className="m-0 line-clamp-2 font-ui text-[18px] font-semibold leading-snug text-v-fg">
            {offer.title}
          </h3>
          {offer.description ? (
            <p className="mt-2 mb-0 line-clamp-2 font-ui text-[14px] leading-relaxed text-v-fg-body">
              {offer.description}
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-3 font-ui text-[13px]">
          <div>
            <p className="m-0 text-v-fg-muted">Raised</p>
            <p className="m-0 mt-0.5 font-semibold text-v-fg">{offer.raisedLabel}</p>
          </div>
          <div>
            <p className="m-0 text-v-fg-muted">Investors</p>
            <p className="m-0 mt-0.5 font-semibold text-v-fg">{offer.investorsCount}</p>
          </div>
          <div>
            <p className="m-0 text-v-fg-muted">Target APR</p>
            <p className="m-0 mt-0.5 font-semibold text-v-green">{offer.apyLabel}</p>
          </div>
          <div>
            <p className="m-0 text-v-fg-muted">Target</p>
            <p className="m-0 mt-0.5 font-semibold text-v-fg">{offer.targetLabel}</p>
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between font-ui text-[13px] font-medium text-v-fg">
            <span>Total funding</span>
            <span>{Math.round(offer.progressPct)}%</span>
          </div>
          <OfferFundingProgressBar percentage={offer.progressPct} color="var(--v-green)" />
        </div>

        <Button type="button" className="mt-auto w-full" asChild>
          <PortalNavLink href={offer.href}>Invest</PortalNavLink>
        </Button>
      </div>
    </article>
  )
}

'use client'

import { PortalExclusiveOfferCard } from '@/components/portal/invest/PortalExclusiveOfferCard'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'

type Props = {
  offers: PortalExclusiveOffer[]
  title?: string
  emptyMessage?: string
}

export function PortalExclusiveOffersSection({
  offers,
  title = 'Exclusive offers',
  emptyMessage,
}: Props) {
  return (
    <section id="exclusive-offers" className="flex scroll-mt-24 flex-col gap-4">
      <PortalSectionHeading title={title} />
      {offers.length === 0 ? (
        emptyMessage ? (
          <p className="m-0 font-ui text-[14px] text-v-fg-muted">{emptyMessage}</p>
        ) : null
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {offers.map((offer) => (
            <PortalExclusiveOfferCard key={offer.id} offer={offer} />
          ))}
        </div>
      )}
    </section>
  )
}

'use client'

import { Carousel, CarouselContent, CarouselItem } from '@/components/ui/carousel'
import { PortalExclusiveOfferCard } from '@/components/portal/invest/PortalExclusiveOfferCard'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'
import { cn } from '@/lib/utils'

type Props = {
  offers: PortalExclusiveOffer[]
}

export function PortalExclusiveOffersSection({ offers }: Props) {
  if (offers.length === 0) return null

  const multi = offers.length > 1

  return (
    <section className="flex flex-col gap-4">
      <PortalSectionHeading title="What's Hot" />
      <Carousel
        opts={{ align: 'start', containScroll: 'trimSnaps', dragFree: true }}
        className="w-full min-w-0"
      >
        <CarouselContent className={cn(multi ? '-ml-3 lg:-ml-4' : '!ml-0')}>
          {offers.map((offer) => (
            <CarouselItem
              key={offer.id}
              className={cn(
                'min-h-0 shrink-0',
                multi ? 'basis-[92%] pl-3 sm:basis-[78%] lg:basis-[420px] lg:pl-4' : '!basis-full !pl-0',
              )}
            >
              <PortalExclusiveOfferCard offer={offer} />
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>
    </section>
  )
}

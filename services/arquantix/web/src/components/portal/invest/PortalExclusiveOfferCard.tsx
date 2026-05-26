'use client'

import { Banknote, CalendarDays, Home, Users } from 'lucide-react'

import { AppExclusiveOfferCard } from '@/components/design-system/app/AppExclusiveOfferCard'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'
import { cn } from '@/lib/utils'

type Props = {
  offer: PortalExclusiveOffer
  className?: string
}

function formatDurationMonths(months: number | null): string | null {
  if (months == null || months <= 0) return null
  return `${months}M`
}

export function PortalExclusiveOfferCard({ offer, className }: Props) {
  const durationLabel = formatDurationMonths(offer.durationMonths)
  const trailingChipLabel = durationLabel ?? (offer.apyLabel !== '—' ? offer.apyLabel : offer.targetLabel)

  const chips = [
    {
      key: 'investors',
      label: String(offer.investorsCount),
      icon: <Users aria-hidden />,
    },
    {
      key: 'raised',
      label: offer.raisedLabel,
      icon: <Banknote aria-hidden />,
      progressPct: offer.progressPct,
    },
    {
      key: 'meta',
      label: trailingChipLabel,
      icon: <CalendarDays aria-hidden />,
    },
  ]

  return (
    <AppExclusiveOfferCard
      className={cn(className)}
      coverImageUrl={offer.coverUrl}
      imageSeed={offer.id}
      category={offer.category}
      categoryIcon={<Home aria-hidden />}
      chips={chips}
      title={offer.title}
      description={offer.description || offer.subtitle || undefined}
      ctaLabel={offer.isFunded ? 'View' : 'Invest'}
      ctaSlot={
        <PortalNavLink
          href={offer.href}
          className="inline-flex h-11 shrink-0 items-center justify-center rounded-full bg-v-fg px-[22px] font-ui text-[14px] font-semibold text-white no-underline transition-opacity hover:opacity-90"
        >
          {offer.isFunded ? 'View' : 'Invest'}
        </PortalNavLink>
      }
    />
  )
}

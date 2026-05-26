'use client'

import { AppActuCard } from '@/components/design-system/app/AppActuCard'
import { AppFlashCard } from '@/components/design-system/app/AppFlashCard'
import { PortalNavLink } from '@/components/portal/PortalNavLink'

type Props = {
  href: string
  title: string
  meta: string
  coverUrl?: string
}

/** Carte article DS preview/26 — Actu (image) ou Flash (texte). */
export function PortalFeaturedArticleCard({ href, title, meta, coverUrl }: Props) {
  const linkProps = {
    href,
    title,
    meta,
    LinkComponent: PortalNavLink,
  }

  if (coverUrl?.trim()) {
    return <AppActuCard {...linkProps} imageUrl={coverUrl.trim()} />
  }

  return <AppFlashCard {...linkProps} />
}

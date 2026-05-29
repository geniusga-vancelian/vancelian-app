'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { formatAcademyReadTime } from '@/lib/portal/academyFormat'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

type Props = {
  items: PortalAcademyArticle[]
  title?: string
}

/** Sidebar highlighted — handoff `.acd-feat`. */
export function PortalAcademyFeaturedList({
  items,
  title = 'Featured',
}: Props) {
  if (items.length === 0) return null

  return (
    <div className="acd-feat">
      <div className="acd-feat__eyebrow">{title}</div>
      <div className="acd-feat__list">
        {items.map((article) => (
          <PortalNavLink key={article.id} href={article.href} className="acd-feat__row no-underline">
            <span
              className="acd-feat__thumb"
              style={article.coverUrl ? { backgroundImage: `url(${article.coverUrl})` } : undefined}
              aria-hidden
            />
            <span className="acd-feat__body">
              <span className="acd-feat__title">{article.title}</span>
              <span className="acd-feat__meta">
                <KalaiIcon name="clock" size={16} />
                {formatAcademyReadTime(article.readingTime)}
              </span>
            </span>
          </PortalNavLink>
        ))}
      </div>
    </div>
  )
}

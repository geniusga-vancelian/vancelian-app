'use client'

import { PortalAcademyCategoryChip } from '@/components/portal/academy/PortalAcademyCategoryChip'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { academySectionLabel, formatAcademyReadTime } from '@/lib/portal/academyFormat'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

type Props = {
  article: PortalAcademyArticle
}

/** Carte article récente — handoff `.acd-rc`. */
export function PortalAcademyArticleCard({ article }: Props) {
  const categoryLabel = article.categoryLabel ?? academySectionLabel(article)

  return (
    <PortalNavLink href={article.href} className="acd-rc no-underline">
      <span
        className="acd-rc__media"
        style={article.coverUrl ? { backgroundImage: `url(${article.coverUrl})` } : undefined}
        aria-hidden
      />
      <span className="acd-rc__body">
        <span className="acd-rc__tags">
          <PortalAcademyCategoryChip label={categoryLabel} tone={article.categoryTone} />
        </span>
        <span className="acd-rc__title">{article.title}</span>
        {article.standfirst ? <span className="acd-rc__excerpt">{article.standfirst}</span> : null}
        <span className="acd-rc__meta">
          <KalaiIcon name="clock" size={12} />
          {formatAcademyReadTime(article.readingTime)}
        </span>
      </span>
    </PortalNavLink>
  )
}

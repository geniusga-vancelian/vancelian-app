'use client'

import { PortalAcademyCategoryChip } from '@/components/portal/academy/PortalAcademyCategoryChip'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  academySectionLabel,
  formatAcademyReadTime,
} from '@/lib/portal/academyFormat'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

type Props = {
  article: PortalAcademyArticle
}

/** Hero à la une — handoff `.acd-hero`. */
export function PortalAcademyHero({ article }: Props) {
  const categoryLabel = article.categoryLabel ?? academySectionLabel(article)

  return (
    <PortalNavLink href={article.href} className="acd-hero no-underline">
      <div
        className="acd-hero__media"
        style={article.coverUrl ? { backgroundImage: `url(${article.coverUrl})` } : undefined}
        aria-hidden
      />
      <div className="acd-hero__body">
        <div className="acd-hero__tags">
          <PortalAcademyCategoryChip label={categoryLabel} tone={article.categoryTone} />
          <span className="acd-hero__section">{academySectionLabel(article)}</span>
        </div>
        <h1 className="acd-hero__title">{article.title}</h1>
        {article.standfirst ? <p className="acd-hero__excerpt">{article.standfirst}</p> : null}
        <div className="acd-hero__meta">
          <span>By {article.authorName}</span>
          <span className="acd-hero__meta-sep" aria-hidden>
            ·
          </span>
          <span className="acd-hero__meta-time">
            <KalaiIcon name="clock" size={16} />
            {formatAcademyReadTime(article.readingTime)}
          </span>
        </div>
      </div>
    </PortalNavLink>
  )
}

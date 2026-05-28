'use client'

import { PortalAcademyCategoryChip } from '@/components/portal/academy/PortalAcademyCategoryChip'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { formatAcademyReadTime } from '@/lib/portal/academyFormat'
import { authorInitials } from '@/lib/portal/portalArticleFormat'
import type { AppNewsCategoryDot } from '@/components/design-system/app/AppNewsStackedList'

type Props = {
  title: string
  standfirst: string | null
  authorName: string
  coverUrl: string | null
  publishedAt: Date
  locale: string
  readingTime: number
  categoryLabel: string
  sectionLabel: string
  categoryTone: AppNewsCategoryDot
}

/** En-tête article — handoff `.art-hero`. */
export function PortalArticleHero({
  title,
  standfirst,
  authorName,
  coverUrl,
  publishedAt,
  locale,
  readingTime,
  categoryLabel,
  sectionLabel,
  categoryTone,
}: Props) {
  return (
    <header className="art-hero">
      <div className="art-hero__tags">
        <PortalAcademyCategoryChip label={categoryLabel} tone={categoryTone} />
        <span className="art-hero__section">{sectionLabel}</span>
      </div>
      <h1 className="art-hero__title">{title}</h1>
      {standfirst ? <p className="art-hero__lede">{standfirst}</p> : null}
      <div className="art-hero__meta">
        <span className="art-hero__author">
          <span className="art-hero__author-avt" aria-hidden>
            <span className="art-hero__author-mono">{authorInitials(authorName)}</span>
          </span>
          Par {authorName}
        </span>
        <span className="art-hero__meta-sep" aria-hidden>
          ·
        </span>
        <span className="art-hero__meta-time">
          <KalaiIcon name="clock" size={16} />
          {formatAcademyReadTime(readingTime)}
        </span>
        <span className="art-hero__meta-sep" aria-hidden>
          ·
        </span>
        <span className="art-hero__meta-date">{formatArticleDateShort(publishedAt, locale)}</span>
      </div>
      {coverUrl ? (
        <figure className="art-hero__cover">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={coverUrl} alt="" />
        </figure>
      ) : null}
    </header>
  )
}

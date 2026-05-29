'use client'

import { useMemo } from 'react'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalAcademyCategoryChip } from '@/components/portal/academy/PortalAcademyCategoryChip'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { academySectionLabel, formatAcademyReadTime } from '@/lib/portal/academyFormat'
import type { PortalAcademyArticle, PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
import { buildAcademyHubCatalog } from '@/lib/portal/academyHubTabs'
import { portalAcademyHubRoute } from '@/lib/portal/portalArticleRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

const ACADEMY_CACHE_KEY = 'portal:academy:v5'

type Props = {
  currentSlug: string
}

function collectRelatedArticles(
  payload: PortalAcademyHubPayload,
  currentSlug: string,
): PortalAcademyArticle[] {
  const candidates = [
    ...(payload.featured ? [payload.featured] : []),
    ...payload.highlighted,
    ...buildAcademyHubCatalog(payload),
  ]

  const seen = new Set<string>()
  const related: PortalAcademyArticle[] = []

  for (const article of candidates) {
    if (seen.has(article.id)) continue
    seen.add(article.id)
    if (article.slug === currentSlug) continue
    related.push(article)
    if (related.length >= 4) break
  }

  return related
}

/** Articles similaires — handoff `.art-rel`. */
export function PortalArticleRelatedSection({ currentSlug }: Props) {
  const { data } = usePortalCachedScreen<PortalAcademyHubPayload>({
    cacheKey: ACADEMY_CACHE_KEY,
    url: '/api/portal/academy',
    ttlMs: 120_000,
    errorMessage: 'Unable to load related articles.',
  })

  const items = useMemo(
    () => (data ? collectRelatedArticles(data, currentSlug) : []),
    [currentSlug, data],
  )

  if (items.length === 0) return null

  return (
    <section className="art-rel">
      <AppSectionHeader
        title="Read more"
        size="md"
        moreHref={portalAcademyHubRoute()}
        moreLabel="All articles"
      />
      <div className="art-rel__grid">
        {items.map((article) => {
          const categoryLabel = article.categoryLabel ?? academySectionLabel(article)
          return (
            <PortalNavLink key={article.id} href={article.href} className="art-rel__card">
              <span
                className="art-rel__media"
                style={article.coverUrl ? { backgroundImage: `url(${article.coverUrl})` } : undefined}
                aria-hidden
              />
              <span className="art-rel__body">
                <span className="art-rel__tags">
                  <PortalAcademyCategoryChip label={categoryLabel} tone={article.categoryTone} />
                </span>
                <span className="art-rel__title">{article.title}</span>
                <span className="art-rel__meta">
                  <KalaiIcon name="clock" size={16} />
                  {formatAcademyReadTime(article.readingTime)}
                </span>
              </span>
            </PortalNavLink>
          )
        })}
      </div>
    </section>
  )
}

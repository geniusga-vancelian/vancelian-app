'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

type Props = {
  featured: PortalAcademyArticle
  highlighted: PortalAcademyArticle[]
  highlightedTitle?: string
  locale?: string
}

function articleMeta(article: PortalAcademyArticle, locale: string): string {
  const parts: string[] = []
  if (article.authorName) parts.push(article.authorName)
  if (article.publishedAt) {
    parts.push(formatArticleDateShort(new Date(article.publishedAt), locale))
  }
  parts.push(`${article.readingTime} min read`)
  return parts.join(' · ')
}

function FeaturedCover({ article }: { article: PortalAcademyArticle }) {
  if (article.coverUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={article.coverUrl} alt={article.title} className="academy-hero__cover-img" />
    )
  }
  return (
    <div className="academy-hero__cover-placeholder">
      <KalaiIcon name="photo" size={32} className="opacity-50" aria-hidden />
    </div>
  )
}

function HighlightedThumb({ article }: { article: PortalAcademyArticle }) {
  if (article.coverUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={article.coverUrl} alt="" className="academy-hero__thumb-img" />
    )
  }
  return (
    <div className="academy-hero__thumb-placeholder">
      <KalaiIcon name="photo" size={20} className="opacity-50" aria-hidden />
    </div>
  )
}

/** Hero Academy — à la une (gauche) + highlighted (droite), grammaire DS portail. */
export function PortalAcademyFeaturedHero({
  featured,
  highlighted,
  highlightedTitle = 'Highlighted',
  locale = 'fr',
}: Props) {
  return (
    <section className="academy-hero" aria-label="Featured news">
      <PortalNavLink href={featured.href} className="academy-hero__featured">
        <div className="academy-hero__cover">
          <FeaturedCover article={featured} />
          <div className="academy-hero__cover-gradient" aria-hidden />
        </div>
        <div className="academy-hero__featured-body">
          <h2 className="academy-hero__featured-title">{featured.title}</h2>
          {featured.standfirst ? (
            <p className="academy-hero__featured-standfirst">{featured.standfirst}</p>
          ) : null}
          <p className="academy-hero__featured-meta">{articleMeta(featured, locale)}</p>
        </div>
      </PortalNavLink>

      {highlighted.length > 0 ? (
        <aside className="academy-hero__sidebar">
          <h3 className="academy-hero__sidebar-title">{highlightedTitle}</h3>
          <ul className="academy-hero__highlighted-list">
            {highlighted.map((article, index) => (
              <li key={article.id}>
                <PortalNavLink href={article.href} className="academy-hero__highlighted-item">
                  <div className="academy-hero__thumb">
                    <HighlightedThumb article={article} />
                  </div>
                  <div className="academy-hero__highlighted-body">
                    <h4 className="academy-hero__highlighted-title">{article.title}</h4>
                    {article.standfirst ? (
                      <p className="academy-hero__highlighted-standfirst">{article.standfirst}</p>
                    ) : null}
                  </div>
                </PortalNavLink>
                {index < highlighted.length - 1 ? (
                  <div className="academy-hero__divider" aria-hidden />
                ) : null}
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
    </section>
  )
}

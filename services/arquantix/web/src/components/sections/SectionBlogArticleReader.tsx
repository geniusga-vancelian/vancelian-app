import Link from 'next/link'
import { getLocaleOrDefault } from '@/config/locales'
import type { PublicArticle } from '@/lib/blog/getPublicArticle'
import { buildArticleBlockElements, DocumentAttachmentRow } from '@/components/blog/ArticleBlockStream'
import { TableOfContents } from '@/components/blog/TableOfContents'
import { ArticleCarousel } from '@/components/blog/ArticleCarousel'
import { SectionShareSm } from '@/components/sections/SectionShareSm'
import { publicArticlePageUrl } from '@/lib/blog/articlePublicPageUrl'
import { getDateLabels, formatArticleDate, formatArticleDateShort } from '@/lib/blog/formatDates'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { cn } from '@/lib/utils'
import {
  CategoryPill,
  ParagraphLargeBold,
  SectionTitle,
  categoryPillDotPalette,
  figmaDsParagraphClassName,
  figmaDsColors,
} from '@/components/design-system/extracted'
import { HERO_NAV_BLEND_ANCHOR_ID } from '@/hooks/useHeroSecondaryNavBlend'

function editorialPill(article: PublicArticle, locale: string): string {
  if (article.articleType === 'ANALYSIS') return siteCommonCta(locale, 'blog_segment_analysis')
  if (article.isCompanyNews) return siteCommonCta(locale, 'blog_segment_company_news')
  return siteCommonCta(locale, 'blog_segment_market_news')
}

/** Modèle CMS (readingTimeLabel) : `{{minutes}}` ou `{{count}}` = nombre calculé. Sinon repli : « n + minRead » (i18n). */
function formatReadingTimeDisplay(
  minutes: number,
  template: string | undefined,
  minReadFallback: string,
): string {
  const t = template?.trim()
  if (t) {
    return t
      .replace(/\{\{minutes\}\}/gi, String(minutes))
      .replace(/\{\{count\}\}/gi, String(minutes))
  }
  return `${minutes} ${minReadFallback}`
}

export interface SectionBlogArticleReaderProps {
  blogLabel?: string
  tocTitle?: string
  showToc?: boolean
  tocMinHeadings?: number
  showDocuments?: boolean
  documentsTitle?: string
  /** Texte durée de lecture (traduisible). `{{minutes}}` / `{{count}}` = nombre. Vide = i18n système. */
  readingTimeLabel?: string
  /** Préfixe type « Par » avant l’auteur (désactivé par défaut). */
  showAuthorByPrefix?: boolean
  /** Texte du préfixe auteur (traduisible). Vide = libellé site (« Par » / « By »). */
  authorPrefixLabel?: string
  /** Afficher la date de mise à jour (désactivé par défaut). */
  showUpdatedDate?: boolean
  locale: string
  blogArticle?: PublicArticle | null
  /** Données section CMS `share_sm` (injectées depuis la page article). */
  shareSmData?: Record<string, unknown> | null
  /** Fil « Blog › … » sous le menu. Défaut true sur le gabarit article. */
  showBreadcrumb?: boolean
}

export function SectionBlogArticleReader({
  blogLabel,
  tocTitle,
  showToc = true,
  tocMinHeadings = 3,
  showDocuments = true,
  documentsTitle,
  readingTimeLabel,
  showAuthorByPrefix = false,
  authorPrefixLabel,
  showUpdatedDate = false,
  locale,
  blogArticle: article,
  shareSmData,
  showBreadcrumb = true,
}: SectionBlogArticleReaderProps) {
  if (!article) {
    return null
  }
  const loc = getLocaleOrDefault(locale)
  const blogPath = `/${loc}/blog`
  const dateLabels = getDateLabels(loc)
  const readingTime = calculateReadingTime(article.blocks)
  const { elements, headings } = buildArticleBlockElements(article.blocks)
  /**
   * On affiche uniquement la **date de création** de l'article (timestamp Prisma
   * `createdAt`). La date de publication (`publishedAt`) et la date de mise à
   * jour (`updatedAt`) ne sont plus exposées dans le hero — choix produit
   * (cf. ticket d'avril 2026). La logique `showUpdatedDate` reste évaluable
   * pour rétrocompatibilité (option masquée dans l'admin, défaut `false`).
   */
  const createdDate = new Date(article.createdAt)
  const updatedDate = new Date(article.updatedAt)
  const showUpdated = updatedDate.getTime() - createdDate.getTime() > 60000
  const shareUrlResolved = publicArticlePageUrl(loc, article.slug)

  const blog = blogLabel?.trim() || siteCommonCta(loc, 'blog_default_title')
  const articleTitle = article.i18n.title
  const toc = tocTitle?.trim() || siteCommonCta(loc, 'article_in_this_article')
  const docsTitle = documentsTitle?.trim() || siteCommonCta(loc, 'article_documents')
  const readingTimeText = formatReadingTimeDisplay(
    readingTime,
    readingTimeLabel,
    dateLabels.minRead,
  )

  const showSegmentPill = !article.categories || article.categories.length === 0

  /** Même règle que `TableOfContents` : sommaire affiché seulement si assez de titres. */
  const articleNavVisible = showToc && headings.length >= tocMinHeadings

  const docs = Array.isArray(article.documents)
    ? (article.documents as { url?: string; title?: string }[]).filter((d) => d?.url)
    : []

  const heroBackground = figmaDsColors.neutral.gray100
  const heroTitleColor = figmaDsColors.neutral.gray900
  const heroMetaMuted = 'text-[#62656e]'

  return (
    <div>
      {/* Hero sous le header global : remonte jusqu'en haut de l'écran. */}
      <div
        id="blog-hero"
        className="-mt-20 md:-mt-24"
        style={{ backgroundColor: heroBackground }}
      >
        <div className="mx-auto max-w-7xl px-4 pb-10 pt-24 sm:px-6 sm:pt-28 lg:px-8 lg:pb-14">
          {showBreadcrumb ? (
            <nav
              className="mb-6 text-[12px] text-[#62656e] md:mb-8"
              aria-label={siteCommonCta(loc, 'breadcrumb_aria')}
            >
              <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <li>
                  <Link href={blogPath} className="text-[#62656e] transition hover:text-black">
                    {blog}
                  </Link>
                </li>
                <li aria-hidden>›</li>
                <li className="line-clamp-1 text-[#62656e]">{articleTitle}</li>
              </ol>
            </nav>
          ) : null}

          <div
            className="grid items-start gap-8 lg:grid-cols-2 lg:items-center lg:gap-10 xl:gap-12"
            data-name="Article hero"
          >
            <div className="min-w-0">
              <div className="mb-4 flex flex-wrap gap-2">
                {article.categories && article.categories.length > 0
                  ? article.categories.map((c, i) => (
                      <CategoryPill
                        key={c.id}
                        label={c.label}
                        dotClassName={categoryPillDotPalette[i % categoryPillDotPalette.length]}
                      />
                    ))
                  : null}
                {showSegmentPill ? (
                  <CategoryPill label={editorialPill(article, loc)} />
                ) : null}
              </div>

              <SectionTitle
                id={HERO_NAV_BLEND_ANCHOR_ID}
                as="h1"
                size="module"
                align="left"
                color={heroTitleColor}
                className="!text-left"
              >
                {articleTitle}
              </SectionTitle>
              {article.i18n.standfirst ? (
                <ParagraphLargeBold color="#62656e" className="mt-4 max-w-[46rem] text-left">
                  {article.i18n.standfirst}
                </ParagraphLargeBold>
              ) : null}

              <div
                className={cn(
                  figmaDsParagraphClassName,
                  'not-italic mt-6 flex w-full max-w-full flex-wrap items-center gap-x-3 gap-y-2',
                  heroMetaMuted,
                )}
                data-name="Article meta"
              >
                <span>
                  {showAuthorByPrefix ? (
                    <>
                      {authorPrefixLabel?.trim() || siteCommonCta(loc, 'article_by_author')}{' '}
                    </>
                  ) : null}
                  <span className="font-ui font-semibold font-extrabold text-black">
                    {article.authorName}
                  </span>
                  {article.authorRole ? (
                    <span className="font-ui font-normal font-normal text-[#62656e]">
                      {' '}
                      · {article.authorRole}
                    </span>
                  ) : null}
                </span>
                <span className="hidden h-3 w-px bg-black/15 sm:inline" aria-hidden />
                <span className="inline-flex items-center gap-1.5">
                  <svg
                    className="h-3.5 w-3.5 shrink-0 text-[#62656e]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span>{readingTimeText}</span>
                </span>
                <span className="hidden h-3 w-px bg-black/15 sm:inline" aria-hidden />
                <time
                  className="text-[#62656e]"
                  dateTime={createdDate.toISOString()}
                  title={formatArticleDate(createdDate, loc)}
                >
                  {formatArticleDateShort(createdDate, loc)}
                  {showUpdatedDate && showUpdated
                    ? ` · ${dateLabels.updated} ${formatArticleDateShort(updatedDate, loc)}`
                    : ''}
                </time>
              </div>
            </div>

            <div className="flex min-w-0 flex-col justify-center self-stretch">
            {article.i18n.coverTitle ? (
              <p className="mb-2 text-[13px] text-[#62656e]">{article.i18n.coverTitle}</p>
            ) : null}
            {article.videoUrl ? (
              <div className="relative aspect-[3/2] w-full overflow-hidden rounded-[14px] bg-black">
                <iframe
                  src={
                    article.videoUrl.includes('youtube.com') || article.videoUrl.includes('youtu.be')
                      ? `https://www.youtube.com/embed/${
                          article.videoUrl.includes('watch?v=')
                            ? article.videoUrl.split('watch?v=')[1].split('&')[0]
                            : article.videoUrl.split('/').pop()
                        }`
                      : article.videoUrl.includes('vimeo.com')
                        ? `https://player.vimeo.com/video/${article.videoUrl.split('/').pop()}`
                        : article.videoUrl
                  }
                  className="h-full w-full"
                  allowFullScreen
                  title={articleTitle}
                />
              </div>
            ) : article.galleryUrls && article.galleryUrls.length > 0 ? (
              <div className="w-full overflow-hidden rounded-[14px]">
                <ArticleCarousel
                  frameClassName="aspect-[3/2]"
                  images={[article.coverUrl, ...article.galleryUrls].filter(Boolean)}
                  title={articleTitle}
                />
              </div>
            ) : article.coverUrl ? (
              <div className="relative aspect-[3/2] w-full max-w-full overflow-hidden rounded-[14px] bg-[#d9e2f8]">
                <img
                  src={article.coverUrl}
                  alt={articleTitle}
                  className="absolute inset-0 h-full w-full object-cover"
                />
              </div>
            ) : (
              <div className="flex aspect-[3/2] w-full max-w-full items-center justify-center rounded-[14px] bg-[#d9e2f8] text-[#8893b0]">
                {siteCommonCta(loc, 'no_image')}
              </div>
            )}
            {(article.coverCredit || article.coverSource) && (
              <p className="mt-2 text-[11px] uppercase tracking-wide text-[#7c8898]">
                {article.coverCredit}
                {article.coverCredit && article.coverSource ? ' / ' : null}
                {article.coverSource}
              </p>
            )}
          </div>
        </div>
        </div>
      </div>

      {/* Corps + sidebar : pas de pt sur mobile (même logique que colonne lg) ; espace haut desktop = lg:pt-20. */}
      <div className="bg-white">
        <div className="mx-auto max-w-7xl px-4 pb-16 pt-0 sm:px-6 lg:px-8 lg:pt-20">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[300px_minmax(0,1fr)] lg:gap-14">
            <aside className="lg:max-w-[300px]">
              {/* Sticky : bord haut du bloc = haut du titre Share ; top 80px = 80px sous le viewport quand collé. */}
              <div className="sticky top-[80px] self-start">
                {shareSmData && articleNavVisible ? (
                  <SectionShareSm
                    title={typeof shareSmData.title === 'string' ? shareSmData.title : ''}
                    items={shareSmData.items}
                    pageUrl={shareUrlResolved}
                    articleTitle={articleTitle}
                  />
                ) : null}
                {showToc ? (
                  <TableOfContents
                    headings={headings}
                    title={toc}
                    minCount={tocMinHeadings}
                    navClassName="hidden w-full lg:block"
                  />
                ) : null}
              </div>
            </aside>

            <div className="min-w-0 max-w-[720px] [&>div:first-child>:first-child]:!mt-0">
              {elements.map(({ blockId, element }) => (
                <div key={blockId}>{element}</div>
              ))}

              {showDocuments && docs.length > 0 ? (
                <div className="mt-12 border-t border-[#e8ecf4] pt-8">
                  <SectionTitle align="left" size="small" className="mb-4 text-black">
                    {docsTitle}
                  </SectionTitle>
                  <div className="space-y-3">
                    {docs.map((doc, i) => (
                      <DocumentAttachmentRow key={i} url={doc.url!} title={doc.title || 'Document'} />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

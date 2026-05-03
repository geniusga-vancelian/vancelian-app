import Link from 'next/link'
import { getLocaleOrDefault } from '@/config/locales'
import { ArticleCarousel } from '@/components/blog/ArticleCarousel'
import { getDateLabels, formatArticleDate, formatArticleDateShort } from '@/lib/blog/formatDates'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { CMS_BLOG_HERO_BLEED_UNDER_NAV_SECTION_CLASSNAME } from '@/lib/design/cmsBlogHeroUnderNavLayout'
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

function embedVideoSrc(videoUrl: string): string {
  if (videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')) {
    const id = videoUrl.includes('watch?v=')
      ? videoUrl.split('watch?v=')[1]?.split('&')[0]
      : videoUrl.split('/').pop()
    return `https://www.youtube.com/embed/${id ?? ''}`
  }
  if (videoUrl.includes('vimeo.com')) {
    return `https://player.vimeo.com/video/${videoUrl.split('/').pop() ?? ''}`
  }
  return videoUrl
}

export interface SectionBlogArticleHeroProps {
  locale: string
  /**
   * Premier bloc sous la nav (overlay gris) : même `pt` / `-mt` que le hero secondary avec image
   * et que `BlogFeaturedModule` — sans dépendre d’un `pt-20` sur le parent.
   */
  bleedUnderPrimaryNav?: boolean
  /** Fil « Blog › … » — tout le contenu vient du CMS, pas d’un article Prisma. */
  showBreadcrumb?: boolean
  blogLabel?: string
  /** Dernier segment du fil (défaut : titre). */
  breadcrumbCurrentText?: string
  title: string
  standfirst?: string
  /** Pastilles type catégories (vide = pas de pastilles sauf editorialPillLabel). */
  categoryPillLabels?: string[]
  /** Une pastille si categoryPillLabels est vide (ex. segment éditorial). */
  editorialPillLabel?: string
  authorName?: string
  authorRole?: string
  showAuthorByPrefix?: boolean
  showReadingTime?: boolean
  /** Texte libre affiché à la place de la durée (ex. « 4 min de lecture »). */
  readingTimeText?: string
  showDate?: boolean
  publishedAtIso?: string
  showUpdatedDate?: boolean
  updatedAtIso?: string
  coverTitle?: string
  coverUrl?: string
  videoUrl?: string
  galleryUrls?: string[]
  coverCredit?: string
  coverSource?: string
}

/**
 * Bandeau « hero article » **100 % CMS** : même grille que l’en-tête du lecteur d’article,
 * sans lien avec `PublicArticle`. Réutilisable sur n’importe quelle page composable.
 */
export function SectionBlogArticleHero({
  locale,
  bleedUnderPrimaryNav = false,
  showBreadcrumb = false,
  blogLabel,
  breadcrumbCurrentText,
  title,
  standfirst,
  categoryPillLabels = [],
  editorialPillLabel,
  authorName,
  authorRole,
  showAuthorByPrefix = false,
  showReadingTime = true,
  readingTimeText,
  showDate = true,
  publishedAtIso,
  showUpdatedDate = false,
  updatedAtIso,
  coverTitle,
  coverUrl,
  videoUrl,
  galleryUrls,
  coverCredit,
  coverSource,
}: SectionBlogArticleHeroProps) {
  const loc = getLocaleOrDefault(locale)
  const blogPath = `/${loc}/blog`
  const blog = blogLabel?.trim() || siteCommonCta(loc, 'blog_default_title')
  const crumbLast = (breadcrumbCurrentText ?? title).trim()
  const dateLabels = getDateLabels(loc)

  const publishedDate = publishedAtIso ? new Date(publishedAtIso) : null
  const updatedDate = updatedAtIso ? new Date(updatedAtIso) : null
  const showUpdated =
    showUpdatedDate &&
    publishedDate &&
    updatedDate &&
    updatedDate.getTime() - publishedDate.getTime() > 60000

  const pills = categoryPillLabels.map((l) => l.trim()).filter(Boolean)
  const showEditorialFallback = pills.length === 0 && Boolean(editorialPillLabel?.trim())

  const heroBackground = figmaDsColors.neutral.gray100
  const heroTitleColor = figmaDsColors.neutral.gray900
  const heroMetaMuted = 'text-[#62656e]'

  const gallery = Array.isArray(galleryUrls) ? galleryUrls.filter(Boolean) : []
  const hasGallery = gallery.length > 0
  const cover = coverUrl?.trim() ?? ''

  return (
    <div
      id={bleedUnderPrimaryNav ? 'blog-hero' : undefined}
      className={cn(
        bleedUnderPrimaryNav
          ? CMS_BLOG_HERO_BLEED_UNDER_NAV_SECTION_CLASSNAME
          : 'pt-10 md:pt-12',
      )}
      style={{ backgroundColor: heroBackground }}
    >
      <div className="mx-auto max-w-7xl px-4 pb-10 pt-0 sm:px-6 lg:px-8 lg:pb-14">
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
              <li className="line-clamp-1 text-[#62656e]">{crumbLast}</li>
            </ol>
          </nav>
        ) : null}

        <div
          className="grid items-start gap-8 lg:grid-cols-2 lg:items-center lg:gap-10 xl:gap-12"
          data-name="Article hero (CMS)"
        >
          <div className="min-w-0">
            <div className="mb-4 flex flex-wrap gap-2">
              {pills.map((label, i) => (
                <CategoryPill
                  key={`${label}-${i}`}
                  label={label}
                  dotClassName={categoryPillDotPalette[i % categoryPillDotPalette.length]}
                />
              ))}
              {showEditorialFallback ? (
                <CategoryPill label={editorialPillLabel!.trim()} />
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
              {title}
            </SectionTitle>
            {standfirst?.trim() ? (
              <ParagraphLargeBold color="#62656e" className="mt-4 max-w-[46rem] text-left">
                {standfirst}
              </ParagraphLargeBold>
            ) : null}

            <div
              className={cn(
                figmaDsParagraphClassName,
                'not-italic mt-6 flex w-full max-w-full flex-wrap items-center gap-x-3 gap-y-2',
                heroMetaMuted,
              )}
              data-name="Article meta (CMS)"
            >
              {authorName?.trim() ? (
                <>
                  <span>
                    {showAuthorByPrefix ? (
                      <>
                        {siteCommonCta(loc, 'article_by_author')}{' '}
                      </>
                    ) : null}
                    <span className="font-['Avenir:Heavy',sans-serif] font-extrabold text-black">
                      {authorName}
                    </span>
                    {authorRole?.trim() ? (
                      <span className="font-['Avenir:Roman',sans-serif] font-normal text-[#62656e]">
                        {' '}
                        · {authorRole}
                      </span>
                    ) : null}
                  </span>
                  {(showReadingTime && readingTimeText?.trim()) || (showDate && publishedDate) ? (
                    <span className="hidden h-3 w-px bg-black/15 sm:inline" aria-hidden />
                  ) : null}
                </>
              ) : null}
              {showReadingTime && readingTimeText?.trim() ? (
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
              ) : null}
              {showReadingTime && readingTimeText?.trim() && showDate && publishedDate ? (
                <span className="hidden h-3 w-px bg-black/15 sm:inline" aria-hidden />
              ) : null}
              {showDate && publishedDate && !Number.isNaN(publishedDate.getTime()) ? (
                <time
                  className="text-[#62656e]"
                  dateTime={publishedDate.toISOString()}
                  title={formatArticleDate(publishedDate, loc)}
                >
                  {formatArticleDateShort(publishedDate, loc)}
                  {showUpdated && updatedDate && !Number.isNaN(updatedDate.getTime())
                    ? ` · ${dateLabels.updated} ${formatArticleDateShort(updatedDate, loc)}`
                    : ''}
                </time>
              ) : null}
            </div>
          </div>

          <div className="flex min-w-0 flex-col justify-center self-stretch">
            {coverTitle?.trim() ? (
              <p className="mb-2 text-[13px] text-[#62656e]">{coverTitle}</p>
            ) : null}
            {videoUrl?.trim() ? (
              <div className="relative aspect-[3/2] w-full overflow-hidden rounded-[14px] bg-black">
                <iframe
                  src={embedVideoSrc(videoUrl)}
                  className="h-full w-full"
                  allowFullScreen
                  title={title}
                />
              </div>
            ) : hasGallery ? (
              <div className="w-full overflow-hidden rounded-[14px]">
                <ArticleCarousel
                  frameClassName="aspect-[3/2]"
                  images={[cover, ...gallery].filter(Boolean)}
                  title={title}
                />
              </div>
            ) : cover ? (
              <div className="relative aspect-[3/2] w-full max-w-full overflow-hidden rounded-[14px] bg-[#d9e2f8]">
                <img
                  src={cover}
                  alt={title}
                  className="absolute inset-0 h-full w-full object-cover"
                />
              </div>
            ) : (
              <div className="flex aspect-[3/2] w-full max-w-full items-center justify-center rounded-[14px] bg-[#d9e2f8] text-[#8893b0]">
                {siteCommonCta(loc, 'no_image')}
              </div>
            )}
            {(coverCredit?.trim() || coverSource?.trim()) && (
              <p className="mt-2 text-[11px] uppercase tracking-wide text-[#7c8898]">
                {coverCredit}
                {coverCredit?.trim() && coverSource?.trim() ? ' / ' : null}
                {coverSource}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

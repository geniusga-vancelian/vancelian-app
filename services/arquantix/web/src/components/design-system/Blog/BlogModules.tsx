import Link from 'next/link'
import { HERO_NAV_BLEND_ANCHOR_ID } from '@/hooks/useHeroSecondaryNavBlend'
import { CMS_BLOG_HERO_BLEED_UNDER_NAV_SECTION_CLASSNAME } from '@/lib/design/cmsBlogHeroUnderNavLayout'
import { cn } from '@/lib/utils'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import {
  Paragraph,
  SectionTitle,
  figmaDsLinksClassName,
  figmaDsTitleSmallClassName,
} from '@/components/design-system/extracted'
import {
  figmaDsColors,
  figmaDsFeaturedPostSidebarTitleClassName,
} from '@/components/design-system/extracted/tokens'

export type DsBlogArticle = {
  id: string
  slug: string
  title: string
  standfirst: string
  coverUrl: string
  authorName: string
  publishedAt: string | null
  readingTime: number
}

function BlogMeta({
  article,
  locale,
  minReadLabel,
  className,
}: {
  article: DsBlogArticle
  locale: string
  minReadLabel: string
  className?: string
}) {
  return (
    <div className={cn('mt-2 flex flex-wrap items-center gap-2 text-[12px] text-[#62656e]', className)}>
      <span>{article.authorName}</span>
      {article.publishedAt && (
        <>
          <span>•</span>
          <time dateTime={article.publishedAt}>
            {formatArticleDateShort(new Date(article.publishedAt), locale)}
          </time>
        </>
      )}
      <span>•</span>
      <span>{article.readingTime} {minReadLabel}</span>
    </div>
  )
}

function BlogCover({
  article,
  className,
  noImageLabel,
}: {
  article: DsBlogArticle
  className: string
  noImageLabel: string
}) {
  if (!article.coverUrl) {
    return (
      <div className={cn('flex items-center justify-center bg-[#d9e2f8] text-[#8893b0]', className)}>
        {noImageLabel}
      </div>
    )
  }
  return <img src={article.coverUrl} alt={article.title} className={cn('object-cover', className)} />
}

export function BlogCtaPillButton({ href, label }: { href: string; label: string }) {
  // Aligné sur le bouton "Voir toutes les offres" (ProjetGallery) : bordure absolue + typo Figma (10/500, lh 110%, tracking 0.4px) + centrage vertical via leading-[0] + p leading-[1.1]
  return (
    <Link
      href={href}
      className="group relative h-[36px] min-w-[112px] shrink-0 cursor-pointer overflow-hidden rounded-[20px] whitespace-nowrap"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-0 bg-white transition-colors duration-200 group-hover:bg-black"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 z-10 rounded-[20px] border border-solid border-[#62656e] transition-colors duration-200 group-hover:border-black"
      />
      <div className="relative z-20 flex h-full w-full items-center justify-center">
        <div className="flex h-full w-full items-center justify-center px-[20px] py-[10px]">
          <div className="flex flex-col justify-center font-ui font-medium leading-[0] not-italic text-[10px] text-center text-black tracking-[0.4px] uppercase transition-colors duration-200 group-hover:text-white">
            <p className="leading-[1.1] transition-colors duration-200 group-hover:text-white">{label}</p>
          </div>
        </div>
      </div>
    </Link>
  )
}

/**
 * Carte teaser article (grille « derniers articles », carrousel vault `BlogALaUne`).
 * - `default` : titre, chapô, ligne meta auteur • date • temps de lecture (comportement historique).
 * - `vault` : titre, **date uniquement** sous le titre (sans auteur ni séparateurs), puis chapô.
 */
export function BlogArticleTeaserCard({
  article,
  locale,
  minReadLabel,
  noImageLabel,
  linkClassName,
  variant = 'default',
}: {
  article: DsBlogArticle
  locale: string
  minReadLabel: string
  noImageLabel: string
  linkClassName?: string
  /** Offre Vault : ligne meta réduite à la date, sous le titre. */
  variant?: 'default' | 'vault'
}) {
  return (
    <Link
      href={article.slug}
      className={cn(
        'group block overflow-hidden rounded-[10px] bg-[#f3f3f3] transition-colors hover:bg-[#eeeeee]',
        linkClassName,
      )}
    >
      <div className="relative h-[230px] w-full shrink-0 overflow-hidden bg-[#d9e2f8]">
        <BlogCover article={article} className="h-full w-full" noImageLabel={noImageLabel} />
      </div>
      <div className="px-6 pb-6 pt-5 md:px-10 md:pb-10 md:pt-8">
        <h3 className={cn(figmaDsLinksClassName, 'line-clamp-2 text-[22px] leading-[1.12] text-black md:text-[24px]')}>
          {article.title}
        </h3>
        {variant === 'vault' ? (
          article.publishedAt ? (
            <time
              dateTime={article.publishedAt}
              className="mt-2 block text-[12px] font-ui font-normal leading-[1.35] text-[#62656e]"
            >
              {formatArticleDateShort(new Date(article.publishedAt), locale)}
            </time>
          ) : null
        ) : null}
        <Paragraph className="mt-3 line-clamp-2 text-[#62656e]">{article.standfirst}</Paragraph>
        {variant === 'vault' ? null : (
          <BlogMeta
            article={article}
            locale={locale}
            minReadLabel={minReadLabel}
            className="mt-4 text-[#62656e]"
          />
        )}
      </div>
    </Link>
  )
}

export function BlogFeaturedModule({
  featuredTitle,
  featuredHref,
  featuredTag,
  featuredArticle,
  sideTitle,
  sideArticles,
  locale,
  showStandfirst = true,
  showMeta = true,
  minReadLabel = 'min read',
  noImageLabel = 'No image',
  bleedUnderPrimaryNav = false,
}: {
  featuredTitle: string
  featuredHref: string
  featuredTag: string
  featuredArticle: DsBlogArticle
  sideTitle: string
  sideArticles: DsBlogArticle[]
  locale: string
  showStandfirst?: boolean
  showMeta?: boolean
  minReadLabel?: string
  noImageLabel?: string
  /** Bandeau sous le menu fixe (page blog CMS), comme hero secondary. */
  bleedUnderPrimaryNav?: boolean
}) {
  return (
    <section
      id={bleedUnderPrimaryNav ? 'blog-hero' : undefined}
      className={cn(
        'relative mb-16 ml-[calc(50%-50vw)] mr-[calc(50%-50vw)] w-screen max-w-[100vw] py-10 md:py-12',
        bleedUnderPrimaryNav && CMS_BLOG_HERO_BLEED_UNDER_NAV_SECTION_CLASSNAME,
      )}
      style={{ backgroundColor: figmaDsColors.neutral.gray100 }}
    >
      <div className="mx-auto grid max-w-7xl items-start gap-8 px-4 sm:px-6 lg:px-8 lg:grid-cols-[minmax(0,760px)_minmax(0,1fr)]">
      <Link
        href={featuredHref}
        className="group block overflow-hidden rounded-[14px]"
        style={{ backgroundColor: figmaDsColors.neutral.gray100 }}
      >
        <div className="relative aspect-[760/468] overflow-hidden rounded-[14px] bg-[#d9e2f8]">
          <BlogCover article={featuredArticle} className="h-full w-full" noImageLabel={noImageLabel} />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/90 via-black/62 to-black/20" />
          <div className="absolute inset-x-0 bottom-0 p-6 md:p-10">
            <h2
              id={bleedUnderPrimaryNav ? HERO_NAV_BLEND_ANCHOR_ID : undefined}
              className={cn(
                figmaDsTitleSmallClassName,
                'line-clamp-2 text-white',
              )}
            >
              {featuredTitle}
            </h2>
            {showStandfirst ? (
              <Paragraph color="#FFFFFF" className="mt-3 line-clamp-2 opacity-95">
                {featuredArticle.standfirst}
              </Paragraph>
            ) : null}
            {showMeta ? (
              <BlogMeta
                article={featuredArticle}
                locale={locale}
                minReadLabel={minReadLabel}
                className="mt-3 text-white/85"
              />
            ) : null}
          </div>
        </div>
      </Link>

      <aside>
        <SectionTitle align="left" size="small" className="mb-5 text-[24px] text-black">
          {sideTitle}
        </SectionTitle>
        <div>
          {sideArticles.map((article, index) => (
            <div key={article.id}>
              <Link
                href={article.slug}
                className="flex items-center gap-4 rounded-[10px] py-3 transition-colors hover:bg-black/[0.04]"
              >
                <div className="h-[66px] w-[108px] shrink-0 overflow-hidden rounded-[12px] bg-[#d9e2f8]">
                  <BlogCover article={article} className="h-full w-full" noImageLabel={noImageLabel} />
                </div>
                <div className="min-w-0">
                  <h3
                    className={cn(
                      figmaDsFeaturedPostSidebarTitleClassName,
                      'line-clamp-2 text-black',
                    )}
                  >
                    {article.title}
                  </h3>
                  <Paragraph className="mt-1 line-clamp-1 text-[#62656e]">{article.standfirst}</Paragraph>
                </div>
              </Link>
              {index < sideArticles.length - 1 ? <div className="h-px bg-[#dfe3ee]" /> : null}
            </div>
          ))}
        </div>
      </aside>
      </div>
    </section>
  )
}

export type BlogMosaicPagination = {
  currentPage: number
  totalPages: number
  prevHref: string | null
  nextHref: string | null
  prevLabel: string
  nextLabel: string
}

export function BlogRecentPostsModule({
  title,
  ctaLabel,
  ctaHref,
  articles,
  locale,
  minReadLabel = 'min read',
  noImageLabel = 'No image',
  /** Grille 2×2 (ex. module « Vous aimerez aussi » sur l’article). */
  layoutVariant = 'default',
  mosaicPagination,
  /** Faux pour `blog_mosaic` : pas de pilule « tout voir » (pagination bas de bloc). */
  showHeaderCta = true,
}: {
  title: string
  /** Ignoré si `showHeaderCta` est faux. */
  ctaLabel?: string
  ctaHref?: string
  articles: DsBlogArticle[]
  locale: string
  minReadLabel?: string
  noImageLabel?: string
  layoutVariant?: 'default' | 'related2x2'
  mosaicPagination?: BlogMosaicPagination
  showHeaderCta?: boolean
}) {
  const gridClassName =
    layoutVariant === 'related2x2'
      ? 'grid grid-cols-1 gap-8 md:grid-cols-2'
      : 'grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3'
  return (
    <section className="mb-16">
      <div
        className={cn(
          'mb-8 flex items-center gap-4',
          showHeaderCta ? 'justify-between' : 'justify-start',
        )}
      >
        <SectionTitle align="left" size="small" className="text-[40px] text-black">
          {title}
        </SectionTitle>
        {showHeaderCta ? (
          <BlogCtaPillButton href={ctaHref ?? '#'} label={ctaLabel ?? ''} />
        ) : null}
      </div>
      <div className={gridClassName}>
        {articles.map((article) => (
          <BlogArticleTeaserCard
            key={article.id}
            article={article}
            locale={locale}
            minReadLabel={minReadLabel}
            noImageLabel={noImageLabel}
          />
        ))}
      </div>
      {mosaicPagination && mosaicPagination.totalPages > 1 ? (
        <nav
          className="mt-10 flex flex-wrap items-center justify-center gap-4 border-t border-[#dfe3ee] pt-8"
          aria-label="Pagination"
        >
          {mosaicPagination.prevHref ? (
            <Link
              href={mosaicPagination.prevHref}
              className={cn(
                figmaDsLinksClassName,
                'rounded-full border border-[#d6dae6] px-5 py-2 text-[15px] text-black transition-colors hover:bg-black/[0.04]',
              )}
            >
              {mosaicPagination.prevLabel}
            </Link>
          ) : (
            <span className="rounded-full border border-transparent px-5 py-2 text-[15px] text-[#a8adb8]">
              {mosaicPagination.prevLabel}
            </span>
          )}
          <span className="text-[14px] text-[#62656e]">
            {mosaicPagination.currentPage} / {mosaicPagination.totalPages}
          </span>
          {mosaicPagination.nextHref ? (
            <Link
              href={mosaicPagination.nextHref}
              className={cn(
                figmaDsLinksClassName,
                'rounded-full border border-[#d6dae6] px-5 py-2 text-[15px] text-black transition-colors hover:bg-black/[0.04]',
              )}
            >
              {mosaicPagination.nextLabel}
            </Link>
          ) : (
            <span className="rounded-full border border-transparent px-5 py-2 text-[15px] text-[#a8adb8]">
              {mosaicPagination.nextLabel}
            </span>
          )}
        </nav>
      ) : null}
    </section>
  )
}

export function BlogCategoryRowsModule({
  title,
  ctaLabel,
  ctaHref,
  articles,
  locale,
  minReadLabel = 'min read',
  noImageLabel = 'No image',
}: {
  title: string
  ctaLabel?: string
  ctaHref?: string
  articles: DsBlogArticle[]
  locale: string
  minReadLabel?: string
  noImageLabel?: string
}) {
  const mainRows = articles.slice(0, 3)
  const compactRows = articles.slice(3, 9)

  return (
    <section className="mb-14">
      <div className="mb-5 flex items-center justify-between gap-4">
        <SectionTitle align="left" size="small" className="text-[40px] text-black">
          {title}
        </SectionTitle>
        {ctaLabel && ctaHref ? (
          <BlogCtaPillButton href={ctaHref} label={ctaLabel} />
        ) : null}
      </div>

      <div className="space-y-5">
        {mainRows.map((article, index) => (
          <div key={article.id} className={cn('space-y-4', index < mainRows.length - 1 && 'pb-5 border-b border-[#d6dae6]')}>
            <Link href={article.slug} className="grid gap-4 rounded-[10px] md:grid-cols-[1fr_240px] md:items-center">
              <div className="min-w-0">
                <h3 className={cn(figmaDsLinksClassName, 'line-clamp-3 text-[26px] leading-[1.1] text-black')}>
                  {article.title}
                </h3>
                <Paragraph className="mt-2 line-clamp-3 text-[#62656e]">{article.standfirst}</Paragraph>
                <BlogMeta article={article} locale={locale} minReadLabel={minReadLabel} className="mt-3" />
              </div>
              <div className="h-[130px] overflow-hidden rounded-[10px] bg-[#d9e2f8]">
                <BlogCover article={article} className="h-full w-full" noImageLabel={noImageLabel} />
              </div>
            </Link>
          </div>
        ))}
      </div>

      {compactRows.length > 0 ? (
        <>
          <div className="mb-5 mt-10 flex items-center justify-between gap-4">
            <SectionTitle align="left" size="small" className="text-[40px] text-black">
              {title}
            </SectionTitle>
            {ctaLabel && ctaHref ? (
              <BlogCtaPillButton href={ctaHref} label={ctaLabel} />
            ) : null}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
          {compactRows.map((article) => (
            <Link
              key={article.id}
              href={article.slug}
              className="grid grid-cols-[1fr_110px] items-center gap-3 rounded-[10px] border border-[#edf0f8] p-3"
            >
              <div className="min-w-0">
                <h3 className={cn(figmaDsLinksClassName, 'line-clamp-3 text-[18px] text-black')}>
                  {article.title}
                </h3>
                <Paragraph className="mt-1 line-clamp-3 text-[#62656e]">{article.standfirst}</Paragraph>
                <BlogMeta article={article} locale={locale} minReadLabel={minReadLabel} className="mt-2" />
              </div>
              <div className="h-[72px] overflow-hidden rounded-[8px] bg-[#d9e2f8]">
                <BlogCover article={article} className="h-full w-full" noImageLabel={noImageLabel} />
              </div>
            </Link>
          ))}
          </div>
        </>
      ) : null}
    </section>
  )
}


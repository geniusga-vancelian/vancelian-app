'use client'

import {
  BlogArticleTeaserCard,
  BlogCtaPillButton,
  type DsBlogArticle,
} from '@/components/design-system/Blog/BlogModules'
import { VEditorialTitle } from '@/components/design-system/vancelian/VEditorialTitle'
import { Carousel, CarouselContent, CarouselItem } from '@/components/ui/carousel'
import { cn } from '@/lib/utils'

type Props = {
  title: string
  ctaLabel: string
  ctaHref: string
  articles: DsBlogArticle[]
  locale: string
  minReadLabel: string
  noImageLabel: string
}

/**
 * Module Vault `BlogALaUne` : liste horizontale défilable façon page Invest
 * (Flutter `ExclusiveOffersCarousel` : ~1 carte + léger peek 1/1,05,
 * sans snap « une carte par geste »).
 */
export function VaultBlogALaUneSliding({
  title,
  ctaLabel,
  ctaHref,
  articles,
  locale,
  minReadLabel,
  noImageLabel,
}: Props) {
  if (articles.length === 0) {
    return null
  }

  const multi = articles.length > 1

  return (
    <section className="mb-16 w-full min-w-0">
      <div className="mb-6 flex flex-wrap items-center gap-4 justify-between">
        <VEditorialTitle as="h2" size="module" align="left" className="text-left">
          {title}
        </VEditorialTitle>
        <BlogCtaPillButton href={ctaHref} label={ctaLabel} />
      </div>

      <Carousel
        opts={{
          align: 'start',
          containScroll: 'trimSnaps',
          dragFree: true,
          duration: 20,
        }}
        className="w-full min-w-0"
      >
        <CarouselContent className={multi ? '-ml-3 md:-ml-4' : '!ml-0'}>
          {articles.map((article) => (
            <CarouselItem
              key={article.id}
              className={cn(
                'min-h-0 shrink-0',
                multi ? 'basis-[95.238%]' : '!basis-full !pl-0 md:!pl-0',
              )}
            >
              <BlogArticleTeaserCard
                article={article}
                locale={locale}
                minReadLabel={minReadLabel}
                noImageLabel={noImageLabel}
                variant="vault"
              />
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>
    </section>
  )
}

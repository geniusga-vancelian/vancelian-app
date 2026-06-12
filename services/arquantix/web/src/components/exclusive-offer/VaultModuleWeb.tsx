'use client'

import { usePathname } from 'next/navigation'
import ReactMarkdown from 'react-markdown'

import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import { cn } from '@/lib/utils'
import {
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from '@/lib/i18n/publicLocalizedRouting'
import {
  SIMPLE_MARKDOWN_MODULE_TITLE_TYPO,
  VAULT_MODULE_DESCRIPTION_TYPO,
  VAULT_MODULE_HEADING_CLASS,
  VAULT_MODULE_LINK_CLASS,
  VAULT_MODULE_CARD_CLASS,
  VAULT_PARAGRAPH_BODY_READING_TYPO,
  vaultProseMarkdownClass,
  type DsBlogArticle,
} from '@/components/design-system'
import { VaultFaqAccordionModuleWeb } from '@/components/exclusive-offer/VaultFaqAccordionModuleWeb'
import {
  VaultMarketingCardsCarouselWeb,
  VaultMarketingLargePortraitWeb,
} from '@/components/exclusive-offer/VaultMarketingModulesWeb'
import {
  VaultAllocationModuleWeb,
  VaultPerformanceChartWeb,
  VaultTransactionLatestModuleWeb,
} from '@/components/exclusive-offer/VaultMetricsModulesWeb'
import { VaultModuleHeader } from '@/components/exclusive-offer/VaultModuleHeader'
import { ArticleBodyBulletListBlock } from '@/components/design-system/ArticleBodyBulletListBlock'
import { ArticleBodyQuoteBlock } from '@/components/design-system/ArticleBodyQuoteBlock'
import { ArticleBodyMarkdown } from '@/lib/blog/articleBodyMarkdown'
import {
  articleBodyMarkdownComponents,
  articleBodyRemarkPlugins,
  slugifyHeading,
} from '@/components/blog/ArticleBlockStream'
import {
  HeroOfferTagChip,
  HERO_OFFER_TAG_GAP_CLASS,
} from '@/components/design-system/heroOfferTagChip'
import { ArticleStepsModule } from '@/components/design-system/ArticleStepsModule'
import { KeyInformationTab } from '@/components/exclusive-offer/KeyInformationTab'
import { VaultMediaCarousel } from '@/components/exclusive-offer/VaultMediaCarousel'
import { VaultVideoBlockArticle } from '@/components/exclusive-offer/VaultVideoBlockArticle'
import { VaultLocalisationModuleWeb } from '@/components/exclusive-offer/VaultLocalisationModuleWeb'
import { VaultVirtualVisualizationModuleWeb } from '@/components/exclusive-offer/VaultVirtualVisualizationModuleWeb'
import { VaultDocumentsListModuleWeb } from '@/components/exclusive-offer/VaultDocumentsListModuleWeb'
import { VaultFundingModuleSection } from '@/components/exclusive-offer/VaultFundingModuleSection'
import { VaultBlogALaUneSliding } from '@/components/exclusive-offer/VaultBlogALaUneSliding'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'

/** SimpleMarkdownContentModule : pas de carte bordurée ; titre centré, corps markdown justifié (pleine largeur). */
function MarkdownBlock({
  title,
  markdown,
  links,
}: {
  title?: string
  markdown: string
  links?: Array<{ label?: string; url?: string }>
}) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  return (
    <div className="w-full">
      {title ? (
        <h2 className={`mb-4 ${SIMPLE_MARKDOWN_MODULE_TITLE_TYPO}`}>{title}</h2>
      ) : null}
      <div className={vaultProseMarkdownClass()}>
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </div>
      {Array.isArray(links) && links.length > 0 ? (
        <ul className={cn('mt-4 w-full list-none space-y-2 pt-2 text-left', VAULT_MODULE_DESCRIPTION_TYPO)}>
          {links.map((l, i) => {
            if (!l?.url || !l?.label) return null
            const raw = l.url.trim()
            const href =
              raw && !shouldSkipLocalizePublicHref(raw)
                ? localizePublicInternalHref(raw, loc)
                : raw
            return (
              <li key={i}>
                <a href={href} className={VAULT_MODULE_LINK_CLASS}>
                  {l.label}
                </a>
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}

export function VaultModuleWeb({ mod }: { mod: VaultModulePublic }) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  const c = mod.content

  const typeNorm = typeof mod.type === 'string' ? mod.type.trim().toLowerCase() : ''
  if (typeNorm === 'stepsmodule') {
    return (
      <div className="w-full">
        <ArticleStepsModule content={c} />
      </div>
    )
  }

  switch (mod.type) {
    case 'TitlePage': {
      const title = typeof c.title === 'string' ? c.title : ''
      const subtitle = typeof c.subtitle === 'string' ? c.subtitle : ''
      return (
        <div className="space-y-3">
          {title ? (
            <h1 className="font-ui text-[clamp(40px,4.6vw,56px)] font-semibold leading-[1.05] tracking-normal text-center text-v-fg">
              {title}
            </h1>
          ) : null}
          {subtitle ? <p className={VAULT_MODULE_DESCRIPTION_TYPO}>{subtitle}</p> : null}
        </div>
      )
    }

    case 'VideoBlockArticleModule': {
      return <VaultVideoBlockArticle content={c} />
    }

    case 'LocalisationModule': {
      return <VaultLocalisationModuleWeb content={c} />
    }

    case 'VirtualVisualizationModule': {
      return <VaultVirtualVisualizationModuleWeb content={c} />
    }

    case 'MediaImageCarouselModule': {
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle : ''
      const description = typeof c.description === 'string' ? c.description : ''
      const rawItems = Array.isArray(c.carouselItems) ? c.carouselItems : []
      const items = rawItems
        .map((raw) => {
          const row = raw as Record<string, unknown>
          const url = typeof row.url === 'string' ? row.url : ''
          const mediaId = typeof row.mediaId === 'string' ? row.mediaId : ''
          const alt = row.alt === null || typeof row.alt === 'string' ? row.alt : null
          return { url, mediaId, alt }
        })
        .filter((x) => x.url.length > 0 && x.mediaId.length > 0)
      if (!items.length) return null
      return (
        <VaultMediaCarousel
          moduleTitle={moduleTitle}
          description={description}
          items={items}
        />
      )
    }

    case 'DocumentsListModule': {
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle : ''
      const description = typeof c.description === 'string' ? c.description : ''
      const subtitle = typeof c.subtitle === 'string' ? c.subtitle : ''
      const rawItems = Array.isArray(c.documentItems) ? c.documentItems : []
      const items = rawItems
        .map((raw) => {
          const row = raw as Record<string, unknown>
          const downloadUrl = typeof row.downloadUrl === 'string' ? row.downloadUrl : ''
          const mediaId = typeof row.mediaId === 'string' ? row.mediaId : ''
          const displayName = typeof row.displayName === 'string' ? row.displayName : ''
          const dateLabel = typeof row.dateLabel === 'string' ? row.dateLabel : ''
          return { downloadUrl, mediaId, displayName, dateLabel }
        })
        .filter((x) => x.downloadUrl.length > 0 && x.mediaId.length > 0)
      if (!items.length) return null
      return (
        <VaultDocumentsListModuleWeb
          subtitle={subtitle}
          moduleTitle={moduleTitle}
          description={description}
          items={items}
        />
      )
    }

    case 'SimpleMarkdownContentModule': {
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle : undefined
      const markdown = typeof c.markdown === 'string' ? c.markdown : ''
      const links = Array.isArray(c.links) ? (c.links as Array<{ label?: string; url?: string }>) : []
      if (!markdown.trim() && !moduleTitle) {
        return null
      }
      return <MarkdownBlock title={moduleTitle} markdown={markdown || ' '} links={links} />
    }

    case 'FundingModule': {
      return <VaultFundingModuleSection content={c} />
    }

    case 'BlogALaUne':
    case 'blogalaune':
    case 'blog_a_la_une': {
      const rawArticles = Array.isArray(c._resolvedArticles) ? c._resolvedArticles : []
      const articles: DsBlogArticle[] = rawArticles.flatMap((row) => {
        if (row == null || typeof row !== 'object' || Array.isArray(row)) return []
        const o = row as Record<string, unknown>
        const id = typeof o.id === 'string' ? o.id : ''
        const slug = typeof o.slug === 'string' ? o.slug : ''
        const title = typeof o.title === 'string' ? o.title : ''
        const standfirst = typeof o.standfirst === 'string' ? o.standfirst : ''
        const authorName = typeof o.authorName === 'string' ? o.authorName : ''
        const coverUrl = typeof o.coverUrl === 'string' ? o.coverUrl : ''
        const rt = typeof o.readingTime === 'number' ? o.readingTime : NaN
        const readingTime = Number.isFinite(rt) ? rt : 0
        let publishedAt: string | null = null
        if (typeof o.publishedAt === 'string' && o.publishedAt.length > 0) {
          publishedAt = o.publishedAt
        }
        if (!id || !slug || !title) return []
        const item = {
          id,
          slug,
          title,
          standfirst,
          coverUrl,
          authorName,
          publishedAt,
          readingTime,
        }
        return [item]
      })

      if (articles.length === 0) {
        return null
      }

      const titleRaw = typeof c.title === 'string' ? c.title.trim() : ''
      const sectionTitle =
        titleRaw.length > 0 ? titleRaw : siteCommonCta(loc, 'blog_featured_stories')

      const blogBasePath = `/${loc}/blog`

      return (
        <VaultBlogALaUneSliding
          title={sectionTitle}
          ctaLabel={siteCommonCta(loc, 'view_all')}
          ctaHref={blogBasePath}
          articles={articles}
          locale={loc}
          minReadLabel={siteCommonCta(loc, 'blog_min_read')}
          noImageLabel={siteCommonCta(loc, 'no_image')}
        />
      )
    }

    case 'TagsModule': {
      const rawTags = Array.isArray(c.tags) ? c.tags : []
      const tags = rawTags
        .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
        .map((t) => t.trim())
      if (tags.length === 0) return null
      return (
        <div
          className={`flex w-full flex-wrap items-center justify-center ${HERO_OFFER_TAG_GAP_CLASS}`}
        >
          {tags.map((t, i) => (
            <HeroOfferTagChip key={`${t}-${i}`} variant="onLight">
              {t}
            </HeroOfferTagChip>
          ))}
        </div>
      )
    }

    case 'CompetitiveAdvantagesModule': {
      const titleRaw = typeof c.title === 'string' ? c.title.trim() : ''
      const rows = Array.isArray(c.rows) ? c.rows : []
      const cells = rows
        .map((raw, i) => {
          const row = raw as Record<string, unknown>
          const rt = typeof row.title === 'string' ? row.title.trim() : ''
          const rd = typeof row.description === 'string' ? row.description.trim() : ''
          if (!rt && !rd) return null
          return (
            <div key={i} className={cn(VAULT_MODULE_CARD_CLASS, 'space-y-2')}>
              {rt ? <h3 className="m-0 font-ui text-[18px] font-semibold text-v-fg">{rt}</h3> : null}
              {rd ? <p className={`m-0 ${VAULT_MODULE_DESCRIPTION_TYPO} !text-left`}>{rd}</p> : null}
            </div>
          )
        })
        .filter(Boolean)
      if (cells.length === 0) return null
      return (
        <div className="w-full space-y-6">
          <VaultModuleHeader title={titleRaw || undefined} />
          <div className="grid gap-4 md:grid-cols-2">{cells}</div>
        </div>
      )
    }

    case 'KeyInformationModule': {
      const titleRaw = typeof c.title === 'string' ? c.title.trim() : ''
      const rowsRaw = Array.isArray(c.rows) ? c.rows : []
      const rows = rowsRaw
        .map((raw) => {
          const row = raw as Record<string, unknown>
          return {
            label: typeof row.label === 'string' ? row.label : '',
            value: typeof row.value === 'string' ? row.value : '',
          }
        })
        .filter((r) => r.label.trim() !== '' || r.value.trim() !== '')
      const ctaLabel = typeof c.ctaLabel === 'string' ? c.ctaLabel.trim() : ''
      const ctaHref = typeof c.ctaHref === 'string' ? c.ctaHref.trim() : ''
      return (
        <KeyInformationTab
          {...(titleRaw ? { title: titleRaw } : {})}
          rows={rows}
          {...(ctaLabel && ctaHref ? { ctaLabel, ctaHref } : {})}
        />
      )
    }

    case 'FaqAccordionModule': {
      return <VaultFaqAccordionModuleWeb content={c} />
    }

    case 'MarktingCardLargePortrait':
      return <VaultMarketingLargePortraitWeb content={c} />

    case 'MarketingCardsSmallCarouselModule':
      return <VaultMarketingCardsCarouselWeb content={c} />

    case 'MarketingCardsSmallSlidingCarrousel_Portrait':
      return <VaultMarketingCardsCarouselWeb content={c} portrait />

    case 'MarketingCardsSmallSlidingCarrousel_Paysage':
      return <VaultMarketingCardsCarouselWeb content={c} />

    case 'AllocationModule':
      return <VaultAllocationModuleWeb content={c} />

    case 'PerformanceChart':
      return <VaultPerformanceChartWeb content={c} />

    case 'TransactionLatest10Module':
      return <VaultTransactionLatestModuleWeb content={c} />

    case 'ContentBasDePageSansModuleBlanc': {
      const markdown = typeof c.markdown === 'string' ? c.markdown : ''
      if (!markdown.trim()) return null
      return (
        <div className="rounded-v-card border border-dashed border-v-fg-20 bg-v-bg-warm/60 p-4 md:p-5">
          <div className={vaultProseMarkdownClass('text-left')}>
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        </div>
      )
    }

    case 'HEADING': {
      const headingText = typeof c.text === 'string' ? c.text.trim() : ''
      if (!headingText) return null
      const headingId = slugifyHeading(headingText)
      return (
        <h2
          id={headingId}
          className={VAULT_MODULE_HEADING_CLASS}
        >
          <ArticleBodyMarkdown text={headingText} variant="inline" />
        </h2>
      )
    }

    case 'PARAGRAPH': {
      const fromText = typeof c.text === 'string' ? c.text : ''
      const fromMd = typeof c.markdown === 'string' ? c.markdown : ''
      const body = fromText.trim().length > 0 ? fromText : fromMd
      if (!body.trim()) return null
      return (
        <div
          className={cn(VAULT_PARAGRAPH_BODY_READING_TYPO, 'not-italic my-6')}
        >
          <ReactMarkdown
            remarkPlugins={[...articleBodyRemarkPlugins]}
            components={articleBodyMarkdownComponents}
          >
            {body}
          </ReactMarkdown>
        </div>
      )
    }

    case 'QUOTE': {
      const q = typeof c.text === 'string' ? c.text : ''
      if (!q.trim()) return null
      return (
        <ArticleBodyQuoteBlock
          quote={q}
          author={typeof c.author === 'string' ? c.author : undefined}
        />
      )
    }

    case 'BULLET_LIST': {
      const rawItems = Array.isArray(c.items) ? c.items : []
      const items = rawItems.filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
      if (!items.length) return null
      return <ArticleBodyBulletListBlock items={items} />
    }

    case 'NUMBERED_LIST': {
      const rawItems = Array.isArray(c.items) ? c.items : []
      const items = rawItems.filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
      if (!items.length) return null
      return (
        <ol
          className={cn(
            'my-8 list-outside list-decimal space-y-3 pl-6 marker:font-semibold',
            VAULT_PARAGRAPH_BODY_READING_TYPO,
          )}
        >
          {items.map((item, i) => (
            <li key={i} className="pl-1">
              <ArticleBodyMarkdown text={item} variant="inline" />
            </li>
          ))}
        </ol>
      )
    }

    default:
      return null
  }
}

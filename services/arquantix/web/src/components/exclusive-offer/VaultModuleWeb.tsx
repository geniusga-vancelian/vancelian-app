'use client'

import Link from 'next/link'
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
  VAULT_MODULE_MARKDOWN_BODY_TYPO,
} from '@/components/design-system'
import {
  HeroOfferTagChip,
  HERO_OFFER_TAG_GAP_CLASS,
} from '@/components/design-system/heroOfferTagChip'
import { ArticleStepsModule } from '@/components/design-system/ArticleStepsModule'
import { KeyInformationTab } from '@/components/exclusive-offer/KeyInformationTab'
import { VaultMediaCarousel } from '@/components/exclusive-offer/VaultMediaCarousel'
import { VaultVideoBlockArticle } from '@/components/exclusive-offer/VaultVideoBlockArticle'
import { VaultLocalisationModuleWeb } from '@/components/exclusive-offer/VaultLocalisationModuleWeb'
import { VaultDocumentsListModuleWeb } from '@/components/exclusive-offer/VaultDocumentsListModuleWeb'
import { VaultFundingModuleSection } from '@/components/exclusive-offer/VaultFundingModuleSection'

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
      <div
        className={cn(
          'prose prose-neutral w-full max-w-none text-justify prose-p:text-justify prose-a:text-indigo-600',
          VAULT_MODULE_MARKDOWN_BODY_TYPO,
          'prose-p:text-inherit prose-li:text-inherit prose-strong:text-inherit',
        )}
      >
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
                <a href={href} className="text-indigo-600 underline-offset-2 hover:underline">
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
  const c = mod.content

  switch (mod.type) {
    case 'TitlePage': {
      const title = typeof c.title === 'string' ? c.title : ''
      const subtitle = typeof c.subtitle === 'string' ? c.subtitle : ''
      return (
        <div className="space-y-3">
          {title ? (
            <h1 className="font-['Avenir:Heavy',sans-serif] text-3xl tracking-tight text-neutral-900 md:text-[2.5rem] md:leading-tight">
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
            <div
              key={i}
              className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm"
            >
              {rt ? <h3 className="font-semibold text-neutral-900">{rt}</h3> : null}
              {rd ? <p className={`mt-2 ${VAULT_MODULE_DESCRIPTION_TYPO}`}>{rd}</p> : null}
            </div>
          )
        })
        .filter(Boolean)
      if (cells.length === 0) return null
      return (
        <div className="rounded-xl border border-neutral-200 bg-neutral-50/80 p-6">
          {titleRaw ? (
            <h2 className="mb-6 font-['Avenir:Heavy',sans-serif] text-xl text-neutral-900">
              {titleRaw}
            </h2>
          ) : null}
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

    case 'StepsModule': {
      return (
        <div className="w-full">
          <ArticleStepsModule content={c} />
        </div>
      )
    }

    case 'FaqAccordionModule': {
      const titleRaw = typeof c.title === 'string' ? c.title.trim() : ''
      const introRaw = typeof c.intro === 'string' ? c.intro.trim() : ''
      const footerLabel = typeof c.footerLinkLabel === 'string' ? c.footerLinkLabel.trim() : ''
      const coll = typeof c.footerCollectionSlug === 'string' ? c.footerCollectionSlug.trim() : ''
      const cat = typeof c.footerCategorySlug === 'string' ? c.footerCategorySlug.trim() : ''
      const helpHref = coll && cat ? `/help/${coll}/${cat}` : coll ? `/help/${coll}` : '/help'
      if (!titleRaw && !introRaw && !footerLabel) {
        return null
      }
      return (
        <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
          {titleRaw ? (
            <h2 className="mb-2 font-['Avenir:Heavy',sans-serif] text-xl text-neutral-900">
              {titleRaw}
            </h2>
          ) : null}
          {introRaw ? <p className={VAULT_MODULE_DESCRIPTION_TYPO}>{introRaw}</p> : null}
          {footerLabel ? (
            <Link
              href={helpHref}
              className="mt-4 inline-flex text-sm font-medium text-indigo-600 hover:underline"
            >
              {footerLabel}
            </Link>
          ) : null}
        </div>
      )
    }

    case 'ContentBasDePageSansModuleBlanc': {
      const markdown = typeof c.markdown === 'string' ? c.markdown : ''
      if (!markdown.trim()) return null
      return (
        <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50/50 p-4">
          <div
            className={cn(
              'prose prose-neutral max-w-none',
              VAULT_MODULE_MARKDOWN_BODY_TYPO,
              'prose-p:text-inherit prose-li:text-inherit prose-strong:text-inherit',
            )}
          >
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        </div>
      )
    }

    default:
      // Fallback "unknown module" : visible uniquement en cas d'incohérence schéma/CMS.
      // Non user-facing en production : exempté du garde-fou i18n vault (cf. vaultHardcodedStringsScanner).
      return (
        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 text-sm text-amber-900">
          {/* i18n-allow-next-line: fallback admin/debug — module inconnu */}
          <p className="font-medium">Module « {mod.type} »</p>
          {/* i18n-allow-next-line: fallback admin/debug — module inconnu */}
          <p className="mt-1 text-xs text-amber-800">
            {/* i18n-allow-next-line: fallback admin/debug — module inconnu */}
            Rendu web générique — affinage possible dans VaultModuleWeb.
          </p>
        </div>
      )
  }
}

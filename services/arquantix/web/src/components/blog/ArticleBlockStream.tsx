import { ArticleBlockType } from '@prisma/client'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'
import {
  articleBodyMarkdownComponents,
  articleBodyRemarkPlugins,
} from '@/lib/blog/articleBodyMarkdown'
import { VAULT_PARAGRAPH_BODY_READING_TYPO } from '@/components/design-system'
import { figmaDsLinksClassName } from '@/components/design-system/extracted'
import { ArticleBodyBulletListBlock } from '@/components/design-system/ArticleBodyBulletListBlock'
import { ArticleBodyQuoteBlock } from '@/components/design-system/ArticleBodyQuoteBlock'

export {
  articleBodyMarkdownComponents,
  articleBodyRemarkPlugins,
} from '@/lib/blog/articleBodyMarkdown'
import { ArticleStepsModule } from '@/components/design-system/ArticleStepsModule'
import { VaultDocumentsListModuleWeb } from '@/components/exclusive-offer/VaultDocumentsListModuleWeb'
import { KeyInformationTab } from '@/components/exclusive-offer/KeyInformationTab'
import { VaultLocalisationModuleWeb } from '@/components/exclusive-offer/VaultLocalisationModuleWeb'
import { VaultMediaCarousel } from '@/components/exclusive-offer/VaultMediaCarousel'
import { VaultVideoBlockArticle } from '@/components/exclusive-offer/VaultVideoBlockArticle'
import HowItWorksDS from '@/components/design-system/HowItWorks'
import type { PublicArticleBlock } from '@/lib/blog/getPublicArticle'

export interface ArticleHeading {
  id: string
  text: string
  level: number
}

export function slugifyHeading(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

/**
 * Titre de bloc « module » (étapes, infos clés, carrousel, etc.) : entrée du sommaire
 * + ancre `module-<blockId>` (évite les collisions de slug entre modules).
 */
function registerModuleTocEntry(
  headings: ArticleHeading[],
  block: PublicArticleBlock,
  title: string,
): string | null {
  const t = title.trim()
  if (!t) return null
  const id = `module-${block.id}`
  headings.push({ id, text: t, level: 2 })
  return id
}

function renderBlock(
  block: PublicArticleBlock,
  headings: ArticleHeading[],
): { element: React.ReactNode; heading?: ArticleHeading } {
  switch (block.type) {
    case ArticleBlockType.HEADING: {
      const headingText = (block.data as { text?: string }).text || ''
      const headingId = slugifyHeading(headingText)
      const heading: ArticleHeading = {
        id: headingId,
        text: headingText,
        level: 2,
      }
      headings.push(heading)
      return {
        element: (
          <h2
            id={headingId}
            className={cn(
              figmaDsLinksClassName,
              'mt-14 scroll-mt-28 text-[26px] leading-[1.1] text-black first:mt-0 md:text-[28px]',
            )}
          >
            {headingText}
          </h2>
        ),
        heading,
      }
    }
    case ArticleBlockType.PARAGRAPH:
      return {
        element: (
          <div className={cn(VAULT_PARAGRAPH_BODY_READING_TYPO, 'not-italic my-6')}>
            <ReactMarkdown
              remarkPlugins={[...articleBodyRemarkPlugins]}
              components={articleBodyMarkdownComponents}
            >
              {String((block.data as { text?: string }).text ?? '')}
            </ReactMarkdown>
          </div>
        ),
      }
    case ArticleBlockType.QUOTE:
      return {
        element: (
          <ArticleBodyQuoteBlock
            quote={String((block.data as { text?: string }).text ?? '')}
            author={(block.data as { author?: string }).author}
          />
        ),
      }
    case ArticleBlockType.BULLET_LIST:
      return {
        element: (
          <ArticleBodyBulletListBlock
            items={((block.data as { items?: string[] }).items || []) as string[]}
          />
        ),
      }
    case ArticleBlockType.NUMBERED_LIST:
      return {
        element: (
          <ol className="my-8 list-outside list-decimal space-y-3 pl-6 text-[17px] leading-relaxed text-[#2a2d35] marker:font-semibold md:text-[18px]">
            {((block.data as { items?: string[] }).items || []).map((item, i) => (
              <li key={i} className="pl-1">
                {item}
              </li>
            ))}
          </ol>
        ),
      }
    case ArticleBlockType.IMAGE: {
      const d = (block.data || {}) as { mediaId?: string; caption?: string }
      const url = block.imageUrl || ''
      const mediaId = typeof d.mediaId === 'string' ? d.mediaId : ''
      const caption = typeof d.caption === 'string' ? d.caption.trim() : ''
      if (!url) {
        return {
          element: (
            <div className="my-10 flex h-64 w-full items-center justify-center rounded-[14px] bg-[#e8edf5] text-[#8893b0]">
              Image
            </div>
          ),
        }
      }
      return {
        element: (
          <div className="my-10 w-full min-w-0">
            <VaultMediaCarousel
              moduleTitle=""
              description=""
              items={[{ url, mediaId, alt: null }]}
            />
            {caption ? (
              <p className="mt-3 text-center text-[13px] text-[#8893b0]">{caption}</p>
            ) : null}
          </div>
        ),
      }
    }
    case ArticleBlockType.VIDEO: {
      const videoUrl = (block.data as { url?: string }).url || ''
      const videoId = videoUrl.includes('youtube.com/watch?v=')
        ? videoUrl.split('v=')[1]?.split('&')[0]
        : videoUrl.includes('youtu.be/')
          ? videoUrl.split('youtu.be/')[1]?.split('?')[0]
          : videoUrl.includes('vimeo.com/')
            ? videoUrl.split('vimeo.com/')[1]?.split('?')[0]
            : null
      return {
        element: (
          <figure className="my-10">
            {videoId ? (
              <div className="aspect-video w-full overflow-hidden rounded-[14px] bg-black">
                {videoUrl.includes('vimeo.com') ? (
                  <iframe
                    src={`https://player.vimeo.com/video/${videoId}`}
                    className="h-full w-full"
                    allow="autoplay; fullscreen; picture-in-picture"
                    allowFullScreen
                    title="Video"
                  />
                ) : (
                  <iframe
                    src={`https://www.youtube.com/embed/${videoId}`}
                    className="h-full w-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    title="Video"
                  />
                )}
              </div>
            ) : (
              <div className="flex h-64 w-full items-center justify-center rounded-[14px] bg-[#e8edf5] text-[#8893b0]">
                Vidéo
              </div>
            )}
            {(block.data as { caption?: string }).caption ? (
              <figcaption className="mt-3 text-center text-[13px] text-[#62656e]">
                {(block.data as { caption?: string }).caption}
              </figcaption>
            ) : null}
          </figure>
        ),
      }
    }
    case ArticleBlockType.DOCUMENT: {
      const docData = block.data as { url?: string; title?: string }
      const docUrl = docData.url || ''
      const docTitle = docData.title || 'Document'
      return {
        element: (
          <div className="my-6">
            <a
              href={docUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 rounded-[12px] border border-[#dfe3ee] p-4 transition-colors hover:bg-[#f7f9ff]"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#e8edf5] text-[10px] font-semibold">
                PDF
              </div>
              <p className="min-w-0 flex-1 truncate font-medium text-[#1a1d24]">{docTitle}</p>
              <svg className="h-5 w-5 shrink-0 text-[#8893b0]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
          </div>
        ),
      }
    }
    case ArticleBlockType.MEDIA_IMAGE_CAROUSEL: {
      const c = (block.data || {}) as Record<string, unknown>
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
      if (!items.length) {
        return { element: null }
      }
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <VaultMediaCarousel
              moduleTitle={moduleTitle}
              description={description}
              items={items}
            />
          </div>
        ),
      }
    }
    case ArticleBlockType.LOCALISATION: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : ''
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <VaultLocalisationModuleWeb content={c} />
          </div>
        ),
      }
    }
    case ArticleBlockType.DOCUMENTS_LIST: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle : ''
      const description = typeof c.description === 'string' ? c.description : ''
      const subtitle = typeof c.subtitle === 'string' ? c.subtitle.trim() : ''
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
      if (!items.length) {
        return { element: null }
      }
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <VaultDocumentsListModuleWeb
              subtitle={subtitle}
              moduleTitle={moduleTitle}
              description={description}
              items={items}
            />
          </div>
        ),
      }
    }
    case ArticleBlockType.KEY_INFORMATION: {
      const c = (block.data || {}) as Record<string, unknown>
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
      if (rows.length === 0) {
        return { element: null }
      }
      const tocId = titleRaw ? registerModuleTocEntry(headings, block, titleRaw) : null
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <KeyInformationTab
              {...(titleRaw ? { title: titleRaw } : {})}
              rows={rows}
              {...(ctaLabel && ctaHref ? { ctaLabel, ctaHref } : {})}
            />
          </div>
        ),
      }
    }
    case ArticleBlockType.VIDEO_BLOCK_ARTICLE: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.title === 'string' ? c.title.trim() : ''
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <VaultVideoBlockArticle content={c} />
          </div>
        ),
      }
    }
    case ArticleBlockType.STEPS_MODULE: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.title === 'string' ? c.title.trim() : ''
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <ArticleStepsModule content={c} />
          </div>
        ),
      }
    }
    case ArticleBlockType.HOW_IT_WORKS_CAROUSEL: {
      // Rendu direct du composant DS `HowItWorks` (et NON `SectionHowItWorksCms`) :
      // dans le contexte article, le layout parent fournit déjà fond blanc +
      // container ; passer par `SectionHowItWorksCms` ajouterait un
      // `<section bg-white><Container>` redondant qui s'affiche comme une
      // « sur-enveloppe blanche » autour du module. La structure JSON du bloc
      // reste identique à la section CMS `how_it_works` (cf. `library.ts`,
      // `howItWorksSchema`), seul le wrapper extérieur diffère.
      // L'enrichissement `steps[].imageMediaId` → `steps[].imageMediaUrl`
      // est fait côté serveur par `enrichPublicArticleBlockData`.
      const c = (block.data || {}) as Record<string, unknown>
      const label = typeof c.label === 'string' ? c.label : undefined
      const title = typeof c.title === 'string' ? c.title : undefined
      const subtitle = typeof c.subtitle === 'string' ? c.subtitle : undefined
      const hideStepNumbering = c.hideStepNumbering === true
      const steps = Array.isArray(c.steps)
        ? (c.steps as Array<Record<string, unknown>>).map((s) => ({
            number: typeof s.number === 'string' ? s.number : '',
            title: typeof s.title === 'string' ? s.title : '',
            description: typeof s.description === 'string' ? s.description : '',
            ...(typeof s.imageMediaUrl === 'string'
              ? { imageMediaUrl: s.imageMediaUrl }
              : {}),
            ...(typeof s.imageMediaAlt === 'string'
              ? { imageMediaAlt: s.imageMediaAlt }
              : {}),
            ...(typeof s.stepButtonLabel === 'string'
              ? { stepButtonLabel: s.stepButtonLabel }
              : {}),
            ...(typeof s.stepButtonHref === 'string'
              ? { stepButtonHref: s.stepButtonHref }
              : {}),
          }))
        : undefined
      const primaryCtaText = typeof c.primaryCtaText === 'string' ? c.primaryCtaText.trim() : ''
      const primaryCtaHref = typeof c.primaryCtaHref === 'string' ? c.primaryCtaHref.trim() : ''
      const secondaryCtaText = typeof c.secondaryCtaText === 'string' ? c.secondaryCtaText.trim() : ''
      const secondaryCtaHref = typeof c.secondaryCtaHref === 'string' ? c.secondaryCtaHref.trim() : ''
      const tocTitle = (title ?? '').trim() || (label ?? '').trim()
      const tocId = registerModuleTocEntry(headings, block, tocTitle)
      return {
        element: (
          <div
            className={cn('my-10 w-full min-w-0', tocId && 'scroll-mt-28')}
            id={tocId ?? undefined}
          >
            <HowItWorksDS
              label={label}
              title={title}
              subtitle={subtitle}
              hideStepNumbering={hideStepNumbering}
              {...(steps && steps.length > 0 ? { steps } : {})}
              surface="light"
              {...(primaryCtaText
                ? {
                    primaryCta: {
                      text: primaryCtaText,
                      ...(primaryCtaHref ? { href: primaryCtaHref } : {}),
                    },
                  }
                : {})}
              {...(secondaryCtaText
                ? {
                    secondaryCta: {
                      text: secondaryCtaText,
                      ...(secondaryCtaHref ? { href: secondaryCtaHref } : {}),
                    },
                  }
                : {})}
            />
          </div>
        ),
      }
    }
    default:
      return { element: null }
  }
}

export function buildArticleBlockElements(blocks: PublicArticleBlock[]) {
  const headings: ArticleHeading[] = []
  const elements = blocks.map((block) => {
    const { element } = renderBlock(block, headings)
    return { blockId: block.id, element }
  })
  return { elements, headings }
}

/** Bloc “inline” documents issus des métadonnées article (hors `ArticleBlock`). */
export function DocumentAttachmentRow({
  url,
  title,
}: {
  url: string
  title: string
}) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-[12px] border border-[#dfe3ee] p-4 transition-colors hover:bg-[#f7f9ff]"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#e8edf5] text-[10px] font-semibold">
        PDF
      </div>
      <p className="min-w-0 flex-1 truncate font-medium text-[#1a1d24]">{title}</p>
    </a>
  )
}

'use client'

import React, { useState } from 'react'
import { ArticleBlockType } from '@prisma/client'
import ReactMarkdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'

import { PortalDsImageCarousel } from '@/components/portal/invest/PortalDsImageCarousel'
import { PortalImageMosaic } from '@/components/portal/invest/PortalImageMosaic'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { articleBodyRemarkPlugins } from '@/lib/blog/articleBodyMarkdown'
import type { PublicArticleBlock } from '@/lib/blog/getPublicArticle'
import {
  PortalArticleMarkdown,
  portalArticleBodyMarkdownComponents,
} from '@/lib/portal/portalArticleBodyMarkdown'
import {
  readCarouselItems,
  readDocumentResources,
  readKeyInformationMetrics,
  readStepsTimeline,
  readVideoItems,
  type PortalVaultTimelineStep,
} from '@/lib/portal/vaultModulePortalFormat'
import { getYouTubeVideoIdFromUrl } from '@/lib/youtubeEmbed'
import { cn } from '@/lib/utils'

export type ArticleHeading = {
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

function ModuleSection({
  tocId,
  title,
  children,
}: {
  tocId: string | null
  title?: string
  children: React.ReactNode
}) {
  return (
    <section className={cn(tocId && 'scroll-mt-28')} id={tocId ?? undefined}>
      {title ? (
        <h2 id={tocId ?? undefined} className="art-prose__h2">
          <PortalArticleMarkdown text={title} variant="inline" />
        </h2>
      ) : null}
      {children}
    </section>
  )
}

function timelineMarker(state: PortalVaultTimelineStep['state']) {
  if (state === 'done') {
    return (
      <span className="marker marker--done" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    )
  }
  if (state === 'current') {
    return <span className="marker marker--current" aria-label="In progress" />
  }
  return <span className="marker marker--pending" aria-hidden="true" />
}

function PortalArticleVideoFigure({
  posterUrl,
  videoUrl,
  caption,
}: {
  posterUrl?: string | null
  videoUrl?: string | null
  caption?: string | null
}) {
  const [playing, setPlaying] = useState(false)
  const videoId = videoUrl ? getYouTubeVideoIdFromUrl(videoUrl) : null
  const isVimeo = Boolean(videoUrl?.includes('vimeo.com/'))
  const vimeoId = isVimeo ? videoUrl?.split('vimeo.com/')[1]?.split('?')[0] : null

  if (playing && (videoId || vimeoId)) {
    return (
      <figure className="art-prose__video">
        <div className="aspect-video w-full overflow-hidden rounded-[var(--v-radius-card)] bg-black">
          {isVimeo && vimeoId ? (
            <iframe
              src={`https://player.vimeo.com/video/${vimeoId}?autoplay=1`}
              className="h-full w-full border-0"
              allow="autoplay; fullscreen; picture-in-picture"
              allowFullScreen
              title="Video"
            />
          ) : (
            <iframe
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
              className="h-full w-full border-0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              title="Video"
            />
          )}
        </div>
        {caption ? (
          <figcaption className="art-prose__video-cap">
            <PortalArticleMarkdown text={caption} variant="inline" />
          </figcaption>
        ) : null}
      </figure>
    )
  }

  return (
    <figure className="art-prose__video">
      <button
        type="button"
        className="art-prose__video-play"
        style={posterUrl ? { backgroundImage: `url(${posterUrl})` } : undefined}
        aria-label="Play video"
        onClick={() => setPlaying(true)}
      >
        <span className="art-prose__video-btn" aria-hidden="true">
          <KalaiIcon name="play" size={24} />
        </span>
      </button>
      {caption ? (
        <figcaption className="art-prose__video-cap">
          <PortalArticleMarkdown text={caption} variant="inline" />
        </figcaption>
      ) : null}
    </figure>
  )
}

function renderPortalArticleBlock(
  block: PublicArticleBlock,
  headings: ArticleHeading[],
): { element: React.ReactNode } {
  switch (block.type) {
    case ArticleBlockType.HEADING: {
      const headingText = (block.data as { text?: string }).text || ''
      const headingId = slugifyHeading(headingText)
      headings.push({ id: headingId, text: headingText, level: 2 })
      return {
        element: (
          <h2 id={headingId} className="art-prose__h2">
            <PortalArticleMarkdown text={headingText} variant="inline" />
          </h2>
        ),
      }
    }
    case ArticleBlockType.PARAGRAPH: {
      const text = String((block.data as { text?: string }).text ?? '')
      if (!text.trim()) return { element: null }
      return {
        element: (
          <ReactMarkdown
            remarkPlugins={[...articleBodyRemarkPlugins]}
            components={portalArticleBodyMarkdownComponents}
          >
            {text}
          </ReactMarkdown>
        ),
      }
    }
    case ArticleBlockType.QUOTE: {
      const text = String((block.data as { text?: string }).text ?? '')
      const author = (block.data as { author?: string }).author
      if (!text.trim()) return { element: null }
      return {
        element: (
          <blockquote className="art-prose__quote">
            <span className="art-prose__quote-mark" aria-hidden="true">
              &ldquo;
            </span>
            <div className="art-prose__quote-text">
              <PortalArticleMarkdown text={text} variant="inline" />
            </div>
            {author ? (
              <cite className="art-prose__quote-cite">
                &mdash; <PortalArticleMarkdown text={author} variant="inline" />
              </cite>
            ) : null}
          </blockquote>
        ),
      }
    }
    case ArticleBlockType.BULLET_LIST: {
      const items = ((block.data as { items?: string[] }).items || []) as string[]
      if (!items.length) return { element: null }
      return {
        element: (
          <ul className="art-prose__check">
            {items.map((item, i) => (
              <li key={i} className="art-prose__check-item">
                <span className="art-prose__check-ic" aria-hidden="true">
                  <KalaiIcon name="check" size={16} />
                </span>
                <span className="min-w-0 flex-1">
                  <PortalArticleMarkdown text={item} variant="inline" />
                </span>
              </li>
            ))}
          </ul>
        ),
      }
    }
    case ArticleBlockType.NUMBERED_LIST: {
      const items = ((block.data as { items?: string[] }).items || []) as string[]
      if (!items.length) return { element: null }
      return {
        element: (
          <ol className="art-prose__ol">
            {items.map((item, i) => (
              <li key={i} className="art-prose__ol-item">
                <PortalArticleMarkdown text={item} variant="inline" />
              </li>
            ))}
          </ol>
        ),
      }
    }
    case ArticleBlockType.IMAGE: {
      const d = (block.data || {}) as { mediaId?: string; caption?: string }
      const url = block.imageUrl || ''
      const caption = typeof d.caption === 'string' ? d.caption.trim() : ''
      if (!url) return { element: null }
      return {
        element: (
          <figure className="m-0">
            <div className="art-prose__grid" style={{ gridTemplateColumns: '1fr' }}>
              <span
                className="art-prose__grid-cell"
                style={{ backgroundImage: `url(${url})`, aspectRatio: '16 / 9' }}
                role="img"
                aria-label={caption || 'Image'}
              />
            </div>
            {caption ? (
              <figcaption className="art-prose__video-cap">
                <PortalArticleMarkdown text={caption} variant="inline" />
              </figcaption>
            ) : null}
          </figure>
        ),
      }
    }
    case ArticleBlockType.VIDEO: {
      const d = block.data as { url?: string; caption?: string }
      const videoUrl = d.url || ''
      const caption = typeof d.caption === 'string' ? d.caption.trim() : ''
      const videoId = getYouTubeVideoIdFromUrl(videoUrl)
      const posterUrl = videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : null
      if (!videoUrl) return { element: null }
      return {
        element: (
          <PortalArticleVideoFigure posterUrl={posterUrl} videoUrl={videoUrl} caption={caption || null} />
        ),
      }
    }
    case ArticleBlockType.DOCUMENT: {
      const docData = block.data as { url?: string; title?: string }
      const docUrl = docData.url || ''
      const docTitle = docData.title || 'Document'
      if (!docUrl) return { element: null }
      return {
        element: <PortalArticleDocumentRow url={docUrl} title={docTitle} />,
      }
    }
    case ArticleBlockType.MEDIA_IMAGE_CAROUSEL: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : ''
      const description = typeof c.description === 'string' ? c.description.trim() : ''
      const items = readCarouselItems(c)
      if (!items.length) return { element: null }
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      const photos = items.map((item) => item.url)
      const galleryLabel = moduleTitle || items.find((item) => item.alt)?.alt || 'Photo gallery'

      if (photos.length <= 3) {
        return {
          element: (
            <ModuleSection tocId={tocId} title={moduleTitle || undefined}>
              {description ? <PortalArticleMarkdown text={description} /> : null}
              <PortalImageMosaic items={items} />
            </ModuleSection>
          ),
        }
      }

      return {
        element: (
          <ModuleSection tocId={tocId} title={moduleTitle || undefined}>
            {description ? <PortalArticleMarkdown text={description} /> : null}
            <div className="portal-gallery portal-gallery--desktop">
              <PortalImageMosaic items={items} />
            </div>
            <div className="portal-gallery portal-gallery--mobile">
              <PortalDsImageCarousel photos={photos} variant="gallery" ariaLabel={galleryLabel} />
            </div>
          </ModuleSection>
        ),
      }
    }
    case ArticleBlockType.LOCALISATION: {
      const c = (block.data || {}) as Record<string, unknown>
      const title = typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : 'Location'
      const address = typeof c.description === 'string' ? c.description.trim() : ''
      const embedUrl = typeof c.embedUrl === 'string' ? c.embedUrl.trim() : ''
      if (!address && !embedUrl) return { element: null }
      const tocId = registerModuleTocEntry(headings, block, title)
      return {
        element: (
          <ModuleSection tocId={tocId} title={title}>
            <div className="map-card">
              <div className={cn('map', embedUrl && 'map--embed')}>
                {embedUrl ? (
                  <iframe
                    title="Map"
                    src={embedUrl}
                    className="map__iframe"
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                  />
                ) : null}
              </div>
              {address ? (
                <div className="map-card__body">
                  <h3 className="map-card__title">Address</h3>
                  <p className="map-card__sub">
                    <PortalArticleMarkdown text={address} variant="inline" />
                  </p>
                </div>
              ) : null}
            </div>
          </ModuleSection>
        ),
      }
    }
    case ArticleBlockType.DOCUMENTS_LIST: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : 'Documents'
      const description = typeof c.description === 'string' ? c.description.trim() : ''
      const resources = readDocumentResources(c)
      if (!resources.length) return { element: null }
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <ModuleSection tocId={tocId} title={moduleTitle}>
            {description ? <PortalArticleMarkdown text={description} /> : null}
            <div className="docs">
              {resources.map((resource, i) => (
                <div className="row" key={`${resource.downloadUrl}-${i}`}>
                  <div className="row__avatar" aria-hidden="true">
                    <KalaiIcon name="file" size={16} />
                  </div>
                  <div className="row__body">
                    <h3 className="row__title">
                      <PortalArticleMarkdown text={resource.name} variant="inline" />
                    </h3>
                    <p className="row__sub">
                      {resource.type}
                      {resource.size ? ` · ${resource.size}` : ''}
                    </p>
                  </div>
                  <div className="row__trailing">
                    <a
                      href={resource.downloadUrl}
                      className="icon-btn icon-btn--outline"
                      aria-label="Download"
                      target="_blank"
                      rel="noopener noreferrer"
                      download
                    >
                      <KalaiIcon name="download" size={18} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </ModuleSection>
        ),
      }
    }
    case ArticleBlockType.KEY_INFORMATION: {
      const c = (block.data || {}) as Record<string, unknown>
      const title = typeof c.title === 'string' ? c.title.trim() : ''
      const metrics = readKeyInformationMetrics(c)
      if (!metrics.length) return { element: null }
      const tocId = title ? registerModuleTocEntry(headings, block, title) : null
      return {
        element: (
          <ModuleSection tocId={tocId} title={title || undefined}>
            <div className="stats stats--lined">
              {metrics.map((row, i) => (
                <div className="stat" key={`${row.key}-${i}`}>
                  <span className="stat__label">
                    <span className="lead" aria-hidden="true">
                      <KalaiIcon name={row.icon} size={16} />
                    </span>
                    <PortalArticleMarkdown text={row.key} variant="inline" />
                  </span>
                  <span className="stat__value">
                    <PortalArticleMarkdown text={row.value} variant="inline" />
                  </span>
                </div>
              ))}
            </div>
          </ModuleSection>
        ),
      }
    }
    case ArticleBlockType.VIDEO_BLOCK_ARTICLE: {
      const c = (block.data || {}) as Record<string, unknown>
      const moduleTitle = typeof c.title === 'string' ? c.title.trim() : ''
      const items = readVideoItems(c)
      if (!items.length) return { element: null }
      const tocId = registerModuleTocEntry(headings, block, moduleTitle)
      return {
        element: (
          <ModuleSection tocId={tocId} title={moduleTitle || undefined}>
            <div className="grid gap-4 md:grid-cols-2">
              {items.map((item, i) => (
                <PortalArticleVideoFigure
                  key={`${item.videoUrl}-${i}`}
                  posterUrl={item.posterImageUrl || null}
                  videoUrl={item.videoUrl || null}
                  caption={item.title || item.date || null}
                />
              ))}
            </div>
          </ModuleSection>
        ),
      }
    }
    case ArticleBlockType.STEPS_MODULE: {
      const c = (block.data || {}) as Record<string, unknown>
      const title = typeof c.title === 'string' ? c.title.trim() : ''
      const steps = readStepsTimeline(c)
      if (!steps.length) return { element: null }
      const tocId = registerModuleTocEntry(headings, block, title || 'Timeline')
      return {
        element: (
          <ModuleSection tocId={tocId} title={title || 'Timeline'}>
            <div className="stepper">
              {steps.map((step, i) => (
                <div className="step" key={i}>
                  {timelineMarker(step.state)}
                  <div className="step__body">
                    <div className={cn('step__title', step.state === 'future' && 'dim')}>
                      <PortalArticleMarkdown text={step.label} variant="inline" />
                      {step.chip ? (
                        <span className="tag">
                          <PortalArticleMarkdown text={step.chip} variant="inline" />
                        </span>
                      ) : null}
                    </div>
                    {step.sub ? (
                      <p className="step__sub">
                        <PortalArticleMarkdown text={step.sub} variant="inline" />
                      </p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </ModuleSection>
        ),
      }
    }
    case ArticleBlockType.HOW_IT_WORKS_CAROUSEL: {
      const c = (block.data || {}) as Record<string, unknown>
      const label = typeof c.label === 'string' ? c.label.trim() : ''
      const title = typeof c.title === 'string' ? c.title.trim() : ''
      const subtitle = typeof c.subtitle === 'string' ? c.subtitle.trim() : ''
      const steps = Array.isArray(c.steps)
        ? (c.steps as Array<Record<string, unknown>>)
            .map((s) => ({
              number: typeof s.number === 'string' ? s.number : '',
              title: typeof s.title === 'string' ? s.title : '',
              description: typeof s.description === 'string' ? s.description : '',
              imageMediaUrl: typeof s.imageMediaUrl === 'string' ? s.imageMediaUrl : '',
              stepButtonLabel: typeof s.stepButtonLabel === 'string' ? s.stepButtonLabel : '',
              stepButtonHref: typeof s.stepButtonHref === 'string' ? s.stepButtonHref : '',
            }))
            .filter((s) => s.title.trim())
        : []
      if (!steps.length && !title && !subtitle) return { element: null }
      const tocTitle = title || label || 'How it works'
      const tocId = registerModuleTocEntry(headings, block, tocTitle)
      const primaryCtaText = typeof c.primaryCtaText === 'string' ? c.primaryCtaText.trim() : ''
      const primaryCtaHref = typeof c.primaryCtaHref === 'string' ? c.primaryCtaHref.trim() : ''
      const secondaryCtaText = typeof c.secondaryCtaText === 'string' ? c.secondaryCtaText.trim() : ''
      const secondaryCtaHref = typeof c.secondaryCtaHref === 'string' ? c.secondaryCtaHref.trim() : ''

      return {
        element: (
          <ModuleSection tocId={tocId} title={tocTitle}>
            {label && !title ? (
              <p className="art-hero__section m-0">
                <PortalArticleMarkdown text={label} variant="inline" />
              </p>
            ) : null}
            {subtitle ? <PortalArticleMarkdown text={subtitle} /> : null}
            {steps.length > 0 ? (
              <ol className="art-prose__ol">
                {steps.map((step, i) => (
                  <li key={i} className="art-prose__ol-item">
                    <div className="space-y-3">
                      <div>
                        {step.number ? (
                          <span className="font-ui text-[12px] font-semibold uppercase tracking-wide text-v-fg-muted">
                            <PortalArticleMarkdown text={step.number} variant="inline" />
                          </span>
                        ) : null}
                        <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">
                          <PortalArticleMarkdown text={step.title} variant="inline" />
                        </p>
                        {step.description ? (
                          <p className="m-0 mt-1 font-ui text-[15px] leading-relaxed text-v-fg-body">
                            <PortalArticleMarkdown text={step.description} variant="inline" />
                          </p>
                        ) : null}
                      </div>
                      {step.imageMediaUrl ? (
                        <span
                          className="art-prose__grid-cell block"
                          style={{ backgroundImage: `url(${step.imageMediaUrl})`, aspectRatio: '16 / 9' }}
                          role="img"
                          aria-label=""
                        />
                      ) : null}
                      {step.stepButtonLabel && step.stepButtonHref ? (
                        <a href={step.stepButtonHref} className="btn btn--secondary btn--sm">
                          <PortalArticleMarkdown text={step.stepButtonLabel} variant="inline" />
                        </a>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ol>
            ) : null}
            {primaryCtaText || secondaryCtaText ? (
              <div className="flex flex-wrap gap-3 pt-2">
                {primaryCtaText ? (
                  <a
                    href={primaryCtaHref || '#'}
                    className="btn btn--primary btn--sm"
                  >
                    <PortalArticleMarkdown text={primaryCtaText} variant="inline" />
                  </a>
                ) : null}
                {secondaryCtaText ? (
                  <a
                    href={secondaryCtaHref || '#'}
                    className="btn btn--secondary btn--sm"
                  >
                    <PortalArticleMarkdown text={secondaryCtaText} variant="inline" />
                  </a>
                ) : null}
              </div>
            ) : null}
          </ModuleSection>
        ),
      }
    }
    default:
      return { element: null }
  }
}

export function buildPortalArticleBlockElements(blocks: PublicArticleBlock[]) {
  const headings: ArticleHeading[] = []
  const elements = blocks.map((block) => {
    const { element } = renderPortalArticleBlock(block, headings)
    return { blockId: block.id, element }
  })
  return { elements, headings }
}

/** Ligne document (métadonnées article ou bloc DOCUMENT) — DS portail `docs .row`. */
export function PortalArticleDocumentRow({ url, title }: { url: string; title: string }) {
  return (
    <div className="docs">
      <div className="row">
        <div className="row__avatar" aria-hidden="true">
          <KalaiIcon name="file" size={16} />
        </div>
        <div className="row__body">
          <h3 className="row__title">
            <PortalArticleMarkdown text={title} variant="inline" />
          </h3>
          <p className="row__sub">PDF</p>
        </div>
        <div className="row__trailing">
          <a
            href={url}
            className="icon-btn icon-btn--outline"
            aria-label="Download"
            target="_blank"
            rel="noopener noreferrer"
          >
            <KalaiIcon name="download" size={18} />
          </a>
        </div>
      </div>
    </div>
  )
}

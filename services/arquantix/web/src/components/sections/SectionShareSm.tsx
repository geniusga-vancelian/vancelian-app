import { Link2 } from 'lucide-react'

import {
  ArticleShareFacebookIcon,
  ArticleShareInstagramIcon,
  ArticleShareLinkedInIcon,
  ArticleShareXIcon,
  ArticleShareYoutubeIcon,
} from '@/components/blog/article-share-icons'
import { figmaDsTitleSmallClassName } from '@/components/design-system/extracted'
import { cn } from '@/lib/utils'

export type ShareSmPlatform = 'facebook' | 'x' | 'linkedin' | 'instagram' | 'youtube' | 'link'

export type ShareSmItem = {
  platform?: ShareSmPlatform | string
  label: string
  href: string
}

const iconButtonClass =
  'grid size-6 shrink-0 select-none place-items-center rounded-full bg-black text-white transition-colors hover:bg-neutral-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-black'

/** Remplace les jetons `{{url}}`, `{{encodedUrl}}`, `{{title}}`, `{{encodedTitle}}`, `{{encodedShareText}}`. */
export function interpolateShareSmHref(template: string, pageUrl: string, articleTitle: string): string {
  const encodedUrl = encodeURIComponent(pageUrl)
  const encodedTitle = encodeURIComponent(articleTitle)
  const encodedShareText = encodeURIComponent(`${articleTitle}\n\n${pageUrl}`)
  return template
    .replace(/\{\{encodedShareText\}\}/g, encodedShareText)
    .replace(/\{\{encodedUrl\}\}/g, encodedUrl)
    .replace(/\{\{encodedTitle\}\}/g, encodedTitle)
    .replace(/\{\{url\}\}/g, pageUrl)
    .replace(/\{\{title\}\}/g, articleTitle)
}

function normalizeItems(raw: unknown): ShareSmItem[] {
  if (!Array.isArray(raw)) return []
  const out: ShareSmItem[] = []
  for (const row of raw) {
    if (row == null || typeof row !== 'object' || Array.isArray(row)) continue
    const o = row as Record<string, unknown>
    const label = typeof o.label === 'string' ? o.label.trim() : ''
    const href = typeof o.href === 'string' ? o.href.trim() : ''
    const platform =
      typeof o.platform === 'string' && o.platform.trim() !== '' ? o.platform.trim() : 'link'
    if (!label || !href) continue
    out.push({ platform: platform as ShareSmPlatform, label, href })
  }
  return out
}

function ShareSmGlyph({ platform }: { platform: string }) {
  switch (platform) {
    case 'facebook':
      return <ArticleShareFacebookIcon className="text-white" />
    case 'x':
      return <ArticleShareXIcon className="text-white" />
    case 'linkedin':
      return <ArticleShareLinkedInIcon className="text-white" />
    case 'instagram':
      return <ArticleShareInstagramIcon className="text-white" />
    case 'youtube':
      return <ArticleShareYoutubeIcon className="text-white" />
    default:
      return <Link2 className="size-3.5 text-white" strokeWidth={2} aria-hidden />
  }
}

type Props = {
  title?: string
  items: unknown
  pageUrl: string
  articleTitle: string
  className?: string
}

/**
 * Module CMS **shareSM** : titre + liste de liens réseaux (libellé + URL ou modèle avec `{{encodedUrl}}`, etc.).
 */
export function SectionShareSm({ title, items, pageUrl, articleTitle, className }: Props) {
  const list = normalizeItems(items)
  const heading = typeof title === 'string' ? title.trim() : ''
  if (!heading && list.length === 0) return null

  return (
    <div className={cn('mb-8', className)}>
      {heading ? (
        <p className={`${figmaDsTitleSmallClassName} mb-5 text-[#0f1219]`}>{heading}</p>
      ) : null}
      {list.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2.5">
          {list.map((item, i) => {
            const href = interpolateShareSmHref(item.href, pageUrl, articleTitle)
            const p = item.platform || 'link'
            return (
              <a
                key={`${p}-${item.label}-${i}`}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className={iconButtonClass}
                aria-label={item.label}
              >
                <ShareSmGlyph platform={p} />
              </a>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

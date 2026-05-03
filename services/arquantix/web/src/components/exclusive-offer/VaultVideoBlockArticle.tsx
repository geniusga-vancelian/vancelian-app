'use client'

import { useState } from 'react'
import { Play } from 'lucide-react'
import { usePathname } from 'next/navigation'

import { SIMPLE_MARKDOWN_MODULE_TITLE_TYPO } from '@/components/design-system'
import type { Locale } from '@/config/locales'
import { getYouTubeVideoIdFromUrl } from '@/lib/youtubeEmbed'
import { getActiveLocaleFromPathname } from '@/lib/i18n/publicLocalizedRouting'
import { vaultCommonCta } from '@/lib/i18n/vaultCommonCta'
import { cn } from '@/lib/utils'

type VideoItem = {
  title: string
  posterImageUrl: string
  videoUrl: string
  date: string
}

function parseItems(content: Record<string, unknown>): VideoItem[] {
  const raw = content.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((it) => {
      const row = it != null && typeof it === 'object' ? (it as Record<string, unknown>) : {}
      return {
        title: typeof row.title === 'string' ? row.title : '',
        posterImageUrl: typeof row.posterImageUrl === 'string' ? row.posterImageUrl : '',
        videoUrl: typeof row.videoUrl === 'string' ? row.videoUrl : '',
        date: typeof row.date === 'string' ? row.date : '',
      }
    })
    .filter((item) => {
      const poster = item.posterImageUrl.trim()
      const yt = getYouTubeVideoIdFromUrl(item.videoUrl)
      return poster.length > 0 && yt != null
    })
}

function VideoCard({
  item,
  priority,
  locale,
}: {
  item: VideoItem
  priority: boolean
  locale: Locale
}) {
  const videoId = getYouTubeVideoIdFromUrl(item.videoUrl)
  const [showEmbed, setShowEmbed] = useState(false)
  const watch = vaultCommonCta(locale, 'watch_video')
  const watchYt = vaultCommonCta(locale, 'watch_video_youtube')
  const iframeTitleFallback = vaultCommonCta(locale, 'video_iframe_fallback')

  if (!videoId) return null

  return (
    <article className="overflow-hidden rounded-2xl border border-neutral-200 shadow-sm">
      <button
        type="button"
        onClick={() => setShowEmbed(true)}
        className={cn(
          'group relative block w-full overflow-hidden bg-neutral-900 text-left',
          showEmbed && 'hidden',
        )}
        aria-label={item.title ? `${watch}: ${item.title}` : watchYt}
      >
        {/* Même ratio que l’iframe YouTube (`aspect-video` = 16/9) pour éviter tout saut à la lecture. */}
        <div className="relative aspect-video w-full">
          {/* eslint-disable-next-line @next/next/no-img-element -- URL présignée / CMS */}
          <img
            src={item.posterImageUrl}
            alt=""
            className="h-full w-full object-cover transition duration-300 group-hover:opacity-95"
            loading={priority ? 'eager' : 'lazy'}
            decoding="async"
          />
          <div
            className="absolute inset-0 bg-black/25 transition group-hover:bg-black/35"
            aria-hidden
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-black/45 shadow-lg ring-2 ring-white/90 backdrop-blur-[2px] transition group-hover:scale-105">
              <Play
                className="h-9 w-9 text-white"
                fill="white"
                strokeWidth={0}
                aria-hidden
              />
            </span>
          </div>
        </div>
      </button>

      {showEmbed ? (
        <div className="relative aspect-video w-full bg-black">
          <iframe
            className="absolute inset-0 h-full w-full"
            src={`https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            title={item.title.trim() || iframeTitleFallback}
          />
        </div>
      ) : null}
    </article>
  )
}

/**
 * Module vault [VideoBlockArticleModule] : cartes poster + lecture YouTube inline (iframe au clic).
 * N’affiche rien si aucune carte valide (poster + lien YouTube).
 */
export function VaultVideoBlockArticle({ content }: { content: Record<string, unknown> }) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  const items = parseItems(content)
  if (items.length === 0) return null

  const moduleTitle = typeof content.title === 'string' ? content.title.trim() : ''

  const list = (
    <div className="flex flex-col gap-8">
      {items.map((item, i) => (
        <VideoCard
          key={`${item.videoUrl}-${i}`}
          item={item}
          priority={i === 0}
          locale={loc}
        />
      ))}
    </div>
  )

  return (
    <div className="w-full">
      {moduleTitle ? (
        <>
          <h2 className={SIMPLE_MARKDOWN_MODULE_TITLE_TYPO}>{moduleTitle}</h2>
          <div className="mt-16">{list}</div>
        </>
      ) : (
        list
      )}
    </div>
  )
}

'use client'

import React from 'react'

import { getYouTubeVideoIdFromUrl } from '@/lib/youtubeEmbed'

type Props = {
  videoUrl: string
}

function vimeoIdFromUrl(url: string): string | null {
  const match = url.trim().match(/vimeo\.com\/(?:video\/)?(\d+)/i)
  return match?.[1] ?? null
}

function isDirectVideoUrl(url: string): boolean {
  return /\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(url.trim())
}

function youtubeEmbedSrc(videoId: string): string {
  const params = new URLSearchParams({
    autoplay: '1',
    mute: '1',
    controls: '0',
    loop: '1',
    playlist: videoId,
    playsinline: '1',
    modestbranding: '1',
    rel: '0',
    showinfo: '0',
    iv_load_policy: '3',
    disablekb: '1',
    fs: '0',
  })
  return `https://www.youtube.com/embed/${videoId}?${params.toString()}`
}

/** Vidéo promo hero — lecture auto muette en arrière-plan (prioritaire sur l’image cover). */
export function PortalHeroBackgroundVideo({ videoUrl }: Props) {
  const url = videoUrl.trim()
  if (!url) return null

  const youtubeId = getYouTubeVideoIdFromUrl(url)
  if (youtubeId) {
    return (
      <div className="dh-article__video" aria-hidden>
        <iframe
          src={youtubeEmbedSrc(youtubeId)}
          title=""
          className="dh-article__video-iframe"
          allow="autoplay; encrypted-media; picture-in-picture"
          referrerPolicy="strict-origin-when-cross-origin"
        />
      </div>
    )
  }

  const vimeoId = vimeoIdFromUrl(url)
  if (vimeoId) {
    const params = new URLSearchParams({
      autoplay: '1',
      muted: '1',
      background: '1',
      loop: '1',
      autopause: '0',
      title: '0',
      byline: '0',
      portrait: '0',
    })
    return (
      <div className="dh-article__video" aria-hidden>
        <iframe
          src={`https://player.vimeo.com/video/${vimeoId}?${params.toString()}`}
          title=""
          className="dh-article__video-iframe"
          allow="autoplay; fullscreen; picture-in-picture"
          referrerPolicy="strict-origin-when-cross-origin"
        />
      </div>
    )
  }

  if (isDirectVideoUrl(url) || url.startsWith('http')) {
    return (
      <video
        className="dh-article__video-native"
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        src={url}
        aria-hidden
      />
    )
  }

  return null
}

'use client'

import * as React from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { parseEditorialTitle } from '@/lib/cms/parseEditorialTitle'

export interface VOfferCardProps {
  href?: string
  ariaLabel?: string
  /** Image poster (optionnelle — sinon 1ʳᵉ frame vidéo). */
  coverImageUrl?: string
  /** Vidéo au survol / viewport (DS `offer-card`). */
  hoverVideoUrl?: string
  /** Texte centré overlay — accepte `<em>`. */
  centerText?: string
  barTitle?: string
  barSubtitle?: string
  barRate?: string
  className?: string
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden>
      <path d="M12 22s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  )
}

/** Carte offre exclusive DS (`offer-card`). */
export function VOfferCard({
  href = '#',
  ariaLabel,
  coverImageUrl,
  hoverVideoUrl,
  centerText,
  barTitle,
  barSubtitle,
  barRate,
  className,
}: VOfferCardProps) {
  const cardRef = React.useRef<HTMLAnchorElement>(null)
  const videoRef = React.useRef<HTMLVideoElement>(null)
  const [videoReady, setVideoReady] = React.useState(false)

  React.useEffect(() => {
    const card = cardRef.current
    const video = videoRef.current
    if (!card || !video || !hoverVideoUrl?.trim()) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const canHover = window.matchMedia('(hover: hover)').matches
    let started = false

    const markReady = () => setVideoReady(true)
    if (video.readyState >= 2) markReady()
    else video.addEventListener('loadeddata', markReady, { once: true })

    const safePlay = () => {
      const p = video.play()
      if (p && typeof p.catch === 'function') p.catch(() => {})
    }

    const ensureLoaded = () => {
      if (started) return
      started = true
      video.load()
    }

    if (canHover) {
      const enter = () => {
        if (reduceMotion) return
        ensureLoaded()
        safePlay()
      }
      const leave = () => {
        video.pause()
        try {
          video.currentTime = 0
        } catch {
          /* noop */
        }
      }
      card.addEventListener('pointerenter', enter)
      card.addEventListener('pointerleave', leave)
      card.addEventListener('focusin', enter)
      card.addEventListener('focusout', leave)
      return () => {
        card.removeEventListener('pointerenter', enter)
        card.removeEventListener('pointerleave', leave)
        card.removeEventListener('focusin', enter)
        card.removeEventListener('focusout', leave)
      }
    }

    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              ensureLoaded()
              if (!reduceMotion) safePlay()
            } else {
              video.pause()
            }
          })
        },
        { threshold: 0.5 },
      )
      io.observe(card)
      return () => io.disconnect()
    }
  }, [hoverVideoUrl])

  const centerNode = centerText?.trim() ? parseEditorialTitle(centerText) : null

  return (
    <Link
      ref={cardRef}
      href={href}
      aria-label={ariaLabel || barTitle}
      className={cn(
        'group relative isolate block aspect-[3/4] overflow-hidden rounded-v-lg border border-v-fg-10 bg-v-card text-inherit no-underline shadow-v-subtle',
        'transition-[box-shadow,border-color] duration-[320ms] ease-v-out hover:border-v-fg-20 hover:shadow-v-medium',
        className,
      )}
    >
      <div className="absolute inset-0 z-0">
        {coverImageUrl?.trim() ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={coverImageUrl}
            alt=""
            className="h-full w-full object-cover transition-transform duration-[320ms] ease-v-out group-hover:scale-[1.03]"
          />
        ) : hoverVideoUrl?.trim() ? (
          <video
            ref={videoRef}
            src={hoverVideoUrl}
            muted
            loop
            playsInline
            preload="metadata"
            className="h-full w-full object-cover"
            aria-hidden
          />
        ) : (
          <div className="h-full w-full bg-v-fg-05" />
        )}
        {hoverVideoUrl?.trim() && coverImageUrl?.trim() ? (
          <video
            ref={videoRef}
            src={hoverVideoUrl}
            muted
            loop
            playsInline
            preload="none"
            aria-hidden
            className={cn(
              'pointer-events-none absolute inset-0 h-full w-full object-cover transition-[opacity,transform] duration-[320ms] ease-v-out',
              videoReady ? 'opacity-0 group-hover:opacity-100 group-hover:scale-[1.03]' : 'opacity-0',
              'max-[hover:none]:opacity-100 max-[hover:none]:group-hover:opacity-100',
            )}
          />
        ) : null}
      </div>

      <div
        className="pointer-events-none absolute inset-0 z-[2] bg-gradient-to-b from-[rgba(20,18,8,0.10)] via-transparent via-[28%] to-[rgba(20,18,8,0.50)]"
        aria-hidden
      />

      {centerNode ? (
        <div className="absolute inset-0 z-[4] flex flex-col items-center justify-center gap-3 p-6 text-center text-white">
          <p className="m-0 font-ui text-[clamp(20px,1.9vw,26px)] font-normal leading-[1.2] [text-shadow:0_1px_8px_rgba(20,18,8,0.30)] text-balance">
            {centerNode}
          </p>
        </div>
      ) : null}

      {(barTitle || barSubtitle || barRate) && (
        <div className="absolute bottom-3 left-3 right-3 z-[5] grid grid-cols-[32px_1fr_auto] items-center gap-3 rounded-2xl border border-white/[0.22] bg-white/[0.16] px-3.5 py-2.5 text-white shadow-[0_12px_32px_rgba(20,18,8,0.22)] backdrop-blur-[40px] backdrop-saturate-[180%]">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-v-fg text-white">
            <PinIcon />
          </span>
          <div className="min-w-0">
            {barTitle ? (
              <p className="m-0 truncate font-ui text-[13px] font-semibold leading-[1.25]">{barTitle}</p>
            ) : null}
            {barSubtitle ? (
              <p className="m-0 truncate font-ui text-[12px] font-normal leading-[1.3] text-white/85">
                {barSubtitle}
              </p>
            ) : null}
          </div>
          {barRate ? (
            <span className="font-ui text-[13px] font-semibold leading-none whitespace-nowrap">
              {barRate}
            </span>
          ) : null}
        </div>
      )}
    </Link>
  )
}

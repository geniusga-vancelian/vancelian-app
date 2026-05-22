'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { VEditorialTitle } from './VEditorialTitle'
import { VIosNotif } from './VIosNotif'
import { parseEditorialTitle } from '@/lib/cms/parseEditorialTitle'
import { useJourneyScrollParallax } from '@/hooks/useJourneyScrollParallax'

export interface VJourneyCta {
  label: string
  href?: string
  variant?: 'primary' | 'secondary'
}

export interface VJourneyProps {
  pill?: string
  title?: string
  description?: string
  backgroundMediaUrl?: string
  /** `video` si l’URL pointe vers un mp4/webm. */
  backgroundMediaKind?: 'video' | 'image'
  notificationMessage?: string
  ctas?: VJourneyCta[]
  className?: string
}

/** Section storytelling fullbleed (`journey`). */
export function VJourney({
  pill,
  title,
  description,
  backgroundMediaUrl,
  backgroundMediaKind = 'video',
  notificationMessage,
  ctas = [],
  className,
}: VJourneyProps) {
  const hasMedia = Boolean(backgroundMediaUrl?.trim())
  const titleNode = title ? parseEditorialTitle(title) : null
  const sectionRef = React.useRef<HTMLElement>(null)
  const mediaRef = React.useRef<HTMLVideoElement | HTMLImageElement>(null)
  const innerRef = React.useRef<HTMLDivElement>(null)
  useJourneyScrollParallax(sectionRef, mediaRef, innerRef, hasMedia)

  return (
    <section
      ref={sectionRef}
      data-nav-surface="dark"
      className={cn(
        'v-journey relative isolate flex min-h-[640px] h-[100vh] max-h-[900px] w-full items-center overflow-hidden bg-[#141208] text-white',
        className,
      )}
    >
      {hasMedia ? (
        <div className="pointer-events-none absolute inset-0 -z-10" aria-hidden>
          {backgroundMediaKind === 'video' ? (
            <video
              ref={mediaRef as React.RefObject<HTMLVideoElement>}
              className="v-journey__media absolute inset-[-25%_0] h-[150%] w-full object-cover"
              autoPlay
              muted
              loop
              playsInline
              preload="auto"
              src={backgroundMediaUrl}
            />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              ref={mediaRef as React.RefObject<HTMLImageElement>}
              src={backgroundMediaUrl}
              alt=""
              className="v-journey__media absolute inset-[-25%_0] h-[150%] w-full object-cover"
            />
          )}
          <div className="absolute inset-0 bg-[rgba(20,18,8,0.35)]" />
        </div>
      ) : null}

      <div
        ref={innerRef}
        className="v-journey__inner mx-auto flex w-full max-w-[640px] flex-col items-center gap-5 px-12 text-center md:px-6 sm:px-4"
      >
        {pill?.trim() ? (
          <span className="inline-flex h-7 items-center rounded-v-pill border border-white/[0.28] bg-white/[0.14] px-3.5 font-ui text-[12px] font-medium uppercase tracking-[0.08em] backdrop-blur-[24px]">
            {pill}
          </span>
        ) : null}

        {titleNode ? (
          <VEditorialTitle as="h2" size="page" tone="inverse" align="center">
            {titleNode}
          </VEditorialTitle>
        ) : null}

        {description?.trim() ? (
          <p className="m-0 max-w-[480px] font-ui text-[16px] font-normal leading-[1.55] text-white/85">
            {description}
          </p>
        ) : null}

        {notificationMessage?.trim() ? (
          <VIosNotif message={notificationMessage} />
        ) : null}

        {ctas.length > 0 ? (
          <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
            {ctas.map((cta, i) => {
              const v = cta.variant === 'primary' ? 'darkPrimary' : 'darkSecondary'
              const content = (
                <>
                  <span>{cta.label}</span>
                  <span aria-hidden="true">→</span>
                </>
              )
              if (cta.href) {
                return (
                  <Button key={i} asChild variant={v} size="default">
                    <a href={cta.href}>{content}</a>
                  </Button>
                )
              }
              return (
                <Button key={i} variant={v} size="default">
                  {content}
                </Button>
              )
            })}
          </div>
        ) : null}
      </div>
    </section>
  )
}

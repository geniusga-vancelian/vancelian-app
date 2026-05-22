'use client'

import * as React from 'react'

function supportsViewTimeline(): boolean {
  if (typeof window === 'undefined') return false
  return Boolean(window.CSS?.supports?.('animation-timeline', 'view()'))
}

/**
 * Parallax + fade-in contenu journey — fallback JS pour Safari / Firefox
 * sans `animation-timeline: view()` (spec Home.html).
 */
export function useJourneyScrollParallax(
  sectionRef: React.RefObject<HTMLElement | null>,
  mediaRef: React.RefObject<HTMLElement | null>,
  innerRef: React.RefObject<HTMLElement | null>,
  enabled = true,
): void {
  React.useEffect(() => {
    if (!enabled) return
    if (typeof window === 'undefined') return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    if (supportsViewTimeline()) return

    const section = sectionRef.current
    const media = mediaRef.current
    const inner = innerRef.current
    if (!section || !media) return

    media.style.willChange = 'transform'
    if (inner) inner.style.willChange = 'transform, opacity'

    let ticking = false

    const update = () => {
      ticking = false
      const h = window.innerHeight || 1
      const r = section.getBoundingClientRect()
      const total = r.height + h
      let p = (h - r.top) / total
      p = Math.min(1, Math.max(0, p))

      const translate = (p - 0.5) * -h * 0.3
      media.style.transform = `translate3d(0, ${translate.toFixed(2)}px, 0)`

      if (inner) {
        const enter = Math.min(1, Math.max(0, (p - 0.1) / 0.25))
        const drift = (1 - enter) * 40
        inner.style.opacity = enter.toFixed(3)
        inner.style.transform = `translate3d(0, ${drift.toFixed(2)}px, 0)`
      }
    }

    const onScroll = () => {
      if (!ticking) {
        ticking = true
        window.requestAnimationFrame(update)
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    update()

    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      media.style.transform = ''
      media.style.willChange = ''
      if (inner) {
        inner.style.opacity = ''
        inner.style.transform = ''
        inner.style.willChange = ''
      }
    }
  }, [enabled, sectionRef, mediaRef, innerRef])
}

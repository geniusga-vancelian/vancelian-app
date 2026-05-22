'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'

const FADE_SELECTOR = '[data-v-scroll-fade]'

/**
 * Fondu + dérive vertical au scroll (spec Home.html).
 * Opacité 1 tant que le centre de l’élément est sous 35 % du viewport,
 * puis fade + translateY(-60px max) en sortie vers le haut.
 */
export function useScrollSectionFade(enabled = true): void {
  const pathname = usePathname()

  React.useEffect(() => {
    if (!enabled) return
    if (typeof window === 'undefined') return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return

    let fadeEls: HTMLElement[] = []
    let ticking = false

    const collect = () => {
      fadeEls = Array.from(document.querySelectorAll<HTMLElement>(FADE_SELECTOR))
      fadeEls.forEach((el) => {
        el.style.willChange = 'transform, opacity'
      })
    }

    const update = () => {
      ticking = false
      const h = window.innerHeight || 1
      const startAt = h * 0.35
      const endAt = -h * 0.1

      fadeEls.forEach((el) => {
        const r = el.getBoundingClientRect()
        const center = r.top + r.height / 2
        let t = (center - endAt) / (startAt - endAt)
        t = Math.min(1, Math.max(0, t))
        const drift = (1 - t) * -60
        el.style.opacity = t.toFixed(3)
        el.style.transform = `translate3d(0, ${drift.toFixed(2)}px, 0)`
      })
    }

    const onScroll = () => {
      if (!ticking) {
        ticking = true
        window.requestAnimationFrame(update)
      }
    }

    collect()
    onScroll()

    // Re-scan après navigation client ou hydratation tardive des sections CMS.
    const rescanTimer = window.setTimeout(() => {
      collect()
      onScroll()
    }, 120)

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)

    return () => {
      window.clearTimeout(rescanTimer)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      fadeEls.forEach((el) => {
        el.style.opacity = ''
        el.style.transform = ''
        el.style.willChange = ''
      })
    }
  }, [enabled, pathname])
}

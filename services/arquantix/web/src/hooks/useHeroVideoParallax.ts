'use client'

import * as React from 'react'

/** Parallax scroll sur la vidéo de fond du hero (0.5× + zoom léger), spec Home.html. */
export function useHeroVideoParallax(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  enabled: boolean,
): void {
  React.useEffect(() => {
    if (!enabled) return
    if (typeof window === 'undefined') return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return

    const video = videoRef.current
    if (!video) return

    video.style.willChange = 'transform'
    let ticking = false

    const update = () => {
      ticking = false
      const y = window.scrollY || window.pageYOffset || 0
      const h = window.innerHeight || 1
      const p = Math.min(1, Math.max(0, y / h))
      const translate = y * 0.5
      const scale = 1 + p * 0.05
      video.style.transform = `translate3d(0, ${translate.toFixed(2)}px, 0) scale(${scale.toFixed(4)})`
    }

    const onScroll = () => {
      if (!ticking) {
        ticking = true
        window.requestAnimationFrame(update)
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    onScroll()

    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      video.style.transform = ''
      video.style.willChange = ''
    }
  }, [enabled, videoRef])
}

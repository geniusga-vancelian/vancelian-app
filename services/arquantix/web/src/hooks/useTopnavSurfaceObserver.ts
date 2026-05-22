'use client'

import * as React from 'react'

/**
 * États visuels du `topnav` Vancelian (cf. pack handoff `components/topnav/topnav.css`).
 *
 * - `transparent` : aucun scroll, au-dessus d'un hero photo → texte/logo blancs.
 * - `solid`       : `window.scrollY > 0`, fond `--v-bg`, texte anthracite.
 * - `warm`        : une section `[data-nav-surface="warm"]` (équivalent `.start`
 *                   dans le DS) passe sous la barre → fond `--v-card-warm`.
 * - `dark`        : une section `[data-nav-surface="dark"]` (équivalent
 *                   `.final-cta` / `.mid-cta` / `.footer` du DS) passe sous la
 *                   barre → fond `#141208`, texte/logo blancs.
 *
 * Priorité (du plus haut au plus bas) : `dark` > `warm` > `solid` > `transparent`.
 */
export type TopnavSurface = 'transparent' | 'solid' | 'warm' | 'dark'

/** Hauteur du topnav Vancelian — strict 72px partout (DS officiel). */
export const TOPNAV_HEIGHT_PX = 72

/**
 * Sélecteur des sections à observer. Chaque section qui passe sous la nav
 * peut déclarer son influence via l'attribut `data-nav-surface`.
 *
 * Convention :
 * - `data-nav-surface="warm"` → fond `--v-card-warm` (sections éditoriales chaudes)
 * - `data-nav-surface="dark"` → fond `#141208` (VFinalCta, VTestimonial fullbleed, Footer)
 *
 * Toute autre valeur est ignorée. Une section sans attribut n'influence rien.
 */
const SURFACE_ATTR = 'data-nav-surface'
const SURFACE_SELECTOR = `[${SURFACE_ATTR}="warm"], [${SURFACE_ATTR}="dark"]`

/**
 * Vancelian — observe les sections marquées sous la nav fixe et bascule
 * automatiquement l'état visuel du topnav (équivalent React de `topnav.js`).
 *
 * Mécanique :
 * 1. À chaque scroll/resize, on regarde toutes les sections `[data-nav-surface]`.
 * 2. La barre regarde la section qui croise sa ligne inférieure (`top <= 72 && bottom > 72`).
 * 3. Si plusieurs sections croisent, `dark` gagne sur `warm` (sécurité).
 * 4. Sinon : `solid` si `scrollY > 0`, `transparent` sinon.
 *
 * SSR : retourne `'transparent'` côté serveur (état neutre).
 */
export function useTopnavSurfaceObserver(): TopnavSurface {
  const [surface, setSurface] = React.useState<TopnavSurface>('transparent')

  React.useEffect(() => {
    if (typeof window === 'undefined') return

    let rafId: number | null = null

    const check = () => {
      rafId = null
      const navBottom = TOPNAV_HEIGHT_PX
      const sections = document.querySelectorAll<HTMLElement>(SURFACE_SELECTOR)
      let warm = false
      let dark = false
      sections.forEach((el) => {
        const r = el.getBoundingClientRect()
        if (r.top <= navBottom && r.bottom > navBottom) {
          const k = el.getAttribute(SURFACE_ATTR)
          if (k === 'dark') dark = true
          else if (k === 'warm') warm = true
        }
      })
      const scrolled =
        (window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0) > 0
      let next: TopnavSurface = 'transparent'
      if (dark) next = 'dark'
      else if (warm) next = 'warm'
      else if (scrolled) next = 'solid'
      setSurface((prev) => (prev === next ? prev : next))
    }

    const schedule = () => {
      if (rafId != null) return
      rafId = window.requestAnimationFrame(check)
    }

    check()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)

    // Observe DOM changes — pages SPA peuvent monter/démonter des sections.
    const mo = new MutationObserver(schedule)
    mo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: [SURFACE_ATTR] })

    return () => {
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
      mo.disconnect()
      if (rafId != null) window.cancelAnimationFrame(rafId)
    }
  }, [])

  return surface
}

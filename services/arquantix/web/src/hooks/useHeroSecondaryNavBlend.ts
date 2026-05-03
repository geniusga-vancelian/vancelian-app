'use client'

import * as React from 'react'

const NAV_H_MD = 60
const NAV_H_SM = 56
/**
 * Distance (px) parcourue par le haut du titre **après** qu’il commence à passer sous la navbar
 * (bord bas de la barre = `navH`) pour passer de l’overlay sombre (t = 0) à la barre claire (t = 1).
 */
const SCROLL_TRANSITION_PX = 80

/** Placé sur le bloc titre du hero (`SectionHero`) — la transition démarre quand ce point atteint la navbar. */
export const HERO_NAV_BLEND_ANCHOR_ID = 'hero-nav-blend-anchor'

/** Courbe douce sur [0, 1] pour éviter un passage linéaire trop « mécanique » au scroll. */
function smoothstep01(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  return x * x * (3 - 2 * x)
}

/**
 * `titleTop` = getBoundingClientRect().top du h1. Tant que le titre est entièrement sous la barre
 * (`titleTop >= navH`), l’overlay reste sombre. La transition démarre dès que le titre entre dans
 * la zone sous la barre (`titleTop < navH`) et se poursuit sur `SCROLL_TRANSITION_PX` px de défilement.
 */
function computeBlendFromTitleTop(titleTop: number, navH: number): number {
  if (titleTop >= navH) return 0
  const end = navH - SCROLL_TRANSITION_PX
  if (titleTop <= end) return 1
  return (navH - titleTop) / SCROLL_TRANSITION_PX
}

/** Repli : bas de section si l’ancre titre est absente — même échelle que le titre. */
function computeBlendFromSectionBottom(sectionBottom: number, navH: number): number {
  if (sectionBottom >= navH + SCROLL_TRANSITION_PX) return 0
  if (sectionBottom <= navH) return 1
  return (navH + SCROLL_TRANSITION_PX - sectionBottom) / SCROLL_TRANSITION_PX
}

/**
 * 0 = nav transparente au-dessus du hero (texte clair), 1 = barre claire / givrée après défilement.
 * Priorité : bord **supérieur** du titre (`#hero-nav-blend-anchor`) — la transition démarre lorsque
 * ce bord passe **sous** la barre fixe, puis progresse sur ~`SCROLL_TRANSITION_PX` px de scroll.
 * Sinon repli sur le bas de la section `anchorId`.
 */
/** Après navigation client, le hero peut ne pas être monté tout de suite : on évite blend=1 tant que la section n’existe pas. */
const HERO_DOM_WAIT_FRAMES = 72

export function useTransparentHeroNavBlend(
  enabled: boolean,
  anchorId: string | null,
): number {
  const [blend, setBlend] = React.useState(enabled && anchorId ? 0 : 1)

  React.useLayoutEffect(() => {
    if (!enabled || !anchorId) {
      setBlend(1)
      return
    }

    const navHeight = () =>
      typeof window !== 'undefined' && window.matchMedia('(min-width: 768px)').matches
        ? NAV_H_MD
        : NAV_H_SM

    let rafWait = 0
    let waitFrames = 0

    const measureOnce = (): boolean => {
      const navH = navHeight()
      const titleEl = document.getElementById(HERO_NAV_BLEND_ANCHOR_ID)
      if (titleEl) {
        const titleTop = titleEl.getBoundingClientRect().top
        const linear = computeBlendFromTitleTop(titleTop, navH)
        setBlend(smoothstep01(linear))
        return true
      }
      const el = document.getElementById(anchorId)
      if (!el) {
        return false
      }
      const b = el.getBoundingClientRect().bottom
      const linear = computeBlendFromSectionBottom(b, navH)
      setBlend(smoothstep01(linear))
      return true
    }

    const onScrollOrResize = () => {
      measureOnce()
    }

    const waitForHeroDom = () => {
      if (measureOnce()) {
        return
      }
      setBlend(0)
      waitFrames++
      if (waitFrames >= HERO_DOM_WAIT_FRAMES) {
        setBlend(1)
        return
      }
      rafWait = requestAnimationFrame(waitForHeroDom)
    }

    waitForHeroDom()
    window.addEventListener('scroll', onScrollOrResize, { passive: true })
    window.addEventListener('resize', onScrollOrResize)
    return () => {
      cancelAnimationFrame(rafWait)
      window.removeEventListener('scroll', onScrollOrResize)
      window.removeEventListener('resize', onScrollOrResize)
    }
  }, [enabled, anchorId])

  return blend
}

/** @deprecated Utiliser `useTransparentHeroNavBlend(true, 'hero-secondary')`. */
export function useHeroSecondaryNavBlend(enabled: boolean): number {
  return useTransparentHeroNavBlend(enabled, enabled ? 'hero-secondary' : null)
}

export type HeroSecondaryNavPalette = {
  navBg: string
  navBorder: string
  inactivePill: string
  homeLink: string
  activeBg: string
  activeFg: string
}

/**
 * Intensité du flou d’arrière-plan (px) pendant la transition dark → light.
 * 0 en plein « dark » (t = 0) ; augmente avec t pour un rendu verre dépoli sur toute la barre.
 */
export function navBackdropBlurPx(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  if (x <= 0) return 0
  return Math.round(20 * x)
}

/** Couleurs interpolées entre overlay sombre (t=0) et thème barre claire (t=1). */
export function navPaletteForBlend(t: number): HeroSecondaryNavPalette {
  const x = Math.min(1, Math.max(0, t))
  const inactiveR = Math.round(255 - 157 * x)
  const inactiveG = Math.round(255 - 154 * x)
  const inactiveB = Math.round(255 - 145 * x)
  const homeK = Math.round(255 * (1 - x))
  const activeBg = Math.round(255 * (1 - x))
  const activeFg = Math.round(255 * x)
  /** Transparence progressive (plafond 0,94) pour laisser voir le backdrop-blur en fin de transition. */
  const navWhiteAlpha = x <= 0 ? 0 : Math.min(0.94, x * 0.92)
  return {
    navBg: `rgba(255,255,255,${navWhiteAlpha})`,
    navBorder: `rgba(243,243,243,${x})`,
    inactivePill: `rgb(${inactiveR},${inactiveG},${inactiveB})`,
    homeLink: `rgb(${homeK},${homeK},${homeK})`,
    activeBg: `rgb(${activeBg},${activeBg},${activeBg})`,
    activeFg: `rgb(${activeFg},${activeFg},${activeFg})`,
  }
}

/**
 * Hero blog (fond `neutral.gray100`) : barre transparente avec liens **foncés**,
 * puis transition vers barre givrée comme `navPaletteForBlend(1)`.
 */
export function navPaletteForLightSolidHeroBlend(t: number): HeroSecondaryNavPalette {
  const x = Math.min(1, Math.max(0, t))
  const navWhiteAlpha = x <= 0 ? 0 : Math.min(0.94, x * 0.92)
  return {
    navBg: `rgba(255,255,255,${navWhiteAlpha})`,
    navBorder: `rgba(243,243,243,${x})`,
    inactivePill: '#62656e',
    homeLink: '#000000',
    activeBg: '#000000',
    activeFg: '#ffffff',
  }
}

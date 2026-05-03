/**
 * État barre de navigation (thème + overlays hero) dérivé d’une route publique CMS.
 * Utilisé par le layout (SSR) et l’API client lors des navigations.
 */
import { prisma } from '@/lib/prisma'
import { getPageSections } from '@/lib/cms/content'
import { resolveHomePageCmsSlug } from '@/lib/cms/resolveHomePageCmsSlug'
import {
  shouldUseArticleReaderHeroUnderNav,
  shouldUseBlogHeroUnderNav,
  shouldUseHeroHomeImageOverlayLight,
  shouldUseHeroSecondaryImageOverlay,
} from '@/lib/cms/heroSecondaryNav'
import type { Locale } from '@/config/locales'

export type NavShellState = {
  themeColor: 'dark' | 'light'
  overlayHeroSecondary: boolean
  overlayHeroHomeLight: boolean
  /** Blog : `blog_hero` en tête — menu transparent sur fond neutre jusqu’au scroll. */
  overlayBlogHero: boolean
}

export const DEFAULT_NAV_SHELL: NavShellState = {
  themeColor: 'light',
  overlayHeroSecondary: false,
  overlayHeroHomeLight: false,
  overlayBlogHero: false,
}

async function resolveCmsSlugForPathname(pathname: string): Promise<string | null> {
  const p = (pathname || '/').replace(/\/$/, '') || '/'
  if (p === '/') {
    return resolveHomePageCmsSlug()
  }

  /** Prévisualisation admin : `/preview/{slug}` → page CMS `slug`. */
  if (p.startsWith('/preview/')) {
    const seg = p.slice('/preview/'.length).split('/').filter(Boolean)[0]
    return seg ?? null
  }

  const byUrl = await prisma.page.findFirst({
    where: { urlPath: p },
  })
  if (byUrl) return byUrl.slug

  const rawSegments = p.split('/').filter(Boolean)
  const hasLocalePrefix =
    rawSegments.length > 0 && /^(fr|en|it)$/i.test(rawSegments[0] || '')
  const segments = hasLocalePrefix ? rawSegments.slice(1) : rawSegments

  const normalizedPath =
    segments.length > 0 ? `/${segments.join('/')}` : '/'
  if (normalizedPath === '/') {
    return resolveHomePageCmsSlug()
  }

  const byNormalizedUrl = await prisma.page.findFirst({
    where: { urlPath: normalizedPath },
  })
  if (byNormalizedUrl) return byNormalizedUrl.slug

  if (segments.length === 2 && segments[0] === 'projects') {
    const row = await prisma.page.findUnique({
      where: { slug: segments[1] },
    })
    return row?.slug ?? null
  }
  if (segments.length === 1) {
    const row = await prisma.page.findUnique({
      where: { slug: segments[0] },
    })
    return row?.slug ?? null
  }

  return null
}

export type GetNavShellOptions = {
  /** Aligné sur la prévisualisation CMS (brouillon d’abord). */
  preferDraft?: boolean
}

/** Aperçu catalogue `/preview/section-demo/hero*` : pas de page CMS — état nav aligné sur le rendu réel du module. */
function navShellForSectionDemoHeroPath(pathname: string): NavShellState | null {
  const p = (pathname || '').replace(/\/$/, '') || '/'
  if (p === '/preview/section-demo/hero_secondary') {
    return {
      themeColor: 'dark',
      overlayHeroSecondary: true,
      overlayHeroHomeLight: false,
      overlayBlogHero: false,
    }
  }
  if (p === '/preview/section-demo/hero') {
    return {
      themeColor: 'light',
      overlayHeroSecondary: false,
      overlayHeroHomeLight: false,
      overlayBlogHero: false,
    }
  }
  if (
    p === '/preview/section-demo/blog_hero' ||
    p === '/preview/section-demo/blog_article_reader' ||
    p === '/preview/section-demo/blog_article_hero'
  ) {
    return {
      themeColor: 'light',
      overlayHeroSecondary: false,
      overlayHeroHomeLight: false,
      overlayBlogHero: true,
    }
  }
  return null
}

export async function getNavShellStateForPathname(
  pathname: string,
  locale: Locale,
  options?: GetNavShellOptions,
): Promise<NavShellState> {
  try {
    const demoHero = navShellForSectionDemoHeroPath(pathname)
    if (demoHero) return demoHero

    const preferDraft = options?.preferDraft === true
    const homeSlug = await resolveHomePageCmsSlug()
    const slug = await resolveCmsSlugForPathname(pathname)
    if (!slug) return DEFAULT_NAV_SHELL

    const page = await prisma.page.findUnique({ where: { slug } })
    if (!page) return DEFAULT_NAV_SHELL

    const primaryMode = preferDraft ? ('draft' as const) : ('published' as const)
    const fallbackMode = preferDraft ? ('published' as const) : ('draft' as const)

    let sections = await getPageSections(slug, locale, primaryMode)
    if (
      sections.length === 0 ||
      sections.every((s) => !s.data || Object.keys(s.data).length === 0)
    ) {
      sections = await getPageSections(slug, locale, fallbackMode)
    }

    const themeColor: 'dark' | 'light' =
      page.themeColor === 'dark' || page.themeColor === 'light'
        ? (page.themeColor as 'dark' | 'light')
        : slug === homeSlug
          ? 'light'
          : 'dark'

    return {
      themeColor,
      overlayHeroSecondary: shouldUseHeroSecondaryImageOverlay(sections),
      overlayHeroHomeLight: shouldUseHeroHomeImageOverlayLight(sections),
      overlayBlogHero:
        shouldUseBlogHeroUnderNav(sections) || shouldUseArticleReaderHeroUnderNav(sections),
    }
  } catch {
    return DEFAULT_NAV_SHELL
  }
}

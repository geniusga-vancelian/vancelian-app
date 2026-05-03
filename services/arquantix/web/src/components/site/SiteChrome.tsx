'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { Navigation } from '@/components/sections/Navigation'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'
import type { NavShellState } from '@/lib/cms/navShellContext'
import { isValidLocale, type Locale } from '@/config/locales'
import { figmaDsSiteShellLightClassName } from '@/components/design-system/extracted/tokens/surfaces'

export type SiteChromeProps = {
  menuItems: MenuItem[]
  initialNav: NavShellState
  children: React.ReactNode
}

/**
 * Coque site : menu fixe + fond de page, persistants entre navigations (pas de remontage du menu).
 * Routes `/admin/*`, `/preview/common-module/*`, `/preview/section/*` et `/preview/email/*` : enfants seuls (pas de menu).
 */
function isHomePath(path: string): boolean {
  const p = path.replace(/\/$/, '') || '/'
  if (p === '/') return true
  // Phase 2A — home CMS sous /fr, /en, /it
  return p === '/fr' || p === '/en' || p === '/it'
}

export function SiteChrome({ menuItems, initialNav, children }: SiteChromeProps) {
  const pathname = usePathname() ?? ''
  const isAdmin = pathname.startsWith('/admin')
  const isIntegratedNavSectionDemo =
    pathname === '/preview/section-demo/hero' ||
    pathname === '/preview/section-demo/hero_secondary' ||
    pathname === '/preview/section-demo/blog_hero' ||
    pathname === '/preview/section-demo/blog_article_reader' ||
    pathname === '/preview/section-demo/blog_article_hero'
  const isCursorDesignSystemPrint = pathname.startsWith('/design/cursor/print')
  const isHermesDesignSystemPrint = pathname.startsWith('/design/hermes/print')
  const shellLessPreview =
    pathname.startsWith('/preview/common-module') ||
    pathname.startsWith('/preview/section/') ||
    pathname.startsWith('/preview/email/') ||
    pathname.startsWith('/preview/article-block-demo/') ||
    (pathname.startsWith('/preview/section-demo/') && !isIntegratedNavSectionDemo) ||
    isCursorDesignSystemPrint ||
    isHermesDesignSystemPrint
  const bareChrome = isAdmin || shellLessPreview
  const [menu, setMenu] = React.useState<MenuItem[]>(menuItems)
  const [nav, setNav] = React.useState<NavShellState>(initialNav)
  const [forcedLocale, setForcedLocale] = React.useState<Locale | null>(null)

  React.useEffect(() => {
    setMenu(menuItems)
  }, [menuItems])

  React.useEffect(() => {
    setNav(initialNav)
  }, [initialNav])

  React.useEffect(() => {
    if (typeof window === 'undefined') return
    const onLocaleChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ locale?: unknown }>).detail
      const locale = detail?.locale
      setForcedLocale(
        typeof locale === 'string' && isValidLocale(locale) ? (locale as Locale) : null,
      )
    }
    window.addEventListener('arq:locale-changed', onLocaleChanged)
    return () => {
      window.removeEventListener('arq:locale-changed', onLocaleChanged)
    }
  }, [])

  React.useLayoutEffect(() => {
    if (bareChrome) return
    let cancelled = false
    const localeInPath =
      pathname.match(/^\/(fr|en|it)(?:\/|$)/)?.[1] ?? null
    const locale = localeInPath ?? forcedLocale
    const run = async () => {
      try {
        const q = new URLSearchParams({ path: pathname })
        if (pathname.startsWith('/preview/')) q.set('draft', '1')
        if (locale) q.set('locale', locale)
        const [navRes, menuRes] = await Promise.all([
          fetch(`/api/site/nav-shell?${q}`, { cache: 'no-store' }),
          fetch(`/api/site/primary-menu?${q}`, { cache: 'no-store' }),
        ])
        if (cancelled) return
        if (navRes.ok) {
          const data = (await navRes.json()) as NavShellState
          if (!cancelled) setNav(data)
        }
        if (menuRes.ok) {
          const data = (await menuRes.json()) as { items?: MenuItem[] }
          if (!cancelled && Array.isArray(data.items) && data.items.length > 0) {
            setMenu(data.items)
          }
        }
      } catch {
        /* garder l’état courant */
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [pathname, bareChrome, forcedLocale])

  if (bareChrome) {
    return <>{children}</>
  }

  const isHome = isHomePath(pathname)
  const overlayHeroSecondary = isHome ? false : nav.overlayHeroSecondary
  const overlayHeroHomeLight = false
  const overlayBlogHero = nav.overlayBlogHero ?? false

  const shellEffectiveTheme = overlayBlogHero
    ? 'light'
    : overlayHeroSecondary
      ? nav.themeColor
      : 'light'
  const shellBg =
    shellEffectiveTheme === 'light'
      ? figmaDsSiteShellLightClassName
      : 'min-h-screen bg-black text-white'

  return (
    <div className={shellBg}>
      <Navigation
        key={pathname}
        menuItems={menu}
        themeColor={nav.themeColor}
        overlayHeroSecondary={overlayHeroSecondary}
        overlayHeroHomeLight={overlayHeroHomeLight}
        overlayBlogHero={overlayBlogHero}
      />
      <div className="flex min-h-0 flex-col">{children}</div>
    </div>
  )
}

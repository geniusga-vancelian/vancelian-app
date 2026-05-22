'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { Navigation } from '@/components/sections/Navigation'
import { PersistentSiteFooter } from '@/components/site/PersistentSiteFooter'
import { NavPendingProvider } from '@/components/site/NavPendingContext'
import { SiteContentPending } from '@/components/site/SiteContentPending'
import { SiteTransitionProvider } from '@/components/site/SiteTransitionContext'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'
import type { NavShellState } from '@/lib/cms/navShellContext'
import type { MenuThemeJson } from '@/lib/cms/menuThemeStorage'
import { isValidLocale, type Locale } from '@/config/locales'
import { figmaDsSiteShellLightClassName } from '@/components/design-system/extracted/tokens/surfaces'
import { ScrollMotionEffects } from '@/components/motion/ScrollMotionEffects'
import { shellLocaleFromPathname } from '@/lib/site/shellLocaleFromPathname'
import type { SiteFooterData } from '@/lib/cms/site-footer'
import { cn } from '@/lib/utils'
import { isPortalPathname } from '@/lib/portal/portalRouting'

import type { SiteBrandLogo } from '@/components/ui/BrandLogo'

export type SiteChromeProps = {
  menuItems: MenuItem[]
  menuTheme: MenuThemeJson
  initialNav: NavShellState
  initialFooterData?: SiteFooterData
  brand?: SiteBrandLogo | null
  showLanguageSwitcher?: boolean
  publicLocales?: Locale[]
  children: React.ReactNode
}

/**
 * Coque site : menu + footer persistants entre navigations (pas de remontage ni refetch systématique).
 * Routes `/admin/*`, `/app/*` (login/signup inclus), `/preview/common-module/*`, … : enfants seuls.
 */
function isHomePath(path: string): boolean {
  const p = path.replace(/\/$/, '') || '/'
  if (p === '/') return true
  return p === '/fr' || p === '/en' || p === '/it'
}

export function SiteChrome({
  menuItems,
  menuTheme: initialMenuTheme,
  initialNav,
  initialFooterData,
  brand,
  showLanguageSwitcher = true,
  publicLocales,
  children,
}: SiteChromeProps) {
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
  const bareChrome = isAdmin || shellLessPreview || isPortalPathname(pathname)

  const [menu, setMenu] = React.useState<MenuItem[]>(menuItems)
  const [menuTheme, setMenuTheme] = React.useState<MenuThemeJson>(initialMenuTheme)
  const [nav, setNav] = React.useState<NavShellState>(initialNav)
  const prevPathRef = React.useRef(pathname)
  const prevLocaleRef = React.useRef<Locale>(shellLocaleFromPathname(pathname))
  const prevBareChromeRef = React.useRef(bareChrome)
  const navShellCacheRef = React.useRef<Map<string, NavShellState>>(new Map())

  const refreshNavShell = React.useCallback(async (path: string, locale: Locale | null) => {
    const cacheKey = `${locale ?? 'default'}:${path}`
    const cached = navShellCacheRef.current.get(cacheKey)
    if (cached) {
      setNav(cached)
      return
    }

    try {
      const q = new URLSearchParams({ path })
      if (path.startsWith('/preview/')) q.set('draft', '1')
      if (locale) q.set('locale', locale)
      const navRes = await fetch(`/api/site/nav-shell?${q}`)
      if (navRes.ok) {
        const data = (await navRes.json()) as NavShellState
        navShellCacheRef.current.set(cacheKey, data)
        setNav(data)
      }
    } catch {
      /* garder l’état courant */
    }
  }, [])

  const refreshMenuFromApi = React.useCallback(async (path: string, locale: Locale | null) => {
    try {
      const q = new URLSearchParams({ path })
      if (path.startsWith('/preview/')) q.set('draft', '1')
      if (locale) q.set('locale', locale)
      const [navRes, menuRes] = await Promise.all([
        fetch(`/api/site/nav-shell?${q}`),
        fetch(`/api/site/primary-menu?${q}`),
      ])
      if (navRes.ok) {
        const data = (await navRes.json()) as NavShellState
        setNav(data)
      }
      if (menuRes.ok) {
        const data = (await menuRes.json()) as { items?: MenuItem[]; theme?: MenuThemeJson }
        if (Array.isArray(data.items) && data.items.length > 0) {
          setMenu(data.items)
        }
        if (data.theme) {
          setMenuTheme(data.theme)
        }
      }
    } catch {
      /* garder l’état courant */
    }
  }, [])

  React.useEffect(() => {
    const wasBareChrome = prevBareChromeRef.current
    prevBareChromeRef.current = bareChrome

    if (bareChrome) return

    const locale = shellLocaleFromPathname(pathname)
    const localeChanged = locale !== prevLocaleRef.current
    const pathChanged = pathname !== prevPathRef.current

    prevPathRef.current = pathname
    prevLocaleRef.current = locale

    if (wasBareChrome) {
      void refreshMenuFromApi(pathname, locale)
      return
    }

    if (localeChanged) {
      void refreshMenuFromApi(pathname, locale)
      return
    }

    if (pathChanged) {
      void refreshNavShell(pathname, locale)
    }
  }, [bareChrome, pathname, refreshMenuFromApi, refreshNavShell])

  React.useEffect(() => {
    if (typeof window === 'undefined') return
    const onLocaleChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ locale?: unknown }>).detail
      const locale =
        typeof detail?.locale === 'string' && isValidLocale(detail.locale)
          ? (detail.locale as Locale)
          : null
      if (locale && !bareChrome) {
        void refreshMenuFromApi(pathname, locale)
      }
    }
    window.addEventListener('arq:locale-changed', onLocaleChanged)
    return () => {
      window.removeEventListener('arq:locale-changed', onLocaleChanged)
    }
  }, [bareChrome, pathname, refreshMenuFromApi])

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

  const chromeContent = bareChrome ? (
    children
  ) : (
    <>
      <ScrollMotionEffects />
      <Navigation
        menuItems={menu}
        brand={brand}
        menuTheme={menuTheme}
        themeColor={nav.themeColor}
        overlayHeroSecondary={overlayHeroSecondary}
        overlayHeroHomeLight={overlayHeroHomeLight}
        overlayBlogHero={overlayBlogHero}
        showLanguageSwitcher={showLanguageSwitcher}
        publicLocales={publicLocales}
      />
      <SiteContentPending className="flex flex-1 flex-col">{children}</SiteContentPending>
      <PersistentSiteFooter initialData={initialFooterData} />
    </>
  )

  return (
    <SiteTransitionProvider brand={brand}>
      {bareChrome ? (
        chromeContent
      ) : (
        <NavPendingProvider>
          <div className={cn(shellBg, 'flex min-h-screen flex-col')}>{chromeContent}</div>
        </NavPendingProvider>
      )}
    </SiteTransitionProvider>
  )
}

'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Logo } from '@/components/ui/Logo'
import { Container } from '@/components/ui/Container'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { MobilePrimaryNavList } from '@/components/layout/MobilePrimaryNavList'
import {
  NAV_MENU_LINK_ACTIVE_SURFACE,
  NAV_MENU_LINK_FRAME,
  NAV_PRIMARY_LINK_TYPO,
} from '@/components/design-system/nav-primary-link'
import {
  navBackdropBlurPx,
  navPaletteForBlend,
  navPaletteForLightSolidHeroBlend,
  useTransparentHeroNavBlend,
} from '@/hooks/useHeroSecondaryNavBlend'
import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import {
  getActiveLocaleFromPathname,
  isPublicHrefExternalNavigation,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from '@/lib/i18n/publicLocalizedRouting'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { FigmaNavSubmenu } from '@/components/mega-menu/figma/FigmaNavSubmenu'
import type { MegaMenuColumnPayload } from '@/lib/menu/buildMegaMenuColumns'

type MegaSlideDir = 'forward' | 'backward'

type MegaLeaving = { cols: MegaMenuColumnPayload[]; dir: MegaSlideDir }

/**
 * Panneau méga-menu desktop : hauteur animée + glissement latéral selon la direction dans la barre.
 */
function DesktopMegaMenuHoverPanel({
  megaOpenItemId,
  linkItems,
  onPanelMouseEnter,
}: {
  megaOpenItemId: string | null
  linkItems: MenuItem[]
  onPanelMouseEnter: () => void
}) {
  const linkItemsRef = React.useRef(linkItems)
  linkItemsRef.current = linkItems

  const [leaving, setLeaving] = React.useState<MegaLeaving | null>(null)
  const leaveTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevOpenIdRef = React.useRef<string | null>(null)
  const [enterAnimClass, setEnterAnimClass] = React.useState('mega-menu-enter-initial')

  const openItem = megaOpenItemId
    ? linkItems.find((i) => i.id === megaOpenItemId)
    : null
  const openCols = openItem?.megaMenu?.columns

  const measureRef = React.useRef<HTMLDivElement>(null)
  const [panelHeight, setPanelHeight] = React.useState<number | null>(null)

  React.useEffect(() => {
    return () => {
      if (leaveTimerRef.current) {
        clearTimeout(leaveTimerRef.current)
        leaveTimerRef.current = null
      }
    }
  }, [])

  React.useLayoutEffect(() => {
    if (leaveTimerRef.current) {
      clearTimeout(leaveTimerRef.current)
      leaveTimerRef.current = null
    }

    const items = linkItemsRef.current
    const item = megaOpenItemId ? items.find((i) => i.id === megaOpenItemId) : null
    const cols = item?.megaMenu?.columns

    if (!megaOpenItemId || !cols?.length) {
      prevOpenIdRef.current = null
      setLeaving(null)
      setEnterAnimClass('mega-menu-enter-initial')
      setPanelHeight(null)
      return
    }

    const prevId = prevOpenIdRef.current

    if (prevId && prevId !== megaOpenItemId) {
      const pItem = items.find((i) => i.id === prevId)
      const nItem = items.find((i) => i.id === megaOpenItemId)
      const dir: MegaSlideDir =
        pItem && nItem && nItem.order < pItem.order ? 'backward' : 'forward'
      const prevCols = items.find((i) => i.id === prevId)?.megaMenu?.columns
      if (prevCols?.length) {
        setLeaving({ cols: prevCols, dir })
        setEnterAnimClass(
          dir === 'forward' ? 'mega-menu-enter-forward' : 'mega-menu-enter-backward',
        )
        leaveTimerRef.current = setTimeout(() => {
          setLeaving(null)
          leaveTimerRef.current = null
        }, 300)
      } else {
        setEnterAnimClass('mega-menu-enter-initial')
      }
    } else {
      setEnterAnimClass('mega-menu-enter-initial')
    }

    prevOpenIdRef.current = megaOpenItemId
  }, [megaOpenItemId])

  React.useLayoutEffect(() => {
    const node = measureRef.current
    if (!node || !megaOpenItemId || !openCols?.length) return

    const update = () => {
      const h = Math.ceil(node.getBoundingClientRect().height)
      if (h > 0) setPanelHeight(h)
    }
    update()
    const ro = new ResizeObserver(() => {
      update()
    })
    ro.observe(node)
    return () => ro.disconnect()
  }, [megaOpenItemId, leaving])

  if (!megaOpenItemId || !openCols?.length) return null

  return (
    <div
      className="absolute left-1/2 top-full z-[80] w-[min(92vw,960px)] -translate-x-1/2 pt-3"
      onMouseEnter={onPanelMouseEnter}
    >
      <div
        className="overflow-hidden"
        style={{
          height: panelHeight != null ? panelHeight : undefined,
          transition: 'height 320ms cubic-bezier(0.33, 1, 0.68, 1)',
        }}
      >
        <div className="relative">
          {leaving ? (
            <div
              className={cn(
                'pointer-events-none absolute inset-x-0 top-0 z-[1]',
                leaving.dir === 'forward' ? 'mega-menu-exit-forward' : 'mega-menu-exit-backward',
              )}
              aria-hidden
            >
              <FigmaNavSubmenu columns={leaving.cols} />
            </div>
          ) : null}
          <div
            ref={measureRef}
            key={megaOpenItemId}
            className={cn('relative z-[2]', enterAnimClass)}
          >
            <FigmaNavSubmenu columns={openCols} />
          </div>
        </div>
      </div>
    </div>
  )
}

function normalizePath(p: string): string {
  const t = p.replace(/\/$/, '')
  return t || '/'
}

function isNavItemActive(pathname: string, item: MenuItem, navLocale: Locale): boolean {
  const p = normalizePath(pathname)
  const kind = item.navigationNodeKind ?? 'PAGE'

  if (kind === 'GROUP' && item.megaMenu?.columns?.length) {
    for (const col of item.megaMenu.columns) {
      for (const sub of col.items) {
        const u = normalizePath(localizePublicInternalHref(sub.href, navLocale))
        if (p === u || p.startsWith(`${u}/`)) return true
      }
    }
    return false
  }

  const u = normalizePath(localizePublicInternalHref(item.urlPath, navLocale))
  if (item.isRoot) {
    if (p === u) return true
    if (p === '/' && u === `/${defaultLocale}`) return true
    return false
  }
  return p === u || p.startsWith(`${u}/`)
}

export interface NavigationProps extends React.HTMLAttributes<HTMLElement> {
  transparent?: boolean
  menuItems?: MenuItem[]
  themeColor?: 'dark' | 'light'
  /**
   * Hero secondary en première section **avec image de fond CMS** : barre transparente,
   * liens inversés (clair sur photo) puis fusion + blur comme ci-dessous.
   * Sans image : laisser à false (barre blanche, thème light classique).
   */
  overlayHeroSecondary?: boolean
  /**
   * Hero **homepage** en première section **avec image CMS** : barre 100 % transparente,
   * liens **light** (noir / gris / actif noir–blanc), même transition blur / givré au scroll
   * que le hero-secondary.
   */
  overlayHeroHomeLight?: boolean
  /**
   * Hero blog en tête : fond neutre (gray100), barre transparente + liens foncés,
   * même mécanique de blend au scroll que le hero secondary (sans photo).
   */
  overlayBlogHero?: boolean
  showLanguageSwitcher?: boolean
  publicLocales?: Locale[]
}

function inferActionStyle(item: MenuItem): 'outline' | 'text' | 'solid' {
  const s = (item.buttonStyle || '').toLowerCase()
  if (s === 'primary') return 'solid'
  if (s === 'secondary') return 'outline'
  if (s === 'outline') return 'outline'
  if (s === 'text' || s === 'ghost' || s === 'link') return 'text'
  const lab = item.label.toLowerCase()
  if (lab.includes('login') || lab.includes('connexion')) return 'outline'
  if (lab.includes('wallet') || lab.includes('connect')) return 'text'
  return 'solid'
}

/** Cible de navigation pour un item BUTTON (lien interne ou externe), hors `buttonAction`. */
function navActionButtonHref(item: MenuItem, navLocale: Locale): string | null {
  if (item.buttonAction) return null
  const raw = ((item.externalUrl || '').trim() || (item.urlPath || '').trim())
  if (!raw || raw === '#') return null
  if (shouldSkipLocalizePublicHref(raw)) return raw
  const path = raw.startsWith('/') ? raw : `/${raw}`
  return localizePublicInternalHref(path, navLocale)
}

export function Navigation({
  transparent: _transparent = true,
  className,
  menuItems: propMenuItems,
  themeColor: _themeColor = 'light',
  overlayHeroSecondary = false,
  overlayHeroHomeLight = false,
  overlayBlogHero = false,
  showLanguageSwitcher = true,
  publicLocales: publicLocalesProp,
  ...props
}: NavigationProps) {
  const pathname = usePathname() ?? ''
  const publicLocales = publicLocalesProp ?? [...supportedLocales]
  const navLocale = getActiveLocaleFromPathname(pathname)
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [scrolled, setScrolled] = React.useState(false)
  const [isMobileViewport, setIsMobileViewport] = React.useState(false)
  const [megaOpenItemId, setMegaOpenItemId] = React.useState<string | null>(null)
  const megaCloseTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearMegaMenuCloseTimer = React.useCallback(() => {
    if (megaCloseTimerRef.current) {
      clearTimeout(megaCloseTimerRef.current)
      megaCloseTimerRef.current = null
    }
  }, [])

  const scheduleMegaMenuClose = React.useCallback(() => {
    clearMegaMenuCloseTimer()
    megaCloseTimerRef.current = setTimeout(() => {
      setMegaOpenItemId(null)
      megaCloseTimerRef.current = null
    }, 140)
  }, [clearMegaMenuCloseTimer])

  const glassAnchorId: string | null = overlayBlogHero
    ? 'blog-hero'
    : overlayHeroSecondary
      ? 'hero-secondary'
      : overlayHeroHomeLight
        ? 'hero-home'
        : null
  const useGlass = Boolean(glassAnchorId)
  const forceLightOnHome = overlayHeroHomeLight
  const mobileHomePlain = overlayHeroHomeLight && isMobileViewport
  const useGlassForUi = useGlass && !mobileHomePlain
  const overlayOnMediaForUi =
    (overlayHeroSecondary || overlayHeroHomeLight || overlayBlogHero) && !mobileHomePlain

  React.useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 6)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  React.useEffect(() => {
    const mql = window.matchMedia('(max-width: 767px)')
    const apply = () => setIsMobileViewport(mql.matches)
    apply()
    mql.addEventListener('change', apply)
    return () => {
      mql.removeEventListener('change', apply)
    }
  }, [])

  React.useEffect(() => {
    if (!mobileOpen) return
    const previousOverflow = document.body.style.overflow
    const previousTouchAction = document.body.style.touchAction
    document.body.style.overflow = 'hidden'
    document.body.style.touchAction = 'none'
    return () => {
      document.body.style.overflow = previousOverflow
      document.body.style.touchAction = previousTouchAction
    }
  }, [mobileOpen])

  const scrollBlend = useTransparentHeroNavBlend(useGlassForUi, glassAnchorId)
  /** 0 = barre transparente sur le hero, 1 = givré / plein après scroll. */
  const tBar = useGlassForUi ? scrollBlend : 1
  const tLink =
    forceLightOnHome ? 1 : overlayOnMediaForUi && !mobileOpen ? scrollBlend : 1
  const tButton =
    forceLightOnHome ? 1 : overlayOnMediaForUi && !mobileOpen ? scrollBlend : 1

  const barPalette = useGlassForUi
    ? overlayBlogHero
      ? navPaletteForLightSolidHeroBlend(tBar)
      : navPaletteForBlend(tBar)
    : null
  const linkPalette = overlayOnMediaForUi
    ? overlayBlogHero
      ? navPaletteForLightSolidHeroBlend(tLink)
      : navPaletteForBlend(tLink)
    : null

  const logoDark =
    forceLightOnHome ||
    (!overlayOnMediaForUi && !overlayBlogHero) ||
    mobileOpen ||
    tBar > 0.45 ||
    overlayBlogHero

  const langTheme: 'dark' | 'light' = overlayBlogHero
    ? 'light'
    : forceLightOnHome
      ? 'light'
      : overlayOnMediaForUi && !mobileOpen && tBar < 0.45
        ? 'dark'
        : 'light'

  const fallbackMenuItems: MenuItem[] = [
    { id: 'fallback-home', label: siteCommonCta(navLocale, 'fallback_menu_home'), urlPath: `/${navLocale}`, order: 0, type: 'LINK', isRoot: true },
    { id: 'fallback-projects', label: siteCommonCta(navLocale, 'fallback_menu_projects'), urlPath: `/${navLocale}/projects`, order: 1, type: 'LINK' },
    { id: 'fallback-vaults', label: siteCommonCta(navLocale, 'fallback_menu_vaults'), urlPath: '/vaults', order: 2, type: 'LINK' },
    { id: 'fallback-about', label: siteCommonCta(navLocale, 'fallback_menu_about'), urlPath: `/${navLocale}/about`, order: 3, type: 'LINK' },
    { id: 'fallback-contact', label: siteCommonCta(navLocale, 'fallback_menu_contact'), urlPath: `/${navLocale}/contact`, order: 4, type: 'LINK' },
    ...(showLanguageSwitcher
      ? ([
          {
            id: 'fallback-lang',
            label: siteCommonCta(navLocale, 'fallback_menu_lang'),
            urlPath: '#',
            order: 9,
            type: 'LANGUAGE_SWITCHER' as const,
          },
        ] satisfies MenuItem[])
      : []),
    { id: 'fallback-login', label: siteCommonCta(navLocale, 'fallback_menu_login'), urlPath: '/login', order: 10, type: 'BUTTON', buttonStyle: 'outline' },
    { id: 'fallback-wallet', label: siteCommonCta(navLocale, 'fallback_menu_connect_wallet'), urlPath: '#', order: 11, type: 'BUTTON', buttonStyle: 'text' },
  ]

  const menuItemsRaw =
    propMenuItems && propMenuItems.length > 0 ? propMenuItems : fallbackMenuItems
  const menuItems = showLanguageSwitcher
    ? menuItemsRaw
    : menuItemsRaw.filter((item) => item.type !== 'LANGUAGE_SWITCHER')

  const rawLinkItems = menuItems.filter((item) => (item.type || 'LINK') === 'LINK')
  const rawButtonItems = menuItems.filter((item) => (item.type || 'LINK') === 'BUTTON')

  /**
   * Certains items édités côté back-office peuvent être enregistrés en BUTTON "text"
   * alors qu'ils représentent un lien de navigation primaire (ex. About/A propos).
   * On les remonte dans la zone des liens pour conserver alignement et style homogènes.
   */
  const buttonAsLinkItems = rawButtonItems
    .filter(
      (item) =>
        inferActionStyle(item) === 'text' &&
        !item.buttonAction &&
        typeof item.externalUrl === 'string' &&
        item.externalUrl.trim().startsWith('/'),
    )
    .map(
      (item) =>
        ({
          ...item,
          type: 'LINK' as const,
          urlPath: item.externalUrl?.trim() || item.urlPath,
        }) satisfies MenuItem,
    )

  const linkItems = [...rawLinkItems, ...buttonAsLinkItems].sort(
    (a, b) => (a.order || 0) - (b.order || 0),
  )
  const buttonItems = rawButtonItems.filter(
    (item) => !buttonAsLinkItems.some((promoted) => promoted.id === item.id),
  )

  /** Langue + boutons d’action, ordre éditorial unique (`order` menu primaire). */
  const rightRailItems = menuItems
    .filter((item) => {
      if (item.type === 'LANGUAGE_SWITCHER') return true
      if ((item.type || 'LINK') !== 'BUTTON') return false
      return !buttonAsLinkItems.some((promoted) => promoted.id === item.id)
    })
    .sort((a, b) => (a.order || 0) - (b.order || 0))

  const isActive = (item: MenuItem) => isNavItemActive(pathname, item, navLocale)

  const renderLink = (
    item: MenuItem,
    onNavigate?: () => void,
    options?: { withAnchorKey?: boolean },
  ) => {
    const withAnchorKey = options?.withAnchorKey !== false
    const active = isActive(item)
    const href = localizePublicInternalHref(item.urlPath, navLocale)
    const palette = linkPalette
    const style: React.CSSProperties = active
      ? {
          backgroundColor: palette ? palette.activeBg : '#000000',
          color: palette ? palette.activeFg : '#ffffff',
          boxShadow: tLink < 0.98 ? '0 1px 2px rgba(0,0,0,0.08)' : undefined,
        }
      : {
          color: palette ? palette.inactivePill : '#62656e',
        }

    return (
      <a
        key={withAnchorKey ? item.id : undefined}
        href={href}
        onClick={onNavigate}
        className={cn(
          NAV_MENU_LINK_FRAME,
          NAV_PRIMARY_LINK_TYPO,
          'transition-[color,background-color] duration-300 ease-out hover:text-black',
          !active && palette ? '' : !active ? 'text-[#62656e]' : '',
        )}
        style={style}
      >
        {item.label}
      </a>
    )
  }

  /** Lien page, groupe non cliquable, ou lien externe — barre desktop. */
  const renderDesktopPrimaryNavItem = (
    item: MenuItem,
    opts?: { hasMegaMenu: boolean },
  ) => {
    const active = isActive(item)
    const palette = linkPalette
    const style: React.CSSProperties = active
      ? {
          backgroundColor: palette ? palette.activeBg : '#000000',
          color: palette ? palette.activeFg : '#ffffff',
          boxShadow: tLink < 0.98 ? '0 1px 2px rgba(0,0,0,0.08)' : undefined,
        }
      : {
          color: palette ? palette.inactivePill : '#62656e',
        }

    const navKind = item.navigationNodeKind ?? 'PAGE'

    if (navKind === 'GROUP') {
      const hm = opts?.hasMegaMenu ?? false
      return (
        <button
          type="button"
          aria-haspopup={hm ? 'menu' : undefined}
          aria-expanded={hm ? megaOpenItemId === item.id : undefined}
          className={cn(
            NAV_MENU_LINK_FRAME,
            NAV_PRIMARY_LINK_TYPO,
            'cursor-default border-none bg-transparent transition-[color,background-color] duration-300 ease-out hover:text-black',
            !active && palette ? '' : !active ? 'text-[#62656e]' : '',
          )}
          style={style}
        >
          {item.label}
        </button>
      )
    }

    if (navKind === 'EXTERNAL_LINK') {
      const raw = (item.urlPath || '').trim()
      const href = shouldSkipLocalizePublicHref(raw) ? raw : localizePublicInternalHref(raw, navLocale)
      const newTab = item.openInNewTab || isPublicHrefExternalNavigation(href)
      return (
        <a
          href={href}
          target={newTab ? '_blank' : undefined}
          rel={newTab ? 'noopener noreferrer' : undefined}
          className={cn(
            NAV_MENU_LINK_FRAME,
            NAV_PRIMARY_LINK_TYPO,
            'transition-[color,background-color] duration-300 ease-out hover:text-black',
            !active && palette ? '' : !active ? 'text-[#62656e]' : '',
          )}
          style={style}
        >
          {item.label}
        </a>
      )
    }

    return renderLink(item, undefined, { withAnchorKey: false })
  }

  const renderButton = (item: MenuItem, mobile = false) => {
    const handleClick = (e: React.MouseEvent) => {
      if (
        item.buttonAction &&
        typeof window !== 'undefined' &&
        (window as unknown as Record<string, unknown>)[item.buttonAction!]
      ) {
        e.preventDefault()
        ;(window as unknown as Record<string, (() => void) | undefined>)[
          item.buttonAction!
        ]?.()
      }
    }

    const style = inferActionStyle(item)
    const darkUi = overlayOnMediaForUi && !overlayBlogHero && tButton < 0.5

    /** Même padding / taille de texte que les entrées « tab » du menu (`NAV_MENU_LINK_FRAME` + lien mobile). */
    const btnTypo = mobile
      ? "font-['Avenir:Heavy',sans-serif] text-[18px] leading-[1.6] tracking-[-0.01em]"
      : NAV_PRIMARY_LINK_TYPO
    const btnPadFrame = mobile ? 'px-6 py-3' : 'px-3 py-2'

    const inner =
      style === 'outline' ? (
        <span
          className={cn(
            btnTypo,
            'inline-flex items-center justify-center rounded-full border transition-colors',
            btnPadFrame,
            mobile ? 'w-full' : '',
            darkUi
              ? 'border-white/70 text-white/95 hover:border-white hover:text-white'
              : 'border-[#8a8f9a] text-[#62656e] hover:border-black hover:text-black',
          )}
        >
          {item.label}
        </span>
      ) : style === 'text' ? (
        <span
          className={cn(
            btnTypo,
            'inline-flex items-center justify-center rounded-full transition-opacity hover:opacity-70',
            btnPadFrame,
            mobile ? 'w-full border border-[#8a8f9a]' : '',
            darkUi ? 'text-white' : 'text-black',
          )}
        >
          {item.label}
        </span>
      ) : (
        <span
          className={cn(
            btnTypo,
            'inline-flex items-center justify-center rounded-full transition-colors',
            btnPadFrame,
            mobile ? 'w-full' : '',
            darkUi
              ? 'bg-white text-black hover:bg-white/90'
              : 'bg-black text-white hover:bg-black/90',
          )}
        >
          {item.label}
        </span>
      )

    const href = navActionButtonHref(item, navLocale)
    const openExternal = href ? isPublicHrefExternalNavigation(href) : false

    const wrapped =
      href && !item.buttonAction ? (
        <a
          key={item.id}
          href={href}
          target={openExternal ? '_blank' : undefined}
          rel={openExternal ? 'noopener noreferrer' : undefined}
          className={cn('inline-flex no-underline', mobile ? 'w-full' : '')}
        >
          {inner}
        </a>
      ) : (
        <button
          key={item.id}
          type="button"
          onClick={handleClick}
          className={cn('inline-flex cursor-pointer border-none bg-transparent p-0', mobile ? 'w-full' : '')}
        >
          {inner}
        </button>
      )

    return wrapped
  }

  const blurPx = useGlassForUi ? navBackdropBlurPx(tBar) : 0

  const navBarStyle: React.CSSProperties | undefined =
    useGlassForUi && barPalette
      ? {
          backgroundColor: barPalette.navBg,
          transition:
            'background-color 220ms ease-out, border-color 220ms ease-out, backdrop-filter 220ms ease-out, -webkit-backdrop-filter 220ms ease-out',
          borderBottomWidth: 0,
          borderBottomColor: 'transparent',
          ...(blurPx > 0
            ? {
                backdropFilter: `saturate(160%) blur(${blurPx}px)`,
                WebkitBackdropFilter: `saturate(160%) blur(${blurPx}px)`,
              }
            : {}),
        }
      : !useGlassForUi
        ? {
            backgroundColor: scrolled ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0)',
            transition:
              'background-color 220ms ease-out, backdrop-filter 220ms ease-out, -webkit-backdrop-filter 220ms ease-out',
            borderBottomWidth: 0,
            borderBottomColor: 'transparent',
            ...(scrolled
              ? {
                  backdropFilter: 'saturate(160%) blur(14px)',
                  WebkitBackdropFilter: 'saturate(160%) blur(14px)',
                }
              : {}),
          }
      : undefined

  return (
    <nav
      className={cn(
        'fixed left-0 right-0 top-0 z-50 w-full min-w-full max-w-[100vw] overflow-x-clip',
        className,
      )}
      style={navBarStyle}
      {...props}
    >
      <Container>
        <div className="relative z-[70] flex h-14 items-center gap-4 md:h-[60px]">
          <a
            href={`/${navLocale}`}
            className="relative aspect-[178/85.7715] w-[142px] min-w-[142px] max-w-[142px] shrink-0 no-underline"
            aria-label={siteCommonCta(navLocale, 'nav_home_aria')}
          >
            <Logo
              className="absolute inset-0 size-full min-h-0 min-w-0 transition-colors duration-300"
              color={logoDark ? 'black' : 'white'}
            />
          </a>

          <div className="hidden min-w-0 flex-1 items-center justify-center md:flex">
            {linkItems.length > 0 ? (
              <div
                className="relative flex min-h-[44px] min-w-0 flex-1 flex-col items-center"
                onMouseLeave={scheduleMegaMenuClose}
              >
                <div className="flex min-h-[44px] min-w-0 flex-wrap items-center justify-center gap-[13px]">
                  {linkItems.map((item) => {
                    const hasMega = Boolean(
                      item.megaMenu &&
                        Array.isArray(item.megaMenu.columns) &&
                        item.megaMenu.columns.length > 0,
                    )
                    const navKind = item.navigationNodeKind ?? 'PAGE'
                    const ariaMega =
                      hasMega && navKind !== 'GROUP'
                        ? ({
                            'aria-haspopup': 'true' as const,
                            'aria-expanded': megaOpenItemId === item.id,
                          } as const)
                        : {}
                    return (
                      <div
                        key={item.id}
                        className="inline-flex"
                        {...ariaMega}
                        onMouseEnter={() => {
                          clearMegaMenuCloseTimer()
                          if (hasMega) setMegaOpenItemId(item.id)
                          else setMegaOpenItemId(null)
                        }}
                      >
                        {renderDesktopPrimaryNavItem(item, { hasMegaMenu: hasMega })}
                      </div>
                    )
                  })}
                </div>
                {megaOpenItemId ? (
                  <DesktopMegaMenuHoverPanel
                    megaOpenItemId={megaOpenItemId}
                    linkItems={linkItems}
                    onPanelMouseEnter={clearMegaMenuCloseTimer}
                  />
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="ml-auto flex shrink-0 items-center gap-2 md:gap-5">
            {rightRailItems.map((item) =>
              item.type === 'LANGUAGE_SWITCHER' ? (
                <span key={item.id} className="hidden md:contents">
                  <LanguageSwitcher
                    key={item.id}
                    themeColor={langTheme}
                    enabledLocales={publicLocales}
                  />
                </span>
              ) : (
                <span key={item.id} className="hidden md:contents">
                  {renderButton(item, false)}
                </span>
              ),
            )}
            {buttonItems.length > 0 ? (
              <span className="shrink-0 md:hidden">{renderButton(buttonItems[0], false)}</span>
            ) : null}

            <button
              type="button"
              className={cn(
                'relative h-10 w-10 p-2 md:hidden transition-colors duration-300',
                logoDark ? 'text-black' : 'text-white',
              )}
              aria-expanded={mobileOpen}
              aria-label={siteCommonCta(navLocale, 'nav_menu_toggle_aria')}
              onClick={() => setMobileOpen((o) => !o)}
            >
              <span
                className={cn(
                  'absolute left-2 right-2 top-[12px] h-[2px] origin-center bg-current transition-transform duration-300',
                  mobileOpen ? 'translate-y-[6px] rotate-45' : '',
                )}
              />
              <span
                className={cn(
                  'absolute left-2 right-2 top-[18px] h-[2px] bg-current transition-opacity duration-200',
                  mobileOpen ? 'opacity-0' : 'opacity-100',
                )}
              />
              <span
                className={cn(
                  'absolute left-2 right-2 top-[24px] h-[2px] origin-center bg-current transition-transform duration-300',
                  mobileOpen ? '-translate-y-[6px] -rotate-45' : '',
                )}
              />
            </button>
          </div>
        </div>

        {mobileOpen ? (
          <div
            className={cn(
              'fixed inset-x-0 top-0 z-[60] flex h-[100dvh] flex-col overflow-hidden bg-white md:hidden',
            )}
          >
            <div className="mx-auto flex min-h-0 w-full min-w-0 max-w-lg flex-1 flex-col pt-[5.5rem]">
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
                <MobilePrimaryNavList
                  linkItems={linkItems}
                  navLocale={navLocale}
                  pathname={pathname}
                  isActive={isActive}
                  onNavigate={() => setMobileOpen(false)}
                />
                {showLanguageSwitcher ? (
                  <LanguageSwitcher
                    variant="drawer-row"
                    themeColor="light"
                    enabledLocales={publicLocales}
                  />
                ) : null}
              </div>
              {buttonItems.length > 1 ? (
                <div className="shrink-0 border-t border-black/[0.06] bg-white px-4 py-4">
                  <div className="mx-auto flex w-full max-w-md flex-col gap-3">
                    {buttonItems.slice(1).map((item) => (
                      <div key={item.id} className="w-full">
                        {renderButton(item, true)}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </Container>
    </nav>
  )
}

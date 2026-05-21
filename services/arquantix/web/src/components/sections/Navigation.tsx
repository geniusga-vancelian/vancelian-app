'use client'

/**
 * Vancelian — **Topnav** (refonte stricte DS Vancelian, pack handoff v1.0).
 *
 * Spec officielle : `components/topnav/topnav.css` + `topnav.html` + `topnav.js`
 * du pack handoff dev. Caractéristiques :
 *
 * - Hauteur **72 px** fixe (`position: fixed; inset: 0 0 auto 0`).
 * - Layout `grid-template-columns: 1fr auto 1fr` (logo · liens · actions).
 * - **4 états chromatiques** auto-détectés via {@link useTopnavSurfaceObserver} :
 *   - `transparent` : par défaut, au-dessus d'un hero — texte/logo blancs.
 *   - `solid`       : `scrollY > 0`, fond `--v-bg`, texte anthracite.
 *   - `warm`        : sur une section `[data-nav-surface="warm"]`, fond `--v-card-warm`.
 *   - `dark`        : sur une section `[data-nav-surface="dark"]` (final-cta,
 *                     testimonial fullbleed, footer) — fond `#141208`, texte
 *                     et logo blancs.
 * - Liens : Inter Medium 14px, padding `6px 0`, **underline subtle 1px** en
 *   bottom (`opacity 0 → 1` au hover/active). Aucun fond ni pill.
 * - Gap items 32 px, transitions 480 ms `var(--v-ease-in-out)`.
 * - CTA droite : **un seul bouton primary pill** (premier bouton CMS) +
 *   sélecteur de langue en `text-link` discret (atome DS officiel).
 * - Mobile (≤ 1024 px) : burger + drawer plein écran, items DS-compatibles.
 *
 * Le mega menu desktop hérité a été retiré (non couvert par le DS Vancelian).
 * Les items GROUP CMS rendent désormais un lien vers leur première sous-page,
 * ce qui préserve la navigation sans rompre la grammaire visuelle.
 */

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { BrandLogo, type SiteBrandLogo } from '@/components/ui/BrandLogo'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { MobilePrimaryNavList } from '@/components/layout/MobilePrimaryNavList'
import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import {
  getActiveLocaleFromPathname,
  isPublicHrefExternalNavigation,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from '@/lib/i18n/publicLocalizedRouting'
import { Container } from '@/components/ui/Container'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { Button } from '@/components/ui/button'
import {
  TOPNAV_HEIGHT_PX,
  useTopnavSurfaceObserver,
  type TopnavSurface,
} from '@/hooks/useTopnavSurfaceObserver'
import {
  buildTopnavPalettes,
  type TopnavPalette,
} from '@/lib/cms/site-menu-theme'
import type { MenuThemeJson } from '@/lib/cms/menuThemeStorage'

/* --------------------------------------------------------------------------
 * Helpers de routage
 * -------------------------------------------------------------------------- */

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

/**
 * Résout l'URL d'un item GROUP en pointant vers son premier sous-lien
 * (le DS Vancelian ne couvre pas le mega menu — on dégrade proprement).
 */
function resolveGroupFallbackHref(item: MenuItem, navLocale: Locale): string | null {
  const first = item.megaMenu?.columns?.[0]?.items?.[0]?.href
  if (!first) return null
  return localizePublicInternalHref(first, navLocale)
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

function navActionButtonHref(item: MenuItem, navLocale: Locale): string | null {
  if (item.buttonAction) return null
  const raw = ((item.externalUrl || '').trim() || (item.urlPath || '').trim())
  if (!raw || raw === '#') return null
  if (shouldSkipLocalizePublicHref(raw)) return raw
  const path = raw.startsWith('/') ? raw : `/${raw}`
  return localizePublicInternalHref(path, navLocale)
}

/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

export interface NavigationProps extends React.HTMLAttributes<HTMLElement> {
  menuItems?: MenuItem[]
  brand?: SiteBrandLogo | null
  /** Palettes topnav CMS (`Menu.themeJson`) — repli sur tokens `--v-*` si absent. */
  menuTheme?: MenuThemeJson | null
  showLanguageSwitcher?: boolean
  publicLocales?: Locale[]
  /**
   * @deprecated — la barre détecte automatiquement son état via
   * `[data-nav-surface]` sur les sections. Conservé pour compat API.
   */
  transparent?: boolean
  /** @deprecated — voir {@link useTopnavSurfaceObserver}. */
  themeColor?: 'dark' | 'light'
  /** @deprecated — voir {@link useTopnavSurfaceObserver}. */
  overlayHeroSecondary?: boolean
  /** @deprecated — voir {@link useTopnavSurfaceObserver}. */
  overlayHeroHomeLight?: boolean
  /** @deprecated — voir {@link useTopnavSurfaceObserver}. */
  overlayBlogHero?: boolean
}

/* --------------------------------------------------------------------------
 * Atome — lien primaire topnav (DS strict)
 * -------------------------------------------------------------------------- */

interface TopnavLinkProps {
  href: string
  active: boolean
  palette: TopnavPalette
  external?: boolean
  newTab?: boolean
  onClick?: () => void
  children: React.ReactNode
}

function TopnavLink({
  href,
  active,
  palette,
  external = false,
  newTab = false,
  onClick,
  children,
}: TopnavLinkProps) {
  return (
    <a
      href={href}
      onClick={onClick}
      target={newTab ? '_blank' : undefined}
      rel={newTab || external ? 'noopener noreferrer' : undefined}
      aria-current={active ? 'page' : undefined}
      data-active={active ? '' : undefined}
      className={cn(
        // Lien en hauteur pleine ; indicateur via .topnav-link-indicator (globals.css).
        'group relative flex h-full items-center font-ui text-[14px] font-medium leading-none',
        'no-underline transition-[color] duration-150 ease-out',
      )}
      style={{ color: palette.linkColor }}
    >
      <span>{children}</span>
      <span
        aria-hidden
        className={cn(
          'topnav-link-indicator pointer-events-none absolute inset-x-0 h-px',
          'transition-opacity duration-150 ease-out',
          active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
        )}
        style={{ background: palette.underlineColor }}
      />
    </a>
  )
}

/* --------------------------------------------------------------------------
 * Atome — bouton CTA primary (DS strict, btn--sm)
 * -------------------------------------------------------------------------- */

interface TopnavCtaProps {
  palette: TopnavPalette
  href?: string | null
  newTab?: boolean
  onClick?: (e: React.MouseEvent) => void
  children: React.ReactNode
}

function TopnavCta({ palette, href, newTab, onClick, children }: TopnavCtaProps) {
  const variant = palette.ctaVariant
  const className = cn(
    variant === 'darkPrimary' &&
      'hover:brightness-105 active:brightness-95',
  )

  if (href) {
    return (
      <Button
        asChild
        variant={variant}
        size="sm"
        className={className}
        style={{
          background: palette.ctaBg,
          color: palette.ctaFg,
        }}
      >
        <a
          href={href}
          target={newTab ? '_blank' : undefined}
          rel={newTab ? 'noopener noreferrer' : undefined}
          onClick={onClick}
        >
          {children}
        </a>
      </Button>
    )
  }

  return (
    <Button
      type="button"
      variant={variant}
      size="sm"
      className={className}
      style={{
        background: palette.ctaBg,
        color: palette.ctaFg,
      }}
      onClick={onClick}
    >
      {children}
    </Button>
  )
}

/* --------------------------------------------------------------------------
 * Atome — text-link discret (DS .text-link)
 * -------------------------------------------------------------------------- */

interface TopnavTextLinkProps {
  palette: TopnavPalette
  href?: string
  onClick?: (e: React.MouseEvent) => void
  children: React.ReactNode
}

function TopnavTextLink({ palette, href, onClick, children }: TopnavTextLinkProps) {
  const base = cn(
    'inline-flex items-center font-ui text-[14px] font-medium leading-none no-underline',
    'transition-[color] duration-150 ease-out hover:underline hover:underline-offset-[3px]',
  )
  const style = { color: palette.textLinkColor }
  if (href) {
    return (
      <a href={href} className={base} style={style} onClick={onClick}>
        {children}
      </a>
    )
  }
  return (
    <button type="button" className={cn(base, 'border-0 bg-transparent cursor-pointer p-0')} style={style} onClick={onClick}>
      {children}
    </button>
  )
}

/* --------------------------------------------------------------------------
 * Composant principal
 * -------------------------------------------------------------------------- */

export function Navigation({
  className,
  menuItems: propMenuItems,
  brand,
  menuTheme,
  showLanguageSwitcher = true,
  publicLocales: publicLocalesProp,
  // Props legacy conservées en signature mais ignorées (auto-detect prend le relais).
  transparent: _transparent,
  themeColor: _themeColor,
  overlayHeroSecondary: _overlayHeroSecondary,
  overlayHeroHomeLight: _overlayHeroHomeLight,
  overlayBlogHero: _overlayBlogHero,
  ...props
}: NavigationProps) {
  void _transparent
  void _themeColor
  void _overlayHeroSecondary
  void _overlayHeroHomeLight
  void _overlayBlogHero

  const pathname = usePathname() ?? ''
  const publicLocales = publicLocalesProp ?? [...supportedLocales]
  const navLocale = getActiveLocaleFromPathname(pathname)
  const surface = useTopnavSurfaceObserver()
  const palette = buildTopnavPalettes(menuTheme)[surface]

  const [mobileOpen, setMobileOpen] = React.useState(false)

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

  /* ---------- Construction des items CMS (compat back-office) ---------- */

  const fallbackMenuItems: MenuItem[] = [
    { id: 'fallback-home', label: siteCommonCta(navLocale, 'fallback_menu_home'), urlPath: `/${navLocale}`, order: 0, type: 'LINK', isRoot: true },
    { id: 'fallback-projects', label: siteCommonCta(navLocale, 'fallback_menu_projects'), urlPath: `/${navLocale}/projects`, order: 1, type: 'LINK' },
    { id: 'fallback-vaults', label: siteCommonCta(navLocale, 'fallback_menu_vaults'), urlPath: '/vaults', order: 2, type: 'LINK' },
    { id: 'fallback-about', label: siteCommonCta(navLocale, 'fallback_menu_about'), urlPath: `/${navLocale}/about`, order: 3, type: 'LINK' },
    { id: 'fallback-contact', label: siteCommonCta(navLocale, 'fallback_menu_contact'), urlPath: `/${navLocale}/contact`, order: 4, type: 'LINK' },
    { id: 'fallback-login', label: siteCommonCta(navLocale, 'fallback_menu_login'), urlPath: '/app/login', order: 10, type: 'BUTTON', buttonStyle: 'primary', externalUrl: '/app/login' },
  ]

  const menuItems = propMenuItems && propMenuItems.length > 0 ? propMenuItems : fallbackMenuItems

  const rawLinkItems = menuItems.filter((item) => (item.type || 'LINK') === 'LINK')
  const rawButtonItems = menuItems.filter((item) => (item.type || 'LINK') === 'BUTTON')

  /**
   * Certains items édités côté back-office sont enregistrés en BUTTON "text"
   * alors qu'ils représentent un lien de navigation primaire (ex. À propos).
   * On les remonte dans la zone des liens pour conserver l'alignement DS.
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

  const isActive = (item: MenuItem) => isNavItemActive(pathname, item, navLocale)

  /** DS strict — un seul CTA primary à droite, le premier bouton CMS. */
  const primaryCta = buttonItems[0] ?? null

  const handleCtaClick = (item: MenuItem) => (e: React.MouseEvent) => {
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

  /* ---------- Style de la barre (background, border, transition 480ms) ---------- */

  const navBarStyle: React.CSSProperties = {
    background: palette.background,
    borderBottom: palette.borderBottom,
    transition:
      'background 480ms var(--v-ease-in-out), border-color 480ms var(--v-ease-in-out), backdrop-filter 480ms var(--v-ease-in-out)',
  }

  /* ---------- Rendu d'un item de liens (link ou group dégradé) ---------- */

  const renderPrimaryLink = (item: MenuItem) => {
    const navKind = item.navigationNodeKind ?? 'PAGE'
    const active = isActive(item)

    if (navKind === 'EXTERNAL_LINK') {
      const raw = (item.urlPath || '').trim()
      const href = shouldSkipLocalizePublicHref(raw) ? raw : localizePublicInternalHref(raw, navLocale)
      const newTab = item.openInNewTab || isPublicHrefExternalNavigation(href)
      return (
        <TopnavLink key={item.id} href={href} active={active} palette={palette} external newTab={newTab}>
          {item.label}
        </TopnavLink>
      )
    }

    if (navKind === 'GROUP') {
      const fallbackHref = resolveGroupFallbackHref(item, navLocale)
      if (fallbackHref) {
        return (
          <TopnavLink key={item.id} href={fallbackHref} active={active} palette={palette}>
            {item.label}
          </TopnavLink>
        )
      }
      // Sans sous-page : item inactif (label seul, sans href).
      return (
        <span
          key={item.id}
          className="inline-flex items-center font-ui text-[14px] font-medium leading-none py-1.5"
          style={{ color: palette.linkColor, opacity: 0.6 }}
        >
          {item.label}
        </span>
      )
    }

    const href = localizePublicInternalHref(item.urlPath, navLocale)
    return (
      <TopnavLink key={item.id} href={href} active={active} palette={palette}>
        {item.label}
      </TopnavLink>
    )
  }

  /* ---------- Logo (filtre inversé sur surfaces sombres) ---------- */

  const logoNode = (
    <a
      href={`/${navLocale}`}
      className="inline-flex items-center no-underline"
      aria-label={siteCommonCta(navLocale, 'nav_home_aria')}
      style={{ height: 22 }}
    >
      <BrandLogo
        brand={brand}
        lockup="horizontal"
        color="black"
        className="block h-[22px] w-auto"
        style={{
          // DS strict : un seul SVG noir, filtré inversé pour surfaces sombres
          // (équivalent `filter: brightness(0) invert(1)` du topnav.css).
          filter: palette.logoInvert ? 'brightness(0) invert(1)' : undefined,
          transition: 'filter 480ms var(--v-ease-in-out)',
        }}
      />
    </a>
  )

  return (
    <nav
      data-topnav-surface={surface}
      className={cn(
        'fixed left-0 right-0 top-0 z-50 box-border w-full',
        className,
      )}
      style={{ ...navBarStyle, height: TOPNAV_HEIGHT_PX }}
      {...props}
    >
      {/*
        Même `<Container>` DS que le body / footer (`.v-container`, max 1280px).
        Layout grid 3 colonnes 1fr auto 1fr (logo · liens · actions), gap 32px.
        Liens en hauteur pleine ; underline actif à -bottom-px (recouvre border-bottom).
      */}
      <Container className="h-full">
        <div className="grid h-full grid-cols-[1fr_auto_1fr] items-stretch gap-8">
          {/* Col 1 — logo (gauche) */}
          <div className="flex h-full items-center justify-self-start">{logoNode}</div>

          {/* Col 2 — liens centraux (cachés ≤ 1024px) */}
          <nav
            aria-label="Navigation principale"
            className="hidden h-full justify-self-center lg:block"
          >
            <ul className="flex h-full list-none items-stretch gap-8 m-0 p-0">
              {linkItems.map((item) => (
                <li key={item.id} className="flex h-full">
                  {renderPrimaryLink(item)}
                </li>
              ))}
            </ul>
          </nav>

          {/* Col 3 — actions droite */}
          <div className="flex h-full items-center justify-end gap-5 sm:gap-3 justify-self-end">
            {/* Sélecteur de langue — text-link discret (atome DS .text-link) */}
            {showLanguageSwitcher && publicLocales.length > 1 ? (
              <div className="hidden sm:contents">
                <LanguageSwitcherInline palette={palette} enabledLocales={publicLocales} />
              </div>
            ) : null}

            {/* CTA primary unique (DS strict : 1 seul bouton à droite) */}
            {primaryCta ? (
              <div className="hidden lg:block">
                <TopnavCta
                  palette={palette}
                  href={navActionButtonHref(primaryCta, navLocale) ?? undefined}
                  newTab={
                    !!navActionButtonHref(primaryCta, navLocale) &&
                    isPublicHrefExternalNavigation(
                      navActionButtonHref(primaryCta, navLocale)!,
                    )
                  }
                  onClick={handleCtaClick(primaryCta)}
                >
                  {primaryCta.label}
                </TopnavCta>
              </div>
            ) : null}

            {/* CTA primary mobile (visible < 1024px à côté du burger) */}
            {primaryCta ? (
              <div className="lg:hidden">
                <TopnavCta
                  palette={palette}
                  href={navActionButtonHref(primaryCta, navLocale) ?? undefined}
                  newTab={
                    !!navActionButtonHref(primaryCta, navLocale) &&
                    isPublicHrefExternalNavigation(
                      navActionButtonHref(primaryCta, navLocale)!,
                    )
                  }
                  onClick={handleCtaClick(primaryCta)}
                >
                  {primaryCta.label}
                </TopnavCta>
              </div>
            ) : null}

            {/* Burger — visible ≤ 1024px */}
            <button
              type="button"
              className={cn(
                'relative h-10 w-10 p-2 lg:hidden transition-colors duration-300',
                'border-0 bg-transparent cursor-pointer',
              )}
              aria-expanded={mobileOpen}
              aria-label={siteCommonCta(navLocale, 'nav_menu_toggle_aria')}
              onClick={() => setMobileOpen((o) => !o)}
              style={{ color: palette.linkColor }}
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
      </Container>

      {/* Drawer mobile plein écran — fond DS bg, items DS-compatibles */}
      {mobileOpen ? (
        <div
          className={cn(
            'fixed inset-x-0 top-0 z-[60] flex h-[100dvh] flex-col overflow-hidden bg-v-bg lg:hidden',
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
              {showLanguageSwitcher && publicLocales.length > 1 ? (
                <LanguageSwitcher
                  variant="drawer-row"
                  themeColor="light"
                  enabledLocales={publicLocales}
                />
              ) : null}
            </div>
            {buttonItems.length > 1 ? (
              <div className="shrink-0 border-t border-v-fg/[0.06] bg-v-bg px-4 py-4">
                <div className="mx-auto flex w-full max-w-md flex-col gap-3">
                  {buttonItems.slice(1).map((item) => (
                    <a
                      key={item.id}
                      href={navActionButtonHref(item, navLocale) ?? '#'}
                      onClick={handleCtaClick(item)}
                      className={cn(
                        'inline-flex w-full items-center justify-center gap-2 whitespace-nowrap font-ui text-[14px] font-medium leading-none',
                        'py-[14px] px-6 rounded-v-pill no-underline',
                        'bg-v-fg text-white hover:bg-[#3B3633] transition-[background-color] duration-150 ease-out',
                      )}
                    >
                      {item.label}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </nav>
  )
}

/* --------------------------------------------------------------------------
 * Adapter inline pour LanguageSwitcher (palette DS dynamique)
 * -------------------------------------------------------------------------- */

function LanguageSwitcherInline({
  palette,
  enabledLocales,
}: {
  palette: TopnavPalette
  enabledLocales: Locale[]
}) {
  const themeColor: 'dark' | 'light' = palette.logoInvert ? 'dark' : 'light'
  return (
    <LanguageSwitcher
      themeColor={themeColor}
      variant="toolbar-icon"
      enabledLocales={enabledLocales}
    />
  )
}

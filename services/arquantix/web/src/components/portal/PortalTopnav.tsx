'use client'

import * as React from 'react'
import Link from 'next/link'
import { Loader2 } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { BrandLogo, type SiteBrandLogo } from '@/components/ui/BrandLogo'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import { buildTopnavPalettes } from '@/lib/cms/site-menu-theme'
import { TOPNAV_HEIGHT_PX } from '@/hooks/useTopnavSurfaceObserver'
import { PORTAL_PATH_PREFIX, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { markPortalPrivySessionReset } from '@/components/portal/PortalAuthPrivySessionHygiene'
import { preloadPrivyPortalProvider } from '@/lib/portal/preloadPrivyPortalProvider'
import {
  PORTAL_MAIN_NAV_TABS,
  PORTAL_SEARCH_NAV,
} from '@/lib/portal/portalNavModel'
import type { PortalDashboardProfile } from '@/lib/portal/dashboardTypes'
import { resolvePortalProfileInitials } from '@/lib/portal/resolveProfileInitials'
import { useNavPending } from '@/components/site/NavPendingContext'
import { PortalLogoutOverlay } from '@/components/portal/PortalLogoutOverlay'

function normalizePath(path: string): string {
  const trimmed = path.replace(/\/$/, '')
  return trimmed || '/'
}

function isNavActive(pathname: string, href: string): boolean {
  const current = normalizePath(pathname)
  const target = normalizePath(href)
  if (target === PORTAL_ROUTES.dashboard) {
    return current === target || current === PORTAL_PATH_PREFIX
  }
  return current === target || current.startsWith(`${target}/`)
}

interface TopnavLinkProps {
  href: string
  active: boolean
  palette: ReturnType<typeof buildTopnavPalettes>['solid']
  onClick?: () => void
  children: React.ReactNode
}

function TopnavLink({ href, active, palette, onClick, children }: TopnavLinkProps) {
  const { setPendingPath } = useNavPending()

  return (
    <Link
      href={href}
      onClick={() => {
        setPendingPath(href)
        onClick?.()
      }}
      aria-current={active ? 'page' : undefined}
      className={cn(
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
    </Link>
  )
}

type PortalTopnavProps = {
  initials?: string
  brand?: SiteBrandLogo | null
  className?: string
}

/**
 * Topnav portail — même grammaire DS que {@link Navigation} (72px, grid 3 cols,
 * liens underline), avec les tabs mobile (Home / Invest / Markets / Design)
 * + action Search + profil + déconnexion.
 */
export function PortalTopnav({ initials: initialsProp, brand: brandProp, className }: PortalTopnavProps) {
  const pathname = usePathname() ?? ''
  const router = useRouter()
  const { effectivePath, setPendingPath } = useNavPending()
  const palette = buildTopnavPalettes(null).solid
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [loggingOut, setLoggingOut] = React.useState(false)
  const [initials, setInitials] = React.useState(initialsProp ?? '')
  const [brand, setBrand] = React.useState<SiteBrandLogo | null | undefined>(brandProp)

  React.useEffect(() => {
    if (initialsProp) {
      setInitials(initialsProp)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/portal/profile', { credentials: 'include', cache: 'no-store' })
        if (!res.ok) return
        const json = (await res.json()) as { profile?: PortalDashboardProfile | null }
        if (!cancelled) {
          setInitials(resolvePortalProfileInitials(json.profile))
        }
      } catch {
        // ignore — avatar fallback below
      }
    })()
    return () => {
      cancelled = true
    }
  }, [initialsProp])

  React.useEffect(() => {
    if (brandProp) {
      setBrand(brandProp)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/site/brand-logo?locale=fr')
        if (!res.ok) return
        const json = (await res.json()) as SiteBrandLogo
        if (!cancelled) setBrand(json)
      } catch {
        // ignore — fallback logo below
      }
    })()
    return () => {
      cancelled = true
    }
  }, [brandProp])

  React.useEffect(() => {
    if (!mobileOpen && !loggingOut) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [mobileOpen, loggingOut])

  const handleLogoutPrefetch = () => {
    router.prefetch(PORTAL_ROUTES.login)
    preloadPrivyPortalProvider()
  }

  const handleLogout = () => {
    if (loggingOut) return
    setLoggingOut(true)
    setMobileOpen(false)
    markPortalPrivySessionReset()
    invalidatePortalCache()
    preloadPrivyPortalProvider()
    router.prefetch(PORTAL_ROUTES.login)

    void fetch('/api/portal/logout', { method: 'POST', credentials: 'include' })
      .then(() => {
        router.replace(PORTAL_ROUTES.login)
      })
      .catch((err) => {
        console.error('[portal/logout]', err)
        setLoggingOut(false)
      })
  }

  const avatarLabel = initials.trim().slice(0, 2).toUpperCase() || '?'
  const profileActive = isNavActive(effectivePath, PORTAL_ROUTES.profile)

  const navBarStyle: React.CSSProperties = {
    background: palette.background,
    borderBottom: palette.borderBottom,
    height: TOPNAV_HEIGHT_PX,
  }

  return (
    <>
      {loggingOut ? <PortalLogoutOverlay variant="below-topnav" /> : null}

      <nav
        data-topnav-surface="solid"
        className={cn('fixed left-0 right-0 top-0 z-50 box-border w-full', className)}
        style={navBarStyle}
      >
      <Container className="h-full">
        <div className="grid h-full grid-cols-[1fr_auto_1fr] items-stretch gap-8">
          <div className="flex h-full items-center justify-self-start">
            <Link
              href={PORTAL_ROUTES.dashboard}
              className="inline-flex items-center no-underline"
              aria-label="Vancelian"
              style={{ height: 22 }}
            >
              <BrandLogo
                brand={brand}
                lockup="horizontal"
                color="black"
                className="block h-[22px] w-auto"
              />
            </Link>
          </div>

          <nav aria-label="Navigation portail" className="hidden h-full justify-self-center lg:block">
            <ul className="m-0 flex h-full list-none items-stretch gap-8 p-0">
              {PORTAL_MAIN_NAV_TABS.map((tab) => (
                <li key={tab.id} className="flex h-full">
                  <TopnavLink href={tab.href} active={isNavActive(effectivePath, tab.href)} palette={palette}>
                    {tab.label}
                  </TopnavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="flex h-full items-center justify-end gap-3 justify-self-end sm:gap-4">
            <Link
              href={PORTAL_SEARCH_NAV.href}
              onClick={() => setPendingPath(PORTAL_SEARCH_NAV.href)}
              aria-label={PORTAL_SEARCH_NAV.label}
              className={cn(
                'hidden h-10 w-10 items-center justify-center rounded-v-pill lg:inline-flex',
                'transition-colors duration-v-fast hover:bg-v-fg-05',
                isNavActive(effectivePath, PORTAL_SEARCH_NAV.href) && 'bg-v-fg-05',
              )}
              style={{ color: palette.linkColor }}
            >
              <PORTAL_SEARCH_NAV.icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
            </Link>

            <Link
              href={PORTAL_ROUTES.profile}
              onClick={() => setPendingPath(PORTAL_ROUTES.profile)}
              aria-label="Profile"
              aria-current={profileActive ? 'page' : undefined}
              className={cn(
                'inline-flex h-9 w-9 items-center justify-center rounded-v-pill font-ui text-[12px] font-semibold text-white transition-opacity duration-v-fast hover:opacity-90',
                profileActive ? 'ring-2 ring-v-terracotta ring-offset-2 ring-offset-v-bg' : '',
              )}
              style={{ background: 'var(--v-fg)' }}
            >
              {avatarLabel}
            </Link>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="hidden sm:inline-flex"
              disabled={loggingOut}
              aria-busy={loggingOut || undefined}
              onMouseEnter={handleLogoutPrefetch}
              onFocus={handleLogoutPrefetch}
              onClick={() => void handleLogout()}
            >
              Sign out
              {loggingOut ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : null}
            </Button>

            <button
              type="button"
              className={cn(
                'relative h-10 w-10 p-2 lg:hidden',
                'cursor-pointer border-0 bg-transparent transition-colors duration-300',
              )}
              aria-expanded={mobileOpen}
              aria-label="Menu"
              onClick={() => setMobileOpen((open) => !open)}
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

      {mobileOpen ? (
        <div className="fixed inset-x-0 top-0 z-[60] flex h-[100dvh] flex-col overflow-hidden bg-v-bg lg:hidden">
          <div className="mx-auto flex min-h-0 w-full min-w-0 max-w-lg flex-1 flex-col pt-[5.5rem]">
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6">
              <ul className="m-0 flex list-none flex-col gap-1 p-0">
                {PORTAL_MAIN_NAV_TABS.map((tab) => {
                  const active = isNavActive(effectivePath, tab.href)
                  return (
                    <li key={tab.id}>
                      <Link
                        href={tab.href}
                        onClick={() => {
                          setPendingPath(tab.href)
                          setMobileOpen(false)
                        }}
                        className={cn(
                          'flex items-center gap-3 rounded-v-input px-3 py-3 font-ui text-[16px] font-medium no-underline',
                          active ? 'bg-v-fg-05 text-v-fg' : 'text-v-fg-body',
                        )}
                      >
                        <tab.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
                        {tab.label}
                      </Link>
                    </li>
                  )
                })}
                <li>
                  <Link
                    href={PORTAL_SEARCH_NAV.href}
                    onClick={() => {
                      setPendingPath(PORTAL_SEARCH_NAV.href)
                      setMobileOpen(false)
                    }}
                    className={cn(
                      'flex items-center gap-3 rounded-v-input px-3 py-3 font-ui text-[16px] font-medium no-underline',
                      isNavActive(effectivePath, PORTAL_SEARCH_NAV.href)
                        ? 'bg-v-fg-05 text-v-fg'
                        : 'text-v-fg-body',
                    )}
                  >
                    <PORTAL_SEARCH_NAV.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
                    {PORTAL_SEARCH_NAV.label}
                  </Link>
                </li>
              </ul>
              <div className="mt-6 border-t border-v-fg-10 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={loggingOut}
                  aria-busy={loggingOut || undefined}
                  onMouseEnter={handleLogoutPrefetch}
                  onFocus={handleLogoutPrefetch}
                  onClick={() => void handleLogout()}
                >
                  Sign out
                  {loggingOut ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : null}
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </nav>
    </>
  )
}

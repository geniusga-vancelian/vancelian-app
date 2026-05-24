'use client'

import * as React from 'react'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { BrandLogo, type SiteBrandLogo } from '@/components/ui/BrandLogo'
import { Container } from '@/components/ui/Container'
import { buildTopnavPalettes } from '@/lib/cms/site-menu-theme'
import { TOPNAV_HEIGHT_PX } from '@/hooks/useTopnavSurfaceObserver'
import { PORTAL_PATH_PREFIX, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { readPortalCache } from '@/lib/portal/portalClientCache'
import { PortalSignOutButton } from '@/components/portal/PortalSignOutButton'
import { warmPortalRoute } from '@/lib/portal/portalNavWarmup'
import {
  PORTAL_MAIN_NAV_TABS,
  PORTAL_SEARCH_NAV,
} from '@/lib/portal/portalNavModel'
import { Wallet } from 'lucide-react'
import type { PortalDashboardProfile } from '@/lib/portal/dashboardTypes'
import { resolvePortalProfileInitials } from '@/lib/portal/resolveProfileInitials'
import { useNavPending } from '@/components/site/NavPendingContext'

type ProfileAvatarState = {
  initials: string
  loaded: boolean
}

function resolveInitialProfileState(initialsProp?: string): ProfileAvatarState {
  if (initialsProp?.trim()) {
    return {
      initials: initialsProp.trim().slice(0, 2).toUpperCase(),
      loaded: true,
    }
  }
  const cached = readPortalCache<{ profile?: PortalDashboardProfile | null }>('portal:profile')
  if (cached?.profile) {
    const resolved = resolvePortalProfileInitials(cached.profile)
    if (resolved) return { initials: resolved, loaded: true }
  }
  return { initials: '', loaded: false }
}

function resolveAvatarLabel(initials: string): string {
  return initials.trim().slice(0, 2).toUpperCase() || '?'
}

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
  return (
    <PortalNavLink
      href={href}
      onClick={() => onClick?.()}
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
    </PortalNavLink>
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
  const { effectivePath } = useNavPending()
  const palette = buildTopnavPalettes(null).solid
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [profileAvatar, setProfileAvatar] = React.useState<ProfileAvatarState>(() =>
    resolveInitialProfileState(initialsProp),
  )
  const [brand, setBrand] = React.useState<SiteBrandLogo | null | undefined>(brandProp)

  React.useEffect(() => {
    warmPortalRoute(PORTAL_ROUTES.profile, router)
  }, [router])

  React.useEffect(() => {
    if (initialsProp?.trim()) {
      setProfileAvatar({
        initials: initialsProp.trim().slice(0, 2).toUpperCase(),
        loaded: true,
      })
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/portal/profile', { credentials: 'include', cache: 'no-store' })
        if (cancelled) return
        if (!res.ok) {
          setProfileAvatar((prev) =>
            prev.loaded ? prev : { initials: resolveAvatarLabel(''), loaded: true },
          )
          return
        }
        const json = (await res.json()) as { profile?: PortalDashboardProfile | null }
        if (!cancelled) {
          const resolved = resolvePortalProfileInitials(json.profile)
          setProfileAvatar({ initials: resolved, loaded: true })
        }
      } catch {
        if (!cancelled) {
          setProfileAvatar((prev) =>
            prev.loaded ? prev : { initials: resolveAvatarLabel(''), loaded: true },
          )
        }
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
    if (!mobileOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [mobileOpen])

  const avatarLabel = resolveAvatarLabel(profileAvatar.initials)
  const profileActive = isNavActive(effectivePath, PORTAL_ROUTES.profile)
  const myWalletsActive = isNavActive(effectivePath, PORTAL_ROUTES.myWallets)

  const navBarStyle: React.CSSProperties = {
    background: palette.background,
    borderBottom: palette.borderBottom,
    height: TOPNAV_HEIGHT_PX,
  }

  return (
    <>
      <nav
        data-topnav-surface="solid"
        className={cn('fixed left-0 right-0 top-0 z-50 box-border w-full', className)}
        style={navBarStyle}
      >
      <Container className="h-full">
        <div className="grid h-full grid-cols-[1fr_auto_1fr] items-stretch gap-8">
          <div className="flex h-full items-center justify-self-start">
            <PortalNavLink
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
            </PortalNavLink>
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
            <PortalNavLink
              href={PORTAL_SEARCH_NAV.href}
              aria-label={PORTAL_SEARCH_NAV.label}
              className={cn(
                'hidden h-10 w-10 items-center justify-center rounded-v-pill lg:inline-flex',
                'transition-colors duration-v-fast hover:bg-v-fg-05',
                isNavActive(effectivePath, PORTAL_SEARCH_NAV.href) && 'bg-v-fg-05',
              )}
              style={{ color: palette.linkColor }}
            >
              <PORTAL_SEARCH_NAV.icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
            </PortalNavLink>

            <PortalNavLink
              href={PORTAL_ROUTES.myWallets}
              aria-label="My wallets"
              aria-current={myWalletsActive ? 'page' : undefined}
              className={cn(
                'hidden h-9 items-center gap-1.5 rounded-v-pill px-3 font-ui text-[13px] font-medium no-underline sm:inline-flex',
                'transition-colors duration-v-fast hover:bg-v-fg-05',
                myWalletsActive && 'bg-v-fg-05',
              )}
              style={{ color: palette.linkColor }}
            >
              <Wallet className="h-4 w-4 shrink-0" strokeWidth={1.75} aria-hidden />
              My wallets
            </PortalNavLink>

            {!profileAvatar.loaded ? (
              <div
                className="portal-shimmer h-9 w-9 shrink-0 rounded-v-pill"
                role="status"
                aria-live="polite"
                aria-label="Loading profile"
              />
            ) : (
              <PortalNavLink
                href={PORTAL_ROUTES.profile}
                aria-label="Profile"
                aria-current={profileActive ? 'page' : undefined}
                className={cn(
                  'portal-reveal inline-flex h-9 w-9 items-center justify-center rounded-v-pill font-ui text-[12px] font-semibold text-white transition-opacity duration-v-fast hover:opacity-90',
                  profileActive ? 'ring-2 ring-v-terracotta ring-offset-2 ring-offset-v-bg' : '',
                )}
                style={{ background: 'var(--v-fg)' }}
              >
                {avatarLabel}
              </PortalNavLink>
            )}

            <PortalSignOutButton className="hidden sm:inline-flex" />

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
                      <PortalNavLink
                        href={tab.href}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                          'flex items-center gap-3 rounded-v-input px-3 py-3 font-ui text-[16px] font-medium no-underline',
                          active ? 'bg-v-fg-05 text-v-fg' : 'text-v-fg-body',
                        )}
                      >
                        <tab.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
                        {tab.label}
                      </PortalNavLink>
                    </li>
                  )
                })}
                <li>
                  <PortalNavLink
                    href={PORTAL_SEARCH_NAV.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-v-input px-3 py-3 font-ui text-[16px] font-medium no-underline',
                      isNavActive(effectivePath, PORTAL_SEARCH_NAV.href)
                        ? 'bg-v-fg-05 text-v-fg'
                        : 'text-v-fg-body',
                    )}
                  >
                    <PORTAL_SEARCH_NAV.icon className="h-5 w-5 shrink-0" strokeWidth={1.75} />
                    {PORTAL_SEARCH_NAV.label}
                  </PortalNavLink>
                </li>
                <li>
                  <PortalNavLink
                    href={PORTAL_ROUTES.myWallets}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-v-input px-3 py-3 font-ui text-[16px] font-medium no-underline',
                      myWalletsActive ? 'bg-v-fg-05 text-v-fg' : 'text-v-fg-body',
                    )}
                  >
                    <Wallet className="h-5 w-5 shrink-0" strokeWidth={1.75} />
                    My wallets
                  </PortalNavLink>
                </li>
              </ul>
              <div className="mt-6 border-t border-v-fg-10 pt-4">
                <PortalSignOutButton className="w-full" />
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </nav>
    </>
  )
}

'use client'

import Link from 'next/link'
import type { ComponentProps } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useNavPending } from '@/components/site/NavPendingContext'
import { shouldBeginPortalNavigation } from '@/lib/portal/portalNavInstantFeedback'
import { isPortalPathname } from '@/lib/portal/portalRouting'
import { warmPortalRoute } from '@/lib/portal/portalNavWarmup'

export type PortalNavLinkProps = ComponentProps<typeof Link>

type LinkPropsHref = PortalNavLinkProps['href']

function hrefToPath(href: LinkPropsHref): string {
  if (typeof href === 'string') return href.split('?')[0] ?? href
  if (typeof href === 'object' && href !== null && 'pathname' in href && href.pathname) {
    return href.pathname.split('?')[0] ?? href.pathname
  }
  return ''
}

/** Lien portail — navigation optimiste (skeleton immédiat) + prefetch / warm cache. */
export function PortalNavLink({
  href,
  children,
  onClick,
  onPointerEnter,
  onFocus,
  ...rest
}: PortalNavLinkProps) {
  const router = useRouter()
  const pathname = usePathname() ?? ''
  const { beginNavigation } = useNavPending()
  const path = hrefToPath(href)
  const isInternalPortal = path ? isPortalPathname(path) : false

  const handleWarm = () => {
    if (isInternalPortal) warmPortalRoute(path, router)
  }

  const triggerOptimisticNav = () => {
    if (!isInternalPortal || !path) return
    if (!shouldBeginPortalNavigation(pathname, path)) return
    handleWarm()
    beginNavigation(path)
  }

  return (
    <Link
      href={href}
      prefetch={isInternalPortal ? true : undefined}
      onPointerEnter={(event) => {
        handleWarm()
        onPointerEnter?.(event)
      }}
      onFocus={(event) => {
        handleWarm()
        onFocus?.(event)
      }}
      onPointerDown={(event) => {
        if (event.button === 0) triggerOptimisticNav()
      }}
      onClick={(event) => {
        triggerOptimisticNav()
        onClick?.(event)
      }}
      {...rest}
    >
      {children}
    </Link>
  )
}

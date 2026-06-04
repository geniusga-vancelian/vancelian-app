'use client'

import Link from 'next/link'
import type { ComponentProps } from 'react'
import { useRouter } from 'next/navigation'
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

/** Lien portail — Next Link natif (URL-first) + prefetch au survol. */
export function PortalNavLink({
  href,
  children,
  onClick,
  onPointerEnter,
  onFocus,
  ...rest
}: PortalNavLinkProps) {
  const router = useRouter()
  const path = hrefToPath(href)
  const isInternalPortal = path ? isPortalPathname(path) : false

  const handleWarm = () => {
    if (isInternalPortal) warmPortalRoute(path, router)
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
      onClick={(event) => {
        if (isInternalPortal) handleWarm()
        onClick?.(event)
      }}
      {...rest}
    >
      {children}
    </Link>
  )
}

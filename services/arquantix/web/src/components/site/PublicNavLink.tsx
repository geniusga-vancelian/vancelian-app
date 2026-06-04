'use client'

import Link from 'next/link'
import * as React from 'react'
import {
  isPublicHrefExternalNavigation,
  shouldSkipLocalizePublicHref,
} from '@/lib/i18n/publicLocalizedRouting'

function isExternalNavHref(href: string): boolean {
  return shouldSkipLocalizePublicHref(href) || isPublicHrefExternalNavigation(href)
}

export type PublicNavLinkProps = React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string
}

/** Lien menu public : `next/link` en interne (SPA), `<a>` pour URLs externes. */
export function PublicNavLink({ href, children, onClick, ...rest }: PublicNavLinkProps) {
  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event)
  }

  if (isExternalNavHref(href)) {
    return (
      <a href={href} onClick={onClick} {...rest}>
        {children}
      </a>
    )
  }

  return (
    <Link href={href} onClick={handleClick} {...rest}>
      {children}
    </Link>
  )
}

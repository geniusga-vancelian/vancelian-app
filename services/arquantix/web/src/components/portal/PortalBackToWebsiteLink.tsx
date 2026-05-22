'use client'

import Link from 'next/link'
import * as React from 'react'
import { useSiteTransition } from '@/components/site/SiteTransitionContext'

type Props = React.ComponentProps<typeof Link>

/** Lien portail → site public avec overlay logo pendant le chargement. */
export function PortalBackToWebsiteLink({ href, onClick, ...rest }: Props) {
  const { startSiteTransition } = useSiteTransition()

  return (
    <Link
      href={href}
      onClick={(event) => {
        startSiteTransition()
        onClick?.(event)
      }}
      {...rest}
    />
  )
}

'use client'

import type { MouseEvent } from 'react'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Props = {
  href: string
  label: string
  onClick?: (event: MouseEvent<HTMLAnchorElement>) => void
}

/** Lien retour — handoff `.ofd-back` (Position.html · Compte.html). */
export function PortalDetailBackLink({ href, label, onClick }: Props) {
  return (
    <div className="ofd-back">
      <PortalNavLink href={href} className="ofd-back__link" onClick={onClick}>
        <KalaiIcon name="arrow-right" size={16} className="rotate-180" aria-hidden />
        {label}
      </PortalNavLink>
    </div>
  )
}

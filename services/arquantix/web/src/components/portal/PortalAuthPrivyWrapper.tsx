'use client'

import * as React from 'react'
import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'

type Props = {
  children: React.ReactNode
  appId: string
  /** Voie sign-out : diffère Privy d’une frame (formulaire seulement, shell CMS déjà rendu). */
  deferPrivy?: boolean
  /** Affiché dans la colonne formulaire avant le montage Privy. */
  deferPlaceholder?: React.ReactNode
}

/**
 * Encapsule Privy pour login / verify. En mode différé, seul le formulaire attend Privy —
 * le hero CMS reste streamé par le layout serveur.
 */
export function PortalAuthPrivyWrapper({
  children,
  appId,
  deferPrivy = false,
  deferPlaceholder = null,
}: Props) {
  const [mountPrivy, setMountPrivy] = React.useState(!deferPrivy)

  React.useEffect(() => {
    if (!deferPrivy || mountPrivy) return
    const frame = window.requestAnimationFrame(() => setMountPrivy(true))
    return () => window.cancelAnimationFrame(frame)
  }, [deferPrivy, mountPrivy])

  if (deferPrivy && !mountPrivy) {
    return <>{deferPlaceholder}</>
  }

  return <PortalAuthPrivyGate appId={appId}>{children}</PortalAuthPrivyGate>
}

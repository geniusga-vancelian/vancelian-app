'use client'

import type { ReactNode } from 'react'
import {
  SupportAsidePanel,
  hasSupportAsideContent,
  type SupportAsideContent,
} from '@/components/design-system/SupportAsidePanel'
import { usePortalSupportContent } from '@/components/portal/PortalSupportContentProvider'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  /** Surcharge ponctuelle du contenu CMS (rare). */
  support?: SupportAsideContent
  /** Masque la colonne Help — contenu pleine largeur (ex. Academy). */
  hideSupport?: boolean
  className?: string
}

/**
 * Layout dashboard portail — même grille 70 / 30 que le module FAQ site
 * (`lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16`).
 */
export function PortalDashboardLayout({
  children,
  support,
  hideSupport = false,
  className,
}: Props) {
  const cmsSupport = usePortalSupportContent()
  const resolvedSupport = support ?? cmsSupport
  const showSupport = !hideSupport && hasSupportAsideContent(resolvedSupport)

  return (
    <div
      className={cn(
        'grid grid-cols-1 items-start gap-12',
        showSupport && 'lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16',
        className,
      )}
    >
      <div className="flex min-w-0 flex-col gap-6 lg:gap-8">{children}</div>

      {showSupport ? (
        <SupportAsidePanel support={resolvedSupport} stickyTopClassName="lg:top-[96px]" />
      ) : null}
    </div>
  )
}

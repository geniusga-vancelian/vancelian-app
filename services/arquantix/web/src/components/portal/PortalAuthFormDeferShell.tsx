'use client'

import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  /** Privy / Captcha en cours — contenu visible avec léger flou, sans bloquer la page. */
  loading: boolean
  className?: string
}

/** Voile discret sur le panneau formulaire auth pendant le boot Privy en arrière-plan. */
export function PortalAuthFormDeferShell({ children, loading, className }: Props) {
  return (
    <div
      className={cn('portal-auth__form-defer', className)}
      aria-busy={loading}
      data-privy-booting={loading ? 'true' : 'false'}
    >
      <div className={cn('portal-auth__form-defer-content', loading && 'is-loading')}>
        {children}
      </div>
      {loading ? <div className="portal-auth__form-defer-veil" aria-hidden="true" /> : null}
    </div>
  )
}

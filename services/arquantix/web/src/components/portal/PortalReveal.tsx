'use client'

import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  /** Index pour le décalage stagger (max 8). */
  index?: number
  className?: string
}

/** Apparition progressive d’un module portail (stagger léger). */
export function PortalReveal({ children, index = 0, className }: Props) {
  return (
    <div
      className={cn('portal-reveal', className)}
      style={{ animationDelay: `${Math.min(index, 8) * 55}ms` }}
    >
      {children}
    </div>
  )
}

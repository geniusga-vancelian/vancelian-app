'use client'

import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/**
 * Zone main portail — le routeur Next pilote URL + contenu.
 * Transitions inter-onglets : `(shell)/loading.tsx` (preview stale ou skeleton destination).
 */
export function PortalShellMain({ children, className }: Props) {
  return <div className={cn('relative flex flex-1 flex-col', className)}>{children}</div>
}

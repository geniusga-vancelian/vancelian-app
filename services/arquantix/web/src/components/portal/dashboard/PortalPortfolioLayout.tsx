'use client'

import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  main: ReactNode
  side?: ReactNode
  className?: string
}

/** Grille portfolio — handoff Portfolio.html / Compte.html (`grid` · `col-main` · `col-side`). */
export function PortalPortfolioLayout({ main, side, className }: Props) {
  return (
    <div className={cn('portal-placer-grid', className)}>
      <div className="col-main">{main}</div>
      {side ? <aside className="col-side">{side}</aside> : null}
    </div>
  )
}

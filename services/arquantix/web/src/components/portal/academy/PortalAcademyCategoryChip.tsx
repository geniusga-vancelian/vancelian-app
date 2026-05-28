'use client'

import type { AppNewsCategoryDot } from '@/components/design-system/app/AppNewsStackedList'
import { cn } from '@/lib/utils'

type Props = {
  label: string
  tone?: AppNewsCategoryDot
  className?: string
}

/** Chip catégorie — handoff `.cchip` / `.cdot`. */
export function PortalAcademyCategoryChip({ label, tone = 'ink', className }: Props) {
  return (
    <span className={cn('cchip', className)}>
      <span className={cn('cdot', `cdot--${tone}`)} aria-hidden />
      {label}
    </span>
  )
}

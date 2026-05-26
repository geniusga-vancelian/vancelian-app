import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  /** `3` : 1 → 2 → 3 colonnes selon la largeur (Academy pleine largeur). Défaut : 2. */
  columns?: 2 | 3
}

/** Grille responsive cartes Actu / Flash — preview/26-cards-flash-actu. */
export function AppNewsDeck({ children, className, columns = 2 }: Props) {
  return (
    <div className={cn('news-deck', columns === 3 && 'news-deck--cols-3', className)}>
      {children}
    </div>
  )
}

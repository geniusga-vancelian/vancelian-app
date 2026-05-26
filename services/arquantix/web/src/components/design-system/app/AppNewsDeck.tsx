import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/** Deck horizontal scrollable — preview/26-cards-flash-actu. */
export function AppNewsDeck({ children, className }: Props) {
  return <div className={cn('news-deck', className)}>{children}</div>
}

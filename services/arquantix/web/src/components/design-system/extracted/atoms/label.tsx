import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { figmaDsLabelClassName } from '../tokens/typography'

export type LabelProps = {
  children: ReactNode
  className?: string
  /** Défaut `span` (pills, fragments de ligne). */
  as?: 'span' | 'p'
}

/**
 * Atome DS **Label** — Figma : Avenir Black 900, 10px, interligne 100 %, uppercase (`figmaDsLabelClassName`).
 */
export function Label({ children, className, as: Comp = 'span' }: LabelProps) {
  return <Comp className={cn(figmaDsLabelClassName, className)}>{children}</Comp>
}

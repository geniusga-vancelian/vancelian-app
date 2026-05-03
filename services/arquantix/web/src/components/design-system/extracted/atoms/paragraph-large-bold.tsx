import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { figmaDsParagraphLargeBoldClassName } from '../tokens/typography'

export interface ParagraphLargeBoldProps {
  children: ReactNode
  /** Défaut `#000000`. */
  color?: string
  className?: string
  as?: 'p' | 'span'
}

/**
 * Atome Figma **Paragraph Large Bold** — Avenir Heavy 800, 18px, lh 160 %, tracking −1 %.
 */
export function ParagraphLargeBold({
  children,
  color = '#000000',
  className,
  as: Comp = 'p',
}: ParagraphLargeBoldProps) {
  return (
    <Comp
      className={cn(figmaDsParagraphLargeBoldClassName, 'w-full not-italic', className)}
      style={{ color }}
    >
      {children}
    </Comp>
  )
}

/** @deprecated Préférer {@link ParagraphLargeBold}. */
export const FigmaParagraphLargeBold = ParagraphLargeBold

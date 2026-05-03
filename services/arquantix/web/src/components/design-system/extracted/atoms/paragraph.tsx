import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { figmaDsParagraphClassName } from '../tokens/typography'

export interface ParagraphProps {
  children: ReactNode
  /** Défaut `#000000`. */
  color?: string
  className?: string
  as?: 'p' | 'span'
}

/**
 * Atome Figma **Paragraph** — Avenir Book 350, 14px, interligne 160 %, interlettrage 0 %.
 * Pour plusieurs paragraphes avec 16px entre eux : envelopper avec `className={figmaDsParagraphStackGapClassName}`.
 */
export function Paragraph({
  children,
  color = '#000000',
  className,
  as: Comp = 'p',
}: ParagraphProps) {
  return (
    <Comp
      className={cn(figmaDsParagraphClassName, 'w-full not-italic', className)}
      style={{ color }}
    >
      {children}
    </Comp>
  )
}

/** @deprecated Préférer {@link Paragraph}. */
export const FigmaParagraph = Paragraph

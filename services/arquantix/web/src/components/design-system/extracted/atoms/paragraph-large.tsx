import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { figmaDsParagraphLargeClassName } from '../tokens/typography'

export interface ParagraphLargeProps {
  children: ReactNode
  /** Défaut `#000000`. */
  color?: string
  className?: string
  as?: 'p' | 'span'
}

/**
 * Atome Figma **Paragraph Large** — Avenir Roman 400, 18px, interligne 160 %, interlettrage 0 %.
 * Espacement entre paragraphes Figma : 16px (`mb-4` / `space-y-4` selon contexte).
 */
export function ParagraphLarge({
  children,
  color = '#000000',
  className,
  as: Comp = 'p',
}: ParagraphLargeProps) {
  return (
    <Comp
      className={cn(figmaDsParagraphLargeClassName, 'w-full not-italic', className)}
      style={{ color }}
    >
      {children}
    </Comp>
  )
}

/** @deprecated Préférer {@link ParagraphLarge}. */
export const FigmaParagraphLarge = ParagraphLarge

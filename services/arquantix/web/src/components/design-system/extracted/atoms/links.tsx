import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { figmaDsLinksClassName } from '../tokens/typography'

export interface LinksProps {
  children: ReactNode
  className?: string
  /** Défaut `#000000` — nav / footer : `text-white`, `text-[#62656e]`, etc. */
  color?: string
  /** Si défini, rend un `<a>` avec la typo **Links**. */
  href?: string
}

/**
 * Atome Figma **Links** (typographie) :
 * Avenir Heavy 800, 16px, line-height 100 %, letter-spacing 0 %.
 *
 * Jeton Tailwind : {@link figmaDsLinksClassName} — même chaîne que `NAV_PRIMARY_LINK_TYPO` (nav).
 */
export function Links({ children, className, color = '#000000', href }: LinksProps) {
  const cls = cn(figmaDsLinksClassName, 'not-italic', className)
  if (href != null && href !== '') {
    return (
      <a href={href} className={cls} style={{ color }}>
        {children}
      </a>
    )
  }
  return (
    <span className={cls} style={{ color }}>
      {children}
    </span>
  )
}

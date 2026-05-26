import * as React from 'react'
import { cn } from '@/lib/utils'

export interface AppEyebrowProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
  /** Variante tag fond warm (sections produit). */
  tagged?: boolean
  /** 10px — labels secondaires in-page. */
  size?: 'default' | 'sm'
  tone?: 'light' | 'dark' | 'inverse'
}

/**
 * Eyebrow webapp — spec App DS v1.2 :
 * Inter 600, 13px, letter-spacing 0.08em, UPPERCASE.
 * (Le site marketing utilise `VEyebrow` : 11px / 0.05em.)
 */
export function AppEyebrow({
  children,
  tagged = false,
  size = 'default',
  tone = 'light',
  className,
  ...rest
}: AppEyebrowProps) {
  const toneClass =
    tone === 'inverse'
      ? 'text-white/80'
      : tone === 'dark'
        ? 'text-v-fg-light'
        : 'text-v-fg-muted'

  return (
    <p
      {...rest}
      className={cn(
        'v-eyebrow m-0 font-ui',
        size === 'sm' && 'v-eyebrow--sm',
        tagged && 'v-eyebrow--tagged',
        toneClass,
        className,
      )}
    >
      {children}
    </p>
  )
}

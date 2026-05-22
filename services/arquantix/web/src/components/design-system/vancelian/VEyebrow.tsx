import * as React from 'react'
import { cn } from '@/lib/utils'

export interface VEyebrowProps extends React.HTMLAttributes<HTMLParagraphElement> {
  /** Texte de l'eyebrow (sera affiché en UPPERCASE). */
  children: React.ReactNode
  /**
   * `light` (défaut) : couleur `--v-fg-muted` sur fond clair.
   * `dark` : couleur `--v-fg-light` sur fond sombre.
   * `inverse` : couleur blanche translucide pour hero photo / final-cta.
   */
  tone?: 'light' | 'dark' | 'inverse'
}

/**
 * Vancelian — eyebrow caption.
 *
 * Atome typographique DS : Inter Medium 11px, letter-spacing 0.05em, UPPERCASE.
 * Spec : voir `.eyebrow` dans `colors_and_type.css` / `base.css` du pack handoff.
 * Couleur par défaut anthracite atténué (`--v-fg-muted`) — sur fond sombre,
 * basculer en `tone="dark"` ou `tone="inverse"`.
 *
 * Usage typique : surtitre `BRANDING · COULEURS` au-dessus d'un titre de section,
 * label de bloc, ligne d'intro éditoriale.
 */
export function VEyebrow({ children, tone = 'light', className, ...rest }: VEyebrowProps) {
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
        'v-caption font-ui font-medium text-[11px] uppercase tracking-[0.05em] leading-[1.4]',
        toneClass,
        className,
      )}
    >
      {children}
    </p>
  )
}

import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Tailles strictes DS Vancelian — la librairie Kalai ne s'utilise qu'en
 * 16 / 20 / 24 / 32 px. Toute autre taille est un bug par rapport au DS.
 */
export type KalaiIconSize = 16 | 20 | 24 | 32

export interface KalaiIconProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'children'> {
  /** Slug Kalai (ex: `arrow-right`, `bitcoin`, `shield-good`). */
  name: string
  /** Une des tailles canoniques DS (16 / 20 / 24 / 32). Défaut : 20. */
  size?: KalaiIconSize
  /**
   * Décoratif par défaut (`aria-hidden`). Passer un texte pour rendre
   * l'icône lisible aux lecteurs d'écran (`aria-label`).
   */
  title?: string
}

/**
 * Vancelian — composant icône Kalai.
 *
 * Doctrine DS :
 * - Monochrome filled, hérite de `color` du parent (équivalent `currentColor`).
 *   Implémenté via `mask-image` (le SVG est utilisé comme masque, la couleur
 *   vient de `background-color: currentColor`) — c'est la seule façon de
 *   garantir l'héritage de couleur sans inliner chaque SVG.
 * - Tailles strictes 16 / 20 / 24 / 32 (les classes `.v-icon--*`).
 * - Jamais teintée en terracotta (réservée aux text-links / accents éditoriaux).
 *
 * Usage :
 * ```tsx
 * <KalaiIcon name="arrow-right" size={20} className="text-v-fg" />
 * <KalaiIcon name="shield-good" size={24} title="Sécurisé" />
 * ```
 */
export function KalaiIcon({
  name,
  size = 20,
  title,
  className,
  style,
  ...rest
}: KalaiIconProps) {
  const url = `url(/icons/kalai/${name}.svg)`
  const accessibility = title
    ? { role: 'img' as const, 'aria-label': title }
    : { 'aria-hidden': true as const }

  return (
    <span
      {...accessibility}
      {...rest}
      className={cn('inline-block align-[-0.125em] bg-current', className)}
      style={{
        width: size,
        height: size,
        WebkitMaskImage: url,
        maskImage: url,
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
        ...style,
      }}
    />
  )
}

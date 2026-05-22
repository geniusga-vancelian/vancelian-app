import type { CSSProperties, ReactNode } from 'react'

import { colors, spacing } from '@/lib/admin/flutter-preview/tokens'

/**
 * Wrapper interne (rendu **dans l'iframe**) qui imite le `PageScaffold`
 * Flutter : background standard, padding latéral `s4`, et stratégie de
 * scroll cohérente.
 *
 * - `kind="page"` : padding standard, background `pageBackground`.
 * - `kind="module"` : background blanc, padding réduit pour un rendu
 *   centré sur le module isolé (pas de page autour).
 */
export function PreviewCanvas({
  children,
  kind = 'page',
  style,
}: {
  children: ReactNode
  kind?: 'page' | 'module'
  style?: CSSProperties
}) {
  const isModule = kind === 'module'
  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100%',
        boxSizing: 'border-box',
        backgroundColor: isModule ? colors.cardBackground : colors.pageBackground,
        padding: isModule ? spacing.s4 : 0,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

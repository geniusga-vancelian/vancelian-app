/**
 * Sémantique « navigation node » (niveau 1) — rétrocompatible : absent ou inconnu ⇒ PAGE.
 */
export type NavigationNodeKind = 'PAGE' | 'GROUP' | 'EXTERNAL_LINK'

export function parseNavigationNodeKind(
  raw: string | null | undefined,
): NavigationNodeKind {
  if (raw === 'GROUP' || raw === 'EXTERNAL_LINK') return raw
  return 'PAGE'
}

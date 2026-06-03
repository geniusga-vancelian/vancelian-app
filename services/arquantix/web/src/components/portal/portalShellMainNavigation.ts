/** Mode de rendu main portail pendant une navigation interne (G4-B1). */
export type PortalShellMainNavMode = 'idle' | 'preview' | 'keep-children'

export function resolvePortalShellMainNavMode(
  isNavigating: boolean,
  hasPreview: boolean,
): PortalShellMainNavMode {
  if (!isNavigating) return 'idle'
  if (hasPreview) return 'preview'
  return 'keep-children'
}

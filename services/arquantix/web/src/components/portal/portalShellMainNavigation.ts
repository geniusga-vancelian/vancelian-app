/** Mode de rendu transition shell — URL-first via segment loading Next. */
export type PortalShellSegmentLoadingMode = 'preview' | 'skeleton'

export function resolvePortalShellSegmentLoadingMode(hasPreview: boolean): PortalShellSegmentLoadingMode {
  return hasPreview ? 'preview' : 'skeleton'
}

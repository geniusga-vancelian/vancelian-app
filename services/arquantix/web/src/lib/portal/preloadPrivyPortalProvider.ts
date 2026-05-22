let privyPortalModulePromise: Promise<typeof import('@/components/portal/PrivyPortalProvider')> | null =
  null

/** Précharge le chunk Privy (~19 Mo) pendant la session authentifiée ou au logout. */
export function preloadPrivyPortalProvider():
  | Promise<typeof import('@/components/portal/PrivyPortalProvider')>
  | null {
  if (typeof window === 'undefined') return null
  privyPortalModulePromise ??= import('@/components/portal/PrivyPortalProvider')
  return privyPortalModulePromise
}

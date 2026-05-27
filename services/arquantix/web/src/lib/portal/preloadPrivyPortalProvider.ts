let privyPortalModulePromise: Promise<
  typeof import('@/components/portal/PrivyPortalProvider')
> | null = null

function isChunkLoadError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const name = 'name' in error ? String(error.name) : ''
  const message = 'message' in error ? String(error.message) : ''
  return (
    name === 'ChunkLoadError' ||
    message.includes('Loading chunk') ||
    message.includes('Failed to fetch dynamically imported module')
  )
}

/** Précharge le chunk Privy (~19 Mo) — erreurs absorbées (cache stale après rebuild dev). */
export function preloadPrivyPortalProvider(): void {
  if (typeof window === 'undefined') return

  privyPortalModulePromise ??= import('@/components/portal/PrivyPortalProvider')
  void privyPortalModulePromise.catch((error: unknown) => {
    privyPortalModulePromise = null
    if (isChunkLoadError(error)) {
      console.warn(
        '[portal] Privy chunk preload failed (stale cache after dev rebuild?). Hard refresh recommended.',
        error,
      )
      return
    }
    console.error('[portal] Privy chunk preload failed.', error)
  })
}

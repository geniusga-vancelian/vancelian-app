import { normalizeNavPath } from '@/components/site/NavPendingContext'

/** Démarre une navigation optimiste seulement si la destination diffère. */
export function shouldBeginPortalNavigation(currentPath: string, targetPath: string): boolean {
  return normalizeNavPath(currentPath) !== normalizeNavPath(targetPath)
}

export function resolveEffectiveNavPath(pendingPath: string | null, pathname: string): string {
  return pendingPath ?? normalizeNavPath(pathname)
}

/** Barre pending : visible dès que la destination optimiste ≠ pathname réel. */
export function resolveNavPendingBarVisible(pendingPath: string | null, pathname: string): boolean {
  if (!pendingPath) return false
  return normalizeNavPath(pendingPath) !== normalizeNavPath(pathname)
}

export function resolveNavIsNavigating(pendingPath: string | null, pathname: string): boolean {
  return resolveNavPendingBarVisible(pendingPath, pathname)
}

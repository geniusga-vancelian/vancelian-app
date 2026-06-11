/** Messages utilisateur pour les échecs resume / upstream bundle. */
export function normalizeBundleResumeError(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err)
  const haystack = msg.toLowerCase()

  if (
    haystack.includes('internal server error') ||
    haystack.includes('502') ||
    haystack.includes('bad gateway') ||
    haystack.includes('upstream_unavailable') ||
    haystack.includes('upstream_non_json') ||
    haystack.includes('service temporairement indisponible')
  ) {
    return 'Service temporairement indisponible — réessayez le rééquilibrage dans quelques instants.'
  }

  if (
    haystack.includes('timeout') ||
    haystack.includes('timed out') ||
    haystack.includes('signal timed out') ||
    haystack.includes('abort')
  ) {
    return 'La reprise du rééquilibrage a expiré — réessayez dans quelques instants.'
  }

  if (/no_running_rebalance|no running rebalance/i.test(msg)) {
    return 'Aucun rééquilibrage en cours à reprendre.'
  }

  return msg || 'Reprise du rééquilibrage impossible.'
}

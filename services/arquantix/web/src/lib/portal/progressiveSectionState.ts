/**
 * Machine à états pure pour le chargement progressif par section.
 *
 * Chaque "section" d'une page lourde (ex. markets → top / bundles / discover) est
 * chargée indépendamment : elle a son propre `loading` (shimmer) et arrive quand
 * son endpoint répond, sans attendre les autres sections.
 *
 * Ces fonctions sont volontairement sans dépendance React pour être testables.
 */

export type PortalSectionState<T> = {
  data: T | null
  /** Premier chargement sans aucune donnée (cache vide) → shimmer plein. */
  loading: boolean
  /** Revalidation alors que des données sont déjà affichées (stale-while-revalidate). */
  refreshing: boolean
  error: string
}

export type PortalSectionBootstrap<T> = {
  data: T | null
  hasInitialData: boolean
  isFresh: boolean
}

/** État initial synchrone depuis le cache (stale inclus) — évite tout flash skeleton. */
export function initSectionState<T>(bootstrap: PortalSectionBootstrap<T>): PortalSectionState<T> {
  return {
    data: bootstrap.data,
    loading: !bootstrap.hasInitialData,
    refreshing: false,
    error: '',
  }
}

/** Transition au démarrage d'un chargement (montage, revalidation ou refresh manuel). */
export function startSectionState<T>(
  prev: PortalSectionState<T>,
  input: { hasDisplayed: boolean; isManualRefresh: boolean; isFresh: boolean },
): PortalSectionState<T> {
  const showFullLoading = !input.hasDisplayed && !input.isManualRefresh
  const showRefreshing =
    input.isManualRefresh || (input.hasDisplayed && !input.isFresh)
  return {
    data: prev.data,
    loading: showFullLoading ? true : prev.loading,
    refreshing: showRefreshing ? true : prev.refreshing,
    error: '',
  }
}

/** Succès : données fraîches, plus de shimmer ni d'erreur. */
export function succeedSectionState<T>(data: T): PortalSectionState<T> {
  return { data, loading: false, refreshing: false, error: '' }
}

/**
 * Échec : on retombe sur le stale si disponible (pas d'erreur visible), sinon
 * on expose le message d'erreur. Les autres sections ne sont jamais impactées.
 */
export function failSectionState<T>(
  prev: PortalSectionState<T>,
  input: { staleData: T | null; errorMessage: string },
): PortalSectionState<T> {
  const fallback = input.staleData ?? prev.data
  return {
    data: fallback,
    loading: false,
    refreshing: false,
    error: fallback != null ? '' : input.errorMessage,
  }
}

/** Réinitialisation au changement de scope (réseau / wallet) pour une section scopée. */
export function resetSectionState<T>(bootstrap: PortalSectionBootstrap<T>): PortalSectionState<T> {
  return initSectionState(bootstrap)
}

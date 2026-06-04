/** Sections Markets chargées après le tableau crypto principal (O3). */
export const MARKETS_DEFERRED_SECTION_IDS = ['news', 'research', 'sidebar'] as const

export type MarketsDeferredSectionId = (typeof MARKETS_DEFERRED_SECTION_IDS)[number]

export function isMarketsDeferredSection(sectionId: string): sectionId is MarketsDeferredSectionId {
  return (MARKETS_DEFERRED_SECTION_IDS as readonly string[]).includes(sectionId)
}

/** Skeleton plein écran Markets uniquement sans payload affichable. */
export function shouldShowMarketsFullSkeleton(loading: boolean, data: unknown): boolean {
  return loading && data == null
}

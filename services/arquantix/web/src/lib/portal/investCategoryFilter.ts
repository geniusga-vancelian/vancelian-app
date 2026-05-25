import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'

export function normalizeInvestCategorySlug(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase().replace(/_/g, '-')
}

export function filterExclusiveOffersByCategory(
  offers: PortalExclusiveOffer[],
  categorySlug: string | null,
): PortalExclusiveOffer[] {
  if (!categorySlug) return offers
  const target = normalizeInvestCategorySlug(categorySlug)
  return offers.filter((offer) => normalizeInvestCategorySlug(offer.categorySlug) === target)
}

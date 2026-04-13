/**
 * Filtres listing admin Exclusive Offers (tests unitaires sans DB).
 */
import type { Prisma } from '@prisma/client'
import {
  PackagedCommercialStatus,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'

export type EngineLinkedFilter = 'all' | 'linked' | 'unlinked'

export type ExclusiveOffersSort = 'updated_desc' | 'featured_asc'

export interface ExclusiveOffersListQuery {
  q?: string | null
  commercialStatus?: PackagedCommercialStatus | null
  visibility?: PackagedVisibility | null
  engineLinked?: EngineLinkedFilter | null
  sort?: ExclusiveOffersSort | null
}

export function buildExclusiveOffersWhere(
  raw: ExclusiveOffersListQuery
): Prisma.PackagedProductWhereInput {
  const q = raw.q?.trim() ?? ''
  const engine = raw.engineLinked ?? 'all'

  const andParts: Prisma.PackagedProductWhereInput[] = [
    { productType: PackagedProductType.EXCLUSIVE_OFFER },
    { page: { template: 'vault_builder' } },
  ]

  if (q.length > 0) {
    andParts.push({
      OR: [
        { slug: { contains: q, mode: 'insensitive' } },
        { page: { title: { contains: q, mode: 'insensitive' } } },
      ],
    })
  }

  if (raw.commercialStatus) {
    andParts.push({ commercialStatus: raw.commercialStatus })
  }
  if (raw.visibility) {
    andParts.push({ visibility: raw.visibility })
  }

  if (engine === 'linked') {
    andParts.push({ lendingPoolProduct: { isNot: null } })
  } else if (engine === 'unlinked') {
    andParts.push({ lendingPoolProduct: null })
  }

  return { AND: andParts }
}

export function exclusiveOffersOrderBy(
  sort: ExclusiveOffersSort | null | undefined
): Prisma.PackagedProductOrderByWithRelationInput[] {
  if (sort === 'featured_asc') {
    return [{ featuredRank: 'asc' }, { updatedAt: 'desc' }]
  }
  return [{ updatedAt: 'desc' }]
}

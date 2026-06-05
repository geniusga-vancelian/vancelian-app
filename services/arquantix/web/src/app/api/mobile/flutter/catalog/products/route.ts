import { NextRequest, NextResponse } from 'next/server'

import { prisma } from '@/lib/prisma'
import {
  CATALOG_DEFAULT_LOCALE,
  commercialStatusToApi,
  engineTypeToApi,
  fetchLendingEngineSnapshot,
  parseCommercialStatusParam,
  parseProductTypeParam,
  parseVisibilityParam,
  productTypeToApi,
  resolveVaultPresentation,
  visibilityToApi,
} from '@/lib/catalog/packagedCatalogHelpers'
import { fetchVaultEngineSnapshotForCatalog } from '@/lib/catalog/vaultEngineCatalogSnapshot'
import { galleryExclusiveOfferCommercialStatuses } from '@/lib/cms/exclusiveOfferGallery'
import { resolveRequestPublicOrigin } from '@/lib/http/resolveRequestPublicOrigin'

/**
 * GET /api/mobile/flutter/catalog/products
 *
 * Catalogue unifié des produits packagés (Product Registry + contenu Vault Builder).
 *
 * Query: type, visibility, commercialStatus, locale, include_engine_data, limit
 *
 * `commercialStatus` omis : **production** → PUBLISHED uniquement ; **`next dev`** → PUBLISHED + DRAFT
 * (aligné grille web / EO encore en brouillon registre). Sinon passer `draft` ou `published` explicitement.
 */
export async function GET(request: NextRequest) {
  try {
    const publicOrigin = resolveRequestPublicOrigin({
      headers: request.headers,
      nextUrl: request.nextUrl,
    })
    const { searchParams } = new URL(request.url)
    const typeFilter = parseProductTypeParam(searchParams.get('type'))
    const visibilityFilter =
      parseVisibilityParam(searchParams.get('visibility')) ?? 'PUBLIC'
    const commercialExplicit = parseCommercialStatusParam(
      searchParams.get('commercialStatus'),
    )
    const commercialStatusWhere =
      commercialExplicit !== undefined
        ? commercialExplicit
        : galleryExclusiveOfferCommercialStatuses()
    const locale = (searchParams.get('locale') || CATALOG_DEFAULT_LOCALE).trim() || CATALOG_DEFAULT_LOCALE
    const includeEngine =
      searchParams.get('include_engine_data') === '1' ||
      searchParams.get('include_engine_data') === 'true'
    const limit = Math.min(
      Math.max(parseInt(searchParams.get('limit') || '50', 10), 1),
      100,
    )

    const rows = await prisma.packagedProduct.findMany({
      where: {
        ...(typeFilter ? { productType: typeFilter } : {}),
        visibility: visibilityFilter,
        commercialStatus: commercialStatusWhere,
      },
      orderBy: [{ featuredRank: 'asc' }, { updatedAt: 'desc' }],
      take: limit,
    })

    const items = await Promise.all(
      rows.map(async (row) => {
        const pres = await resolveVaultPresentation({
          prisma,
          pageId: row.pageId,
          locale,
          publicOrigin,
        })
        let snapshot: Record<string, unknown> | null | undefined
        if (includeEngine && row.engineReferenceId?.trim()) {
          if (row.engineType === 'LENDING') {
            snapshot =
              (await fetchLendingEngineSnapshot(row.engineReferenceId.trim())) ??
              undefined
          } else if (row.engineType === 'VAULT_ENGINE') {
            snapshot =
              (await fetchVaultEngineSnapshotForCatalog(row.engineReferenceId.trim())) ??
              undefined
          }
        }
        return {
          id: row.id,
          slug: row.slug,
          legacyProjectId: row.legacyProjectId,
          productType: productTypeToApi(row.productType),
          commercialStatus: commercialStatusToApi(row.commercialStatus),
          visibility: visibilityToApi(row.visibility),
          title: pres.title,
          subtitle: pres.subtitle,
          coverUrl: pres.coverUrl,
          featuredRank: row.featuredRank,
          category: row.categorySlug,
          tags: row.tags,
          engine: {
            type: engineTypeToApi(row.engineType),
            referenceId: row.engineReferenceId,
            snapshot: snapshot ?? null,
          },
        }
      }),
    )

    return NextResponse.json({ products: items })
  } catch (error) {
    console.error('[api/mobile/flutter/catalog/products]', error)
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: 'The request could not be completed.',
      },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}

import { NextRequest, NextResponse } from 'next/server'

import { ContentStatus } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import {
  CATALOG_DEFAULT_LOCALE,
  VAULT_SECTION_KEY,
  commercialStatusToApi,
  engineTypeToApi,
  fetchLendingEngineSnapshot,
  productTypeToApi,
  resolveVaultPresentation,
  visibilityToApi,
} from '@/lib/catalog/packagedCatalogHelpers'

/**
 * GET /api/mobile/flutter/catalog/products/{slug}
 *
 * Détail registre + contenu Vault Builder (section publiée) + enrichissement moteur optionnel.
 */
export async function GET(
  _request: NextRequest,
  {
    params,
  }: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = (resolved?.slug ?? '').trim()
    if (!slug) {
      return NextResponse.json({ error: 'Missing slug' }, { status: 400 })
    }

    const { searchParams } = new URL(_request.url)
    const locale =
      (searchParams.get('locale') || CATALOG_DEFAULT_LOCALE).trim() ||
      CATALOG_DEFAULT_LOCALE
    const includeEngine =
      searchParams.get('include_engine_data') === '1' ||
      searchParams.get('include_engine_data') === 'true'

    const packaged = await prisma.packagedProduct.findUnique({
      where: { slug },
      include: {
        page: {
          include: {
            sections: {
              where: { key: VAULT_SECTION_KEY },
              include: {
                contents: {
                  where: {
                    locale,
                    status: ContentStatus.PUBLISHED,
                  },
                  take: 1,
                },
              },
              take: 1,
            },
          },
        },
      },
    })

    if (!packaged) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const pres = await resolveVaultPresentation({
      prisma,
      pageId: packaged.pageId,
      locale,
    })

    const section = packaged.page.sections[0]
    const content = section?.contents[0]
    const vaultData = content?.data ?? null

    let snapshot: Record<string, unknown> | null = null
    if (
      includeEngine &&
      packaged.engineType === 'LENDING' &&
      packaged.engineReferenceId?.trim()
    ) {
      snapshot = await fetchLendingEngineSnapshot(packaged.engineReferenceId.trim())
    }

    return NextResponse.json({
      packagedProduct: {
        id: packaged.id,
        slug: packaged.slug,
        productType: productTypeToApi(packaged.productType),
        commercialStatus: commercialStatusToApi(packaged.commercialStatus),
        visibility: visibilityToApi(packaged.visibility),
        featuredRank: packaged.featuredRank,
        categorySlug: packaged.categorySlug,
        tags: packaged.tags,
        engineType: engineTypeToApi(packaged.engineType),
        engineReferenceId: packaged.engineReferenceId,
        legacyProjectId: packaged.legacyProjectId,
        publishedAt: packaged.publishedAt?.toISOString() ?? null,
        createdAt: packaged.createdAt.toISOString(),
        updatedAt: packaged.updatedAt.toISOString(),
      },
      page: {
        id: packaged.page.id,
        slug: packaged.page.slug,
        title: packaged.page.title,
        description: packaged.page.description,
        urlPath: packaged.page.urlPath,
        template: packaged.page.template,
      },
      vault: {
        sectionKey: VAULT_SECTION_KEY,
        locale: content?.locale ?? locale,
        data: vaultData,
      },
      presentation: {
        title: pres.title,
        subtitle: pres.subtitle,
        coverUrl: pres.coverUrl,
      },
      engine: {
        type: engineTypeToApi(packaged.engineType),
        referenceId: packaged.engineReferenceId,
        snapshot,
      },
    })
  } catch (error) {
    console.error('[api/mobile/flutter/catalog/products/[slug]]', error)
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: 'The request could not be completed.',
      },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}

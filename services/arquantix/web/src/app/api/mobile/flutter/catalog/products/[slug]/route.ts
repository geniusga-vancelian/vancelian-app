import { NextRequest, NextResponse } from 'next/server'

import { absolutizeArticlePreviewForMobile } from '@/lib/blog/absolutizeBlogApiForMobile'
import { getArticlesLinkedToVaultPageSlugs } from '@/lib/blog/articleService'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { prisma } from '@/lib/prisma'
import {
  enrichVaultModulesForMobileClient,
  type VaultModulePublic,
} from '@/lib/cms/exclusiveOfferVaultPage'
import { resolveVaultSectionContentForCatalog } from '@/lib/cms/resolveVaultSectionContent'
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
import { normalizeVaultBuilderSectionDataRoot } from '@/lib/vault/normalizeVaultModules'
import {
  appendNormalizedPortfolioModules,
  fetchPortfolioModulesRawForMerge,
} from '@/lib/catalog/mergePortfolioProductVaultModules'
import { ensureBlogALaUneFromDraftWhenRelatedNews } from '@/lib/catalog/ensureBlogALaUneVaultModuleForRelatedNews'
import { resolveRequestPublicOrigin } from '@/lib/http/resolveRequestPublicOrigin'

/**
 * GET /api/mobile/flutter/catalog/products/{slug}
 *
 * Détail registre + contenu Vault Builder (résolution alignée web + enrichissement médias mobile) + moteur optionnel.
 */
export async function GET(
  _request: NextRequest,
  {
    params,
  }: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const publicOrigin = resolveRequestPublicOrigin({
      headers: _request.headers,
      nextUrl: _request.nextUrl,
    })
    const resolved = await Promise.resolve(params)
    const slug = (resolved?.slug ?? '').trim()
    if (!slug) {
      return NextResponse.json({ error: 'Missing slug' }, { status: 400 })
    }

    const { searchParams } = new URL(_request.url)
    const requestedLocale =
      (searchParams.get('locale') || CATALOG_DEFAULT_LOCALE).trim() || CATALOG_DEFAULT_LOCALE
    const includeEngine =
      searchParams.get('include_engine_data') === '1' ||
      searchParams.get('include_engine_data') === 'true'

    // Fallback locale : on charge tous les SectionContent pour permettre
    // à `resolveVaultSectionContentForCatalog` de retomber sur EN/n’importe
    // quelle locale (parité avec articles : sinon Flutter reçoit
    // `vault.data = null` quand l’EO n’est éditée qu’en EN).
    const packaged = await prisma.packagedProduct.findUnique({
      where: { slug },
      include: {
        lendingPoolProduct: {
          select: { projectId: true },
        },
        page: {
          include: {
            sections: {
              where: { key: VAULT_SECTION_KEY },
              include: { contents: true },
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
      locale: requestedLocale,
      publicOrigin,
    })

    const section = packaged.page.sections[0]
    const sectionContents = section?.contents ?? []
    const preferredVaultContent = resolveVaultSectionContentForCatalog(sectionContents, {
      requestedLocale,
      defaultLocale: CATALOG_DEFAULT_LOCALE,
    })
    const rawVaultData = preferredVaultContent?.data ?? null
    const portfolioModulesRaw = await fetchPortfolioModulesRawForMerge(prisma, {
      slug,
      legacyProjectId: packaged.legacyProjectId,
      lendingPoolProduct: packaged.lendingPoolProduct,
    })

    let vaultData: Record<string, unknown> | null = null
    const vaultRootPlain =
      rawVaultData != null && typeof rawVaultData === 'object' && !Array.isArray(rawVaultData)
        ? (rawVaultData as Record<string, unknown>)
        : portfolioModulesRaw.length > 0
          ? ({ modules: [] } as Record<string, unknown>)
          : null

    if (vaultRootPlain != null) {
      const { data: normalized, warnings: normalizeWarnings } = normalizeVaultBuilderSectionDataRoot(
        vaultRootPlain,
        slug,
      )
      if (normalized != null) {
        let mods = (normalized.modules ?? []) as VaultModulePublic[]
        let mergePortfolioWarnings: string[] = []
        if (portfolioModulesRaw.length > 0) {
          const appended = appendNormalizedPortfolioModules(mods, portfolioModulesRaw, slug)
          mods = appended.merged
          mergePortfolioWarnings = appended.warnings
        }
        const allNormalizeWarnings = [...normalizeWarnings, ...mergePortfolioWarnings]
        if (process.env.NODE_ENV === 'development' && allNormalizeWarnings.length > 0) {
          console.warn(`[catalog/products/[slug]] normalize vault slug=${slug}`, allNormalizeWarnings)
        }
        const enriched =
          Array.isArray(mods) && mods.length > 0
              ? await enrichVaultModulesForMobileClient(prisma, mods, publicOrigin)
              : mods
        vaultData = { ...normalized, modules: enriched }
      } else {
        if (process.env.NODE_ENV === 'development' && normalizeWarnings.length > 0) {
          console.warn(`[catalog/products/[slug]] normalize vault slug=${slug}`, normalizeWarnings)
        }
        vaultData = vaultRootPlain
      }
    }

    let snapshot: Record<string, unknown> | null = null
    if (
      includeEngine &&
      packaged.engineType === 'LENDING' &&
      packaged.engineReferenceId?.trim()
    ) {
      snapshot = await fetchLendingEngineSnapshot(packaged.engineReferenceId.trim())
    }

    const vaultPageSlugSet = new Set<string>()
    if (typeof packaged.page?.slug === 'string' && packaged.page.slug.trim()) {
      vaultPageSlugSet.add(packaged.page.slug.trim().toLowerCase())
    }
    if (typeof packaged.slug === 'string' && packaged.slug.trim()) {
      vaultPageSlugSet.add(packaged.slug.trim().toLowerCase())
    }

    const relatedArticlesRaw =
      vaultPageSlugSet.size === 0
        ? []
        : await getArticlesLinkedToVaultPageSlugs(
            {
              vaultPageSlugs: Array.from(vaultPageSlugSet),
              locale: requestedLocale,
              limit: 24,
            },
            calculateReadingTime,
          )

    if (vaultData != null && relatedArticlesRaw.length > 0) {
      vaultData = await ensureBlogALaUneFromDraftWhenRelatedNews(prisma, {
        sectionContents,
        vaultData,
        relatedArticleCount: relatedArticlesRaw.length,
        requestedLocale,
        defaultLocale: CATALOG_DEFAULT_LOCALE,
        publicOrigin,
        contextSlug: slug,
      })
    }

    const relatedArticles = relatedArticlesRaw.map((a) =>
      absolutizeArticlePreviewForMobile(a, publicOrigin),
    )

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
        locale: preferredVaultContent?.locale ?? requestedLocale,
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
      relatedArticles,
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

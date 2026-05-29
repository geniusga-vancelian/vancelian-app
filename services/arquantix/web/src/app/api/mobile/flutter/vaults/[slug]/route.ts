import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { absolutizeArticlePreviewForMobile } from '@/lib/blog/absolutizeBlogApiForMobile'
import { getArticlesLinkedToVaultPageSlugs } from '@/lib/blog/articleService'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { getLocaleOrDefault } from '@/config/locales'
import { CATALOG_DEFAULT_LOCALE } from '@/lib/catalog/packagedCatalogHelpers'
import { prisma } from '@/lib/prisma'
import { resolvePageSeoFields } from '@/lib/cms/resolvePageI18nMetadata'
import {
  resolveVaultSectionContent,
  resolveVaultSectionContentForCatalog,
} from '@/lib/cms/resolveVaultSectionContent'
import {
  enrichVaultModulesForMobileClient,
  type VaultModulePublic,
} from '@/lib/cms/exclusiveOfferVaultPage'
import { normalizeVaultBuilderSectionDataRoot } from '@/lib/vault/normalizeVaultModules'
import { ensureBlogALaUneFromDraftWhenRelatedNews } from '@/lib/catalog/ensureBlogALaUneVaultModuleForRelatedNews'
import { resolveRequestPublicOrigin } from '@/lib/http/resolveRequestPublicOrigin'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

/**
 * GET /api/mobile/flutter/vaults/[slug]?locale=fr&status=draft|published
 * Endpoint public pour afficher un vault dans l'app Flutter.
 * Résolution du SectionContent : en **published**, alignée sur le catalogue mobile
 * (`resolveVaultSectionContentForCatalog` — repli brouillon si pub sans modules).
 * En **draft**, résolution stricte du brouillon.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const resolvedParams = await Promise.resolve(params)
    const requestedSlug = (resolvedParams.slug ?? '').trim()
    if (!requestedSlug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const reqUrl = new URL(request.url)
    const { searchParams } = reqUrl
    const publicOrigin = resolveRequestPublicOrigin({ headers: request.headers, nextUrl: reqUrl })
    const locale = getLocaleOrDefault(searchParams.get('locale') ?? undefined)
    const requestedStatus = (searchParams.get('status') || 'published').toLowerCase()
    const mode =
      requestedStatus === 'published' ? ContentStatus.PUBLISHED : ContentStatus.DRAFT

    const page = await prisma.page.findFirst({
      where: {
        slug: requestedSlug,
        template: VAULT_TEMPLATE_DB,
      },
      include: {
        sections: {
          where: { key: VAULT_SECTION_KEY },
          include: {
            contents: true,
          },
          take: 1,
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Vault not found' }, { status: 404 })
    }

    const section = page.sections[0]
    const contents = section?.contents ?? []
    const content =
      mode === ContentStatus.PUBLISHED
        ? resolveVaultSectionContentForCatalog(contents, {
            requestedLocale: locale,
            defaultLocale: CATALOG_DEFAULT_LOCALE,
          })
        : resolveVaultSectionContent(contents, {
            requestedLocale: locale,
            defaultLocale: CATALOG_DEFAULT_LOCALE,
            mode: ContentStatus.DRAFT,
          })

    if (!content) {
      return NextResponse.json(
        { error: `No ${requestedStatus} content for locale "${locale}"` },
        { status: 404 },
      )
    }

    const seo = await resolvePageSeoFields(page.id, locale)

    const { data: normalizedVault, warnings: normalizeWarnings } =
      normalizeVaultBuilderSectionDataRoot(content.data, requestedSlug)
    if (process.env.NODE_ENV === 'development' && normalizeWarnings.length > 0) {
      console.warn(`[normalizeVaultModules] mobile vault slug=${requestedSlug}`, normalizeWarnings)
    }

    // Enrichissement médias (presigned + URLs absolues) — parité catalogue.
    let enrichedVault: unknown = normalizedVault ?? content.data
    if (
      normalizedVault != null &&
      typeof normalizedVault === 'object' &&
      Array.isArray((normalizedVault as Record<string, unknown>).modules)
    ) {
      const root = normalizedVault as Record<string, unknown>
      const mods = root.modules as VaultModulePublic[]
      const enriched =
        mods.length > 0
          ? await enrichVaultModulesForMobileClient(prisma, mods, publicOrigin)
          : mods
      enrichedVault = { ...root, modules: enriched }
    }

    const slugNorm = requestedSlug.trim().toLowerCase()
    const relatedArticlesRaw =
      slugNorm.length === 0
        ? []
        : await getArticlesLinkedToVaultPageSlugs(
            {
              vaultPageSlugs: [slugNorm],
              locale,
              limit: 24,
            },
            calculateReadingTime,
          )

    if (
      mode === ContentStatus.PUBLISHED &&
      relatedArticlesRaw.length > 0 &&
      enrichedVault != null &&
      typeof enrichedVault === 'object'
    ) {
      const enrichedRecord = enrichedVault as Record<string, unknown>
      const merged = await ensureBlogALaUneFromDraftWhenRelatedNews(prisma, {
        sectionContents: contents,
        vaultData: enrichedRecord,
        relatedArticleCount: relatedArticlesRaw.length,
        requestedLocale: locale,
        defaultLocale: CATALOG_DEFAULT_LOCALE,
        publicOrigin,
        contextSlug: requestedSlug,
      })
      enrichedVault = merged ?? enrichedVault
    }

    const relatedArticles = relatedArticlesRaw.map((a) =>
      absolutizeArticlePreviewForMobile(a, publicOrigin),
    )

    return NextResponse.json(
      {
        page: {
          id: page.id,
          slug: page.slug,
          title: seo.title?.trim() || page.slug,
          description: seo.description?.trim() ?? null,
          urlPath: page.urlPath,
          template: page.template,
        },
        vault: enrichedVault,
        meta: {
          locale,
          status: requestedStatus,
          contentLocale: content.locale,
        },
        relatedArticles,
      },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
          Pragma: 'no-cache',
          Expires: '0',
        },
      },
    )
  } catch (error) {
    console.error('[api/mobile/flutter/vaults/[slug]]', error)
    return NextResponse.json(
      { error: 'Internal server error', message: 'The request could not be completed.' },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}

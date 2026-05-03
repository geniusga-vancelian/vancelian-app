import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { defaultLocale, getLocaleOrDefault } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import { resolvePageSeoFields } from '@/lib/cms/resolvePageI18nMetadata'
import { resolveVaultSectionContent } from '@/lib/cms/resolveVaultSectionContent'
import { normalizeVaultBuilderSectionDataRoot } from '@/lib/vault/normalizeVaultModules'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

/**
 * GET /api/mobile/flutter/vaults/[slug]?locale=fr&status=draft|published
 * Endpoint public pour afficher un vault dans l'app Flutter.
 * Résolution du SectionContent : même logique que le rendu web (`resolveVaultSectionContent`).
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

    const { searchParams } = new URL(request.url)
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
    const content = resolveVaultSectionContent(contents, {
      requestedLocale: locale,
      defaultLocale,
      mode,
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
        vault: normalizedVault ?? content.data,
        meta: {
          locale,
          status: requestedStatus,
        },
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

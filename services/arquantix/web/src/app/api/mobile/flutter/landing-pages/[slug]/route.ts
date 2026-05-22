import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import {
  resolveVaultSectionContent,
  type ResolveVaultSectionContentMode,
} from '@/lib/cms/resolveVaultSectionContent'

const LANDING_TEMPLATE_DB = 'landing_builder'
const LANDING_SECTION_KEY = 'landing_builder_v1'

function parseStatus(raw: string | null): ResolveVaultSectionContentMode {
  const v = (raw ?? '').toLowerCase()
  if (v === 'published') return ContentStatus.PUBLISHED
  if (v === 'draft') return ContentStatus.DRAFT
  /// Comportement par défaut **mobile public** : on ne tolère pas le brouillon.
  return ContentStatus.PUBLISHED
}

/**
 * GET /api/mobile/flutter/landing-pages/[slug]?locale=fr&status=draft|published
 *
 * Endpoint public pour la prévisualisation runtime d'une landing page Flutter.
 *
 * - Locale : fallback `requested → defaultLocale (AppSettings) → toute locale disponible`
 *   (mêmes paliers que `resolveVaultSectionContent`).
 * - Status : `published` par défaut. `draft` autorisé pour preview admin signée
 *   (le secret est implicite : on ne révèle pas que la page existe en brouillon
 *   tant qu'aucune publication n'est faite).
 * - `meta.contentLocale` reflète la locale **réellement** servie après fallback.
 */
export async function GET(
  request: Request,
  { params }: { params: { slug: string } }
) {
  try {
    const requestedSlug = (params.slug ?? '').trim()
    if (!requestedSlug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const { searchParams } = new URL(request.url)
    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (searchParams.get('locale') || '').trim() || i18n.defaultLocale
    const mode = parseStatus(searchParams.get('status'))

    const page = await prisma.page.findFirst({
      where: {
        slug: requestedSlug,
        template: LANDING_TEMPLATE_DB,
      },
      include: {
        sections: {
          where: { key: LANDING_SECTION_KEY },
          include: {
            contents: true,
          },
          take: 1,
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Landing page not found' }, { status: 404 })
    }

    const allContents = page.sections[0]?.contents ?? []
    const picked = resolveVaultSectionContent(allContents, {
      requestedLocale,
      defaultLocale: i18n.defaultLocale,
      mode,
    })

    if (!picked) {
      return NextResponse.json(
        {
          error: `No ${mode === ContentStatus.PUBLISHED ? 'published' : 'draft'} content available`,
          meta: {
            requestedLocale,
            defaultLocale: i18n.defaultLocale,
          },
        },
        { status: 404 }
      )
    }

    return NextResponse.json(
      {
        page: {
          id: page.id,
          slug: page.slug,
          title: page.title,
          description: page.description,
          urlPath: page.urlPath,
          template: page.template,
        },
        landing: picked.data,
        meta: {
          requestedLocale,
          contentLocale: picked.locale,
          contentStatus: picked.status,
          defaultLocale: i18n.defaultLocale,
        },
      },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
          Pragma: 'no-cache',
          Expires: '0',
        },
      }
    )
  } catch (error) {
    console.error('[api/mobile/flutter/landing-pages/[slug]]', error)
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: 'The request could not be completed.',
      },
      {
        status: 500,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      }
    )
  }
}

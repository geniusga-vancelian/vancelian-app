import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import { resolveVaultSectionContent } from '@/lib/cms/resolveVaultSectionContent'

const LANDING_TEMPLATE_DB = 'landing_builder'
const LANDING_SECTION_KEY = 'landing_builder_v1'

const navbarActionSchema = z.object({
  icon: z.enum(['none', 'favorite', 'share', 'notifications']).default('none'),
  redirectType: z.enum(['none', 'back', 'close', 'internal', 'external']).default('none'),
  target: z.string().optional().default(''),
})

const landingConfigSchema = z.object({
  templateKey: z
    .enum([
      'PageSimpleNavBarTopTitlePageContent',
      'ModaleFullHeightPage',
      'DashboardScrollTemplate',
    ])
    .default('PageSimpleNavBarTopTitlePageContent'),
  navbar: z.object({
    leftIconType: z.enum(['none', 'back', 'close']).default('back'),
    leftRedirectType: z.enum(['back', 'close', 'internal', 'external']).default('back'),
    leftTarget: z.string().optional().default(''),
    rightAction: navbarActionSchema.default({
      icon: 'none',
      redirectType: 'none',
      target: '',
    }),
  }),
  pageTitle: z.object({
    enabled: z.boolean().default(true),
    text: z.string().default(''),
  }),
  fixedBottomCta: z.object({
    enabled: z.boolean().default(false),
    label: z.string().default(''),
    redirectType: z.enum(['none', 'back', 'close', 'internal', 'external']).default('none'),
    target: z.string().optional().default(''),
  }),
  modules: z
    .array(
      z.object({
        id: z.string(),
        type: z.string(),
        enabled: z.boolean().default(true),
        // Content is module-specific; keep it fully flexible.
        content: z.any().default({}),
      })
    )
    .default([]),
})

const updateLandingPageSchema = z.object({
  title: z.string().max(200).optional(),
  description: z.string().max(1000).nullable().optional(),
  config: landingConfigSchema,
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

/** Config par défaut pour l’éditeur (évite tout appel à Zod.parse qui pourrait lever). */
function getDefaultLandingConfig(): z.infer<typeof landingConfigSchema> {
  return {
    templateKey: 'PageSimpleNavBarTopTitlePageContent',
    navbar: {
      leftIconType: 'back',
      leftRedirectType: 'back',
      leftTarget: '',
      rightAction: { icon: 'none', redirectType: 'none', target: '' },
    },
    pageTitle: { enabled: true, text: '' },
    fixedBottomCta: { enabled: false, label: '', redirectType: 'none', target: '' },
    modules: [],
  }
}

/** Extrait et normalise les modules depuis les données brutes (préservation si la validation Zod échoue). */
function normalizeModulesFromRaw(raw: unknown): z.infer<typeof landingConfigSchema>['modules'] {
  if (raw == null || typeof raw !== 'object' || !Array.isArray((raw as Record<string, unknown>).modules))
    return []
  const arr = (raw as Record<string, unknown>).modules as unknown[]
  return arr.map((item, i) => {
    if (item == null || typeof item !== 'object') {
      return { id: `module-${i}`, type: 'Unknown', enabled: true, content: {} }
    }
    const o = item as Record<string, unknown>
    return {
      id: typeof o.id === 'string' ? o.id : `module-${i}`,
      type: typeof o.type === 'string' ? o.type : 'Unknown',
      enabled: typeof o.enabled === 'boolean' ? o.enabled : true,
      content: o.content != null && typeof o.content === 'object' ? (o.content as Record<string, unknown>) : {},
    }
  })
}

export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const slug = normalizeSlug(params?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    let session
    try {
      session = await getSessionFromCookie()
    } catch (authErr) {
      console.error('[api/admin/landing-pages/GET] getSessionFromCookie', authErr)
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale

    const page = await prisma.page.findFirst({
      where: {
        slug,
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
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    /// Résolution avec fallback locale (`requestedLocale → defaultLocale → any`)
    /// et brouillon-prioritaire pour l'éditeur (cohérent avec `vault_builder` admin).
    const allContents = page.sections[0]?.contents ?? []
    const picked = resolveVaultSectionContent(allContents, {
      requestedLocale,
      defaultLocale: i18n.defaultLocale,
      mode: 'either_draft_first',
    })

    const isMissingForRequestedLocale = !allContents.some(
      (c) => c.locale === requestedLocale,
    )

    const rawData = picked?.data ?? null
    let config: z.infer<typeof landingConfigSchema>
    try {
      const data =
        rawData == null
          ? {}
          : typeof rawData === 'string'
            ? (() => {
                try {
                  return JSON.parse(rawData) as unknown
                } catch {
                  return {}
                }
              })()
            : typeof rawData === 'object' && rawData !== null
              ? { ...(rawData as Record<string, unknown>) }
              : {}
      const validated = landingConfigSchema.safeParse(data)
      if (validated.success) {
        config = validated.data
      } else {
        config = getDefaultLandingConfig()
        config.modules = normalizeModulesFromRaw(data)
      }
    } catch {
      config = getDefaultLandingConfig()
      config.modules = normalizeModulesFromRaw(rawData)
    }

    const updatedAt = page.updatedAt
    const pagePayload = {
      id: page.id,
      slug: page.slug,
      title: page.title ?? null,
      description: page.description ?? null,
      urlPath: page.urlPath,
      updatedAt: updatedAt instanceof Date ? updatedAt.toISOString() : String(updatedAt),
    }

    const localeCoverage = Array.from(new Set(allContents.map((c) => c.locale)))

    return NextResponse.json({
      page: pagePayload,
      config,
      meta: {
        defaultLocale: i18n.defaultLocale,
        supportedLocales: i18n.supportedLocales,
        requestedLocale,
        contentLocale: picked?.locale ?? null,
        contentStatus: picked?.status ?? null,
        localeCoverage,
        /// `true` si la locale demandée n'a aucun contenu (DRAFT ou PUBLISHED) :
        /// l'éditeur peut alors proposer "Copier depuis la locale source".
        isFallback: isMissingForRequestedLocale,
      },
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/landing-pages/GET]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 }
    )
  }
}

/// Statuts cibles pour le PUT.
/// - `draft` : seul le brouillon est mis à jour (par défaut, sécurisé).
/// - `published` : on aligne DRAFT et PUBLISHED (équivalent "Publier").
type WriteScope = 'draft' | 'published'

function parseWriteScope(value: string | null): WriteScope {
  return value?.toLowerCase() === 'published' ? 'published' : 'draft'
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const slug = normalizeSlug(params?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale
    const writeScope = parseWriteScope(request.nextUrl.searchParams.get('status'))

    /// Garde-fou : on n'écrit que sur une locale activée côté admin (sinon le
    /// résolveur public ne pourrait jamais la retrouver et l'éditeur stockerait
    /// du contenu orphelin).
    if (
      i18n.multilingualEnabled &&
      !i18n.supportedLocales.includes(requestedLocale as (typeof i18n.supportedLocales)[number])
    ) {
      return NextResponse.json(
        { error: `Locale "${requestedLocale}" not enabled in site settings` },
        { status: 400 }
      )
    }

    const body = await request.json()
    const parsed = updateLandingPageSchema.parse(body)

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: LANDING_TEMPLATE_DB,
      },
      include: {
        sections: {
          where: { key: LANDING_SECTION_KEY },
          take: 1,
        },
      },
    })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const section = page.sections[0]
    if (!section) {
      return NextResponse.json(
        { error: 'Landing section not found for this page' },
        { status: 400 }
      )
    }

    await prisma.page.update({
      where: { id: page.id },
      data: {
        title: parsed.title ?? page.title,
        description:
          parsed.description !== undefined ? parsed.description : page.description,
      },
    })

    /// `published` aligne DRAFT et PUBLISHED en une seule opération ;
    /// `draft` ne touche **que** le brouillon (défaut, comportement non-publication).
    const statuses: ContentStatus[] =
      writeScope === 'published'
        ? [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
        : [ContentStatus.DRAFT]
    for (const status of statuses) {
      await prisma.sectionContent.upsert({
        where: {
          sectionId_locale_status: {
            sectionId: section.id,
            locale: requestedLocale,
            status,
          },
        },
        update: {
          data: parsed.config,
          updatedByUserId: session.userId,
        },
        create: {
          sectionId: section.id,
          locale: requestedLocale,
          status,
          data: parsed.config,
          updatedByUserId: session.userId,
        },
      })
    }

    return NextResponse.json({
      success: true,
      meta: {
        contentLocale: requestedLocale,
        writeScope,
      },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating landing page:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const slug = normalizeSlug(params?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: LANDING_TEMPLATE_DB,
      },
      select: { id: true, slug: true },
    })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    await prisma.page.delete({ where: { id: page.id } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting landing page:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const LANDING_TEMPLATE_DB = 'landing_builder'
const LANDING_SECTION_KEY = 'landing_builder_v1'
const LANDING_DEFAULT_LOCALE = 'fr'

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
  _request: NextRequest,
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

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: LANDING_TEMPLATE_DB,
      },
      include: {
        sections: {
          where: { key: LANDING_SECTION_KEY },
          include: {
            contents: {
              where: {
                locale: LANDING_DEFAULT_LOCALE,
                status: ContentStatus.DRAFT,
              },
              take: 1,
            },
          },
          take: 1,
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Même logique de lecture que l'API mobile : accès direct au contenu sans validation stricte
    const content = page.sections[0]?.contents[0]
    const rawData = content?.data

    let config: z.infer<typeof landingConfigSchema>
    try {
      const draftData =
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
      const validated = landingConfigSchema.safeParse(draftData)
      if (validated.success) {
        config = validated.data
      } else {
        config = getDefaultLandingConfig()
        config.modules = normalizeModulesFromRaw(draftData)
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

    return NextResponse.json({ page: pagePayload, config })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/landing-pages/GET]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 }
    )
  }
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

    // Keep DRAFT and PUBLISHED aligned for this dedicated builder.
    const statuses: ContentStatus[] = [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
    for (const status of statuses) {
      await prisma.sectionContent.upsert({
        where: {
          sectionId_locale_status: {
            sectionId: section.id,
            locale: LANDING_DEFAULT_LOCALE,
            status,
          },
        },
        update: {
          data: parsed.config,
          updatedByUserId: session.userId,
        },
        create: {
          sectionId: section.id,
          locale: LANDING_DEFAULT_LOCALE,
          status,
          data: parsed.config,
          updatedByUserId: session.userId,
        },
      })
    }

    return NextResponse.json({ success: true })
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

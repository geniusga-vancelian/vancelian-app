import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'
const VAULT_DEFAULT_LOCALE = 'fr'

const navbarActionSchema = z.object({
  icon: z.enum(['none', 'favorite', 'share', 'notifications']).default('none'),
  redirectType: z.enum(['none', 'back', 'close', 'internal', 'external']).default('none'),
  target: z.string().optional().default(''),
})

const vaultConfigSchema = z.object({
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
        content: z.any().default({}),
      })
    )
    .default([]),
  investmentTypeSlug: z.string().optional(),
  sortOrder: z.number().optional(),
  headerMediaId: z.string().optional().nullable(),
})

const updateVaultSchema = z.object({
  title: z.string().max(200).optional(),
  description: z.string().max(1000).nullable().optional(),
  config: vaultConfigSchema,
})

function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

function getDefaultVaultConfig(): z.infer<typeof vaultConfigSchema> {
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
    investmentTypeSlug: undefined,
    sortOrder: 999,
    headerMediaId: undefined,
  }
}

function normalizeModulesFromRaw(raw: unknown): z.infer<typeof vaultConfigSchema>['modules'] {
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
  { params }: { params: Promise<{ slug: string }> | { slug: string } }
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    let session
    try {
      session = await getSessionFromCookie()
    } catch (authErr) {
      console.error('[api/admin/vaults/GET] getSessionFromCookie', authErr)
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: VAULT_TEMPLATE_DB,
      },
      include: {
        packagedProduct: true,
        sections: {
          where: { key: VAULT_SECTION_KEY },
          include: {
            contents: {
              where: {
                locale: VAULT_DEFAULT_LOCALE,
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
      return NextResponse.json({ error: 'Vault not found' }, { status: 404 })
    }

    const content = page.sections[0]?.contents[0]
    const rawData = content?.data

    let config: z.infer<typeof vaultConfigSchema>
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
      const validated = vaultConfigSchema.safeParse(draftData)
      if (validated.success) {
        config = validated.data
      } else {
        config = getDefaultVaultConfig()
        config.modules = normalizeModulesFromRaw(draftData)
        const raw = draftData as Record<string, unknown>
        if (typeof raw.investmentTypeSlug === 'string') config.investmentTypeSlug = raw.investmentTypeSlug
        if (typeof raw.sortOrder === 'number') config.sortOrder = raw.sortOrder
        if (typeof raw.headerMediaId === 'string' || raw.headerMediaId === null) config.headerMediaId = raw.headerMediaId
      }
    } catch {
      config = getDefaultVaultConfig()
      config.modules = normalizeModulesFromRaw(rawData)
      const raw = rawData as Record<string, unknown> | null
      if (raw && typeof raw.investmentTypeSlug === 'string') config.investmentTypeSlug = raw.investmentTypeSlug
      if (raw && typeof raw.sortOrder === 'number') config.sortOrder = raw.sortOrder
      if (raw && (typeof raw.headerMediaId === 'string' || raw.headerMediaId === null)) config.headerMediaId = raw.headerMediaId
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

    const pp = page.packagedProduct
    const lendingRow =
      pp != null
        ? await prisma.lendingPoolProducts.findUnique({
            where: { packagedProductId: pp.id },
            select: { id: true },
          })
        : null
    const lendingEngineLinked = lendingRow != null

    const packagedProduct = pp
      ? {
          id: pp.id,
          slug: pp.slug,
          pageId: pp.pageId,
          productType: pp.productType,
          commercialStatus: pp.commercialStatus,
          visibility: pp.visibility,
          featuredRank: pp.featuredRank,
          categorySlug: pp.categorySlug,
          tags: (() => {
            const t = pp.tags
            if (t == null) return [] as string[]
            if (Array.isArray(t)) {
              return t.filter((x): x is string => typeof x === 'string' && x.length > 0)
            }
            return [] as string[]
          })(),
          engineType: pp.engineType,
          engineReferenceId: pp.engineReferenceId,
          lendingEngineLinked,
          updatedAt: pp.updatedAt.toISOString(),
          publishedAt: pp.publishedAt ? pp.publishedAt.toISOString() : null,
        }
      : null

    return NextResponse.json({ page: pagePayload, config, packagedProduct })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/vaults/GET]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> | { slug: string } }
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = updateVaultSchema.parse(body)

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: VAULT_TEMPLATE_DB,
      },
      include: {
        sections: {
          where: { key: VAULT_SECTION_KEY },
          take: 1,
        },
      },
    })
    if (!page) {
      return NextResponse.json({ error: 'Vault not found' }, { status: 404 })
    }

    const section = page.sections[0]
    if (!section) {
      return NextResponse.json(
        { error: 'Vault section not found for this page' },
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

    const statuses: ContentStatus[] = [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
    for (const status of statuses) {
      await prisma.sectionContent.upsert({
        where: {
          sectionId_locale_status: {
            sectionId: section.id,
            locale: VAULT_DEFAULT_LOCALE,
            status,
          },
        },
        update: {
          data: parsed.config,
          updatedByUserId: session.userId,
        },
        create: {
          sectionId: section.id,
          locale: VAULT_DEFAULT_LOCALE,
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
    console.error('Error updating vault:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ slug: string }> | { slug: string } }
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = normalizeSlug(resolved?.slug)
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
        template: VAULT_TEMPLATE_DB,
      },
      select: { id: true, slug: true },
    })
    if (!page) {
      return NextResponse.json({ error: 'Vault not found' }, { status: 404 })
    }

    const pp = await prisma.packagedProduct.findUnique({
      where: { pageId: page.id },
      include: { lendingPoolProduct: { select: { id: true } } },
    })
    if (pp?.lendingPoolProduct) {
      return NextResponse.json(
        {
          error:
            'Ce vault est lié à un produit lending. Détachez la liaison avant suppression.',
          code: 'LENDING_LINKED',
        },
        { status: 409 }
      )
    }
    if (pp) {
      await prisma.packagedProduct.delete({ where: { id: pp.id } })
    }

    await prisma.page.delete({ where: { id: page.id } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting vault:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

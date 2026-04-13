import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { calculateUrlPath, isValidSlug } from '@/lib/utils/slugify'

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

const createVaultSchema = z.object({
  slug: z
    .string()
    .min(1)
    .max(60)
    .refine(isValidSlug, {
      message: 'Slug invalide',
    }),
  title: z.string().max(200).optional(),
  description: z.string().max(1000).optional(),
  investmentTypeSlug: z.string().max(100).optional(),
  config: vaultConfigSchema.optional(),
})

function buildDefaultConfig() {
  return vaultConfigSchema.parse({
    templateKey: 'PageSimpleNavBarTopTitlePageContent',
    navbar: {
      leftIconType: 'back',
      leftRedirectType: 'back',
      leftTarget: '',
      rightAction: {
        icon: 'favorite',
        redirectType: 'none',
        target: '',
      },
    },
    pageTitle: {
      enabled: true,
      text: 'Titre de page',
    },
    fixedBottomCta: {
      enabled: false,
      label: 'Parrainer une entreprise',
      redirectType: 'none',
      target: '',
    },
    modules: [],
    investmentTypeSlug: undefined,
    sortOrder: 0,
  })
}

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const pages = await prisma.page.findMany({
      where: { template: VAULT_TEMPLATE_DB },
      include: {
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
        },
      },
      orderBy: { updatedAt: 'desc' },
    })

    const out = pages.map((page) => {
      const draftData = page.sections[0]?.contents[0]?.data ?? null
      const parsed = draftData ? vaultConfigSchema.safeParse(draftData) : null
      const config = parsed?.success ? parsed.data : null
      const raw = draftData as Record<string, unknown> | null
      const investmentTypeSlug = config?.investmentTypeSlug ?? raw?.investmentTypeSlug ?? null
      const sortOrder = config?.sortOrder ?? (typeof raw?.sortOrder === 'number' ? raw.sortOrder : 999)
      return {
        id: page.id,
        slug: page.slug,
        urlPath: page.urlPath,
        title: page.title,
        description: page.description,
        updatedAt: page.updatedAt,
        investmentTypeSlug,
        sortOrder,
        configSummary: {
          templateKey: config?.templateKey ?? null,
          modulesCount: Array.isArray(config?.modules) ? config.modules.length : 0,
        },
      }
    })

    return NextResponse.json({ vaults: out })
  } catch (error) {
    console.error('Error listing vaults:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = createVaultSchema.parse(body)
    const slug = parsed.slug
    const urlPath = calculateUrlPath(slug)
    const investmentTypeSlug = parsed.investmentTypeSlug?.trim() || undefined
    const config = parsed.config ?? buildDefaultConfig()
    const configWithMeta = {
      ...config,
      investmentTypeSlug: investmentTypeSlug ?? undefined,
      sortOrder: investmentTypeSlug ? 0 : 999,
    }

    const existing = await prisma.page.findFirst({
      where: {
        OR: [{ slug }, { urlPath }],
      },
      select: { id: true },
    })
    if (existing) {
      return NextResponse.json(
        { error: 'Un vault ou une page existe déjà avec ce slug ou cette URL.' },
        { status: 409 }
      )
    }

    const created = await prisma.page.create({
      data: {
        slug,
        urlPath,
        title: parsed.title ?? slug,
        description: parsed.description ?? null,
        template: VAULT_TEMPLATE_DB,
        sections: {
          create: {
            key: VAULT_SECTION_KEY,
            order: 0,
            schemaVersion: 'v1',
            contents: {
              create: [
                {
                  locale: VAULT_DEFAULT_LOCALE,
                  status: ContentStatus.DRAFT,
                  data: configWithMeta,
                  updatedByUserId: session.userId,
                },
                {
                  locale: VAULT_DEFAULT_LOCALE,
                  status: ContentStatus.PUBLISHED,
                  data: configWithMeta,
                  updatedByUserId: session.userId,
                },
              ],
            },
          },
        },
      },
    })

    return NextResponse.json({ vault: created }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating vault:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus, PackagedProductType } from '@prisma/client'
import { z } from 'zod'

import { defaultLocale, type Locale } from '@/config/locales'
import { isValidLocale } from '@/config/locales'
import { EXCLUSIVE_OFFER_VAULT_INVESTMENT_TYPE_SLUG } from '@/lib/admin/exclusiveOfferVaultCreate'
import { getSessionFromCookie } from '@/lib/auth'
import { computePageLocaleCompleteness } from '@/lib/admin/pageLocaleCompleteness'
import { computeVaultLocaleLayerInfos } from '@/lib/admin/vaultLocaleSectionStatus'
import { getVaultPageTextFieldsForLocale, parseAdminVaultLocale } from '@/lib/admin/vaultAdminLocale'
import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

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
  /** Locale éditée (SectionContent + PageI18n pour cette langue). */
  locale: z.enum(['fr', 'en', 'it']),
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

function parseVaultConfigFromRaw(rawData: unknown): z.infer<typeof vaultConfigSchema> {
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
  return config
}

function applyExclusiveOfferVaultCategoryMeta<T extends { investmentTypeSlug?: string | undefined }>(
  config: T,
  productType: string | null | undefined,
): T {
  if (productType !== PackagedProductType.EXCLUSIVE_OFFER) return config
  return { ...config, investmentTypeSlug: EXCLUSIVE_OFFER_VAULT_INVESTMENT_TYPE_SLUG }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> | { slug: string } }
) {
  try {
    const resolved = await Promise.resolve(params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const editingLocale = parseAdminVaultLocale(request.nextUrl.searchParams.get('locale'))

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
        pageI18n: true,
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
    const draftForLocale = contents.find(
      (c) => c.locale === editingLocale && c.status === ContentStatus.DRAFT,
    )
    const publishedForLocale = contents.find(
      (c) => c.locale === editingLocale && c.status === ContentStatus.PUBLISHED,
    )
    const rawData = draftForLocale?.data
    let config = parseVaultConfigFromRaw(rawData)
    const publishedRaw = publishedForLocale?.data
    let publishedConfig = publishedRaw != null ? parseVaultConfigFromRaw(publishedRaw) : null

    const ppEarly = page.packagedProduct
    config = applyExclusiveOfferVaultCategoryMeta(config, ppEarly?.productType ?? null)
    if (publishedConfig) {
      publishedConfig = applyExclusiveOfferVaultCategoryMeta(publishedConfig, ppEarly?.productType ?? null)
    }

    const localeVaultLayers = computeVaultLocaleLayerInfos(
      contents.map((c) => ({
        locale: c.locale,
        status: c.status,
        data: c.data,
      })),
    )

    const updatedAt = page.updatedAt
    const i18nRows = page.pageI18n.map((r) => ({
      locale: r.locale,
      title: r.title,
      description: r.description,
    }))
    const { title: displayTitle, description: displayDescription } = getVaultPageTextFieldsForLocale(
      { title: page.title, description: page.description },
      i18nRows,
      editingLocale,
    )

    const pagePayload = {
      id: page.id,
      slug: page.slug,
      title: displayTitle,
      description: displayDescription,
      urlPath: page.urlPath,
      updatedAt: updatedAt instanceof Date ? updatedAt.toISOString() : String(updatedAt),
    }

    const completeness = computePageLocaleCompleteness({
      id: page.id,
      template: page.template,
      title: page.title,
      description: page.description,
      pageI18n: i18nRows,
      sections: [
        {
          id: section?.id ?? page.id,
          contents: contents.map((c) => ({ locale: c.locale, status: c.status })),
        },
      ],
    })

    const pp = page.packagedProduct
    const lendingRow =
      pp != null
        ? await prisma.lendingPoolProducts.findUnique({
            where: { packagedProductId: pp.id },
            select: { id: true },
          })
        : null
    const lendingEngineLinked = lendingRow != null
    const vaultEngineLinked =
      pp?.engineType === 'VAULT_ENGINE' && Boolean(pp.engineReferenceId?.trim())

    const packagedProduct = pp
      ? {
          id: pp.id,
          slug: pp.slug,
          pageId: pp.pageId,
          productType: pp.productType,
          commercialStatus: pp.commercialStatus,
          visibility: pp.visibility,
          featuredRank: pp.featuredRank,
          categorySlug:
            pp.productType === PackagedProductType.EXCLUSIVE_OFFER
              ? (pp.categorySlug ?? EXCLUSIVE_OFFER_VAULT_INVESTMENT_TYPE_SLUG)
              : pp.categorySlug,
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
          vaultEngineLinked,
          updatedAt: pp.updatedAt.toISOString(),
          publishedAt: pp.publishedAt ? pp.publishedAt.toISOString() : null,
        }
      : null

    return NextResponse.json({
      page: pagePayload,
      config,
      publishedConfig,
      localeVaultLayers,
      packagedProduct,
      editingLocale,
      localeCompleteness: completeness.locales,
    })
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
    const loc = parsed.locale as Locale
    if (!isValidLocale(loc)) {
      return NextResponse.json({ error: 'Invalid locale' }, { status: 400 })
    }

    const page = await prisma.page.findFirst({
      where: {
        slug,
        template: VAULT_TEMPLATE_DB,
      },
      include: {
        packagedProduct: { select: { productType: true } },
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

    const titleVal = parsed.title !== undefined ? parsed.title : undefined
    const descVal = parsed.description !== undefined ? parsed.description : undefined

    if (titleVal !== undefined || descVal !== undefined) {
      await prisma.pageI18n.upsert({
        where: { pageId_locale: { pageId: page.id, locale: loc } },
        create: {
          pageId: page.id,
          locale: loc,
          title: titleVal ?? null,
          description: descVal ?? null,
        },
        update: {
          ...(titleVal !== undefined ? { title: titleVal } : {}),
          ...(descVal !== undefined ? { description: descVal } : {}),
        },
      })

      if (loc === defaultLocale) {
        await prisma.page.update({
          where: { id: page.id },
          data: {
            ...(titleVal !== undefined ? { title: titleVal } : {}),
            ...(descVal !== undefined ? { description: descVal } : {}),
          },
        })
      }
    }

    const dataToSave = applyExclusiveOfferVaultCategoryMeta(
      parsed.config,
      page.packagedProduct?.productType ?? null,
    )

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: loc,
          status: ContentStatus.DRAFT,
        },
      },
      update: {
        data: dataToSave,
        updatedByUserId: session.userId,
      },
      create: {
        sectionId: section.id,
        locale: loc,
        status: ContentStatus.DRAFT,
        data: dataToSave,
        updatedByUserId: session.userId,
      },
    })

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

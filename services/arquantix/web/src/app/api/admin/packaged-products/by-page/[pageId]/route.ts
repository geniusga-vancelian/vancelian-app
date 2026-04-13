import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { packagedProductByPagePutSchema } from '@/lib/admin/packagedProductSchemas'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { isValidSlug } from '@/lib/utils/slugify'

const VAULT_TEMPLATE_DB = 'vault_builder'

function jsonError(message: string, status: number, extra?: Record<string, unknown>) {
  return NextResponse.json({ error: message, ...extra }, { status })
}

type SerializedPackaged = {
  id: string
  slug: string
  pageId: string
  productType: string
  commercialStatus: string
  visibility: string
  featuredRank: number | null
  categorySlug: string | null
  tags: string[]
  engineType: string | null
  engineReferenceId: string | null
  lendingEngineLinked: boolean
  updatedAt: string
  publishedAt: string | null
}

function normalizeTagsFromDb(tags: unknown): string[] {
  if (tags == null) return []
  if (Array.isArray(tags)) {
    return tags.filter((t): t is string => typeof t === 'string' && t.length > 0)
  }
  return []
}

function serializePackagedProduct(pp: {
  id: string
  slug: string
  pageId: string
  productType: string
  commercialStatus: string
  visibility: string
  featuredRank: number | null
  categorySlug: string | null
  tags: unknown
  engineType: string | null
  engineReferenceId: string | null
  publishedAt: Date | null
  updatedAt: Date
  lendingPoolProduct: { id: string } | null
}): SerializedPackaged {
  return {
    id: pp.id,
    slug: pp.slug,
    pageId: pp.pageId,
    productType: pp.productType,
    commercialStatus: pp.commercialStatus,
    visibility: pp.visibility,
    featuredRank: pp.featuredRank,
    categorySlug: pp.categorySlug,
    tags: normalizeTagsFromDb(pp.tags),
    engineType: pp.engineType,
    engineReferenceId: pp.engineReferenceId,
    lendingEngineLinked: pp.lendingPoolProduct != null,
    updatedAt: pp.updatedAt.toISOString(),
    publishedAt: pp.publishedAt ? pp.publishedAt.toISOString() : null,
  }
}

async function assertVaultPage(pageId: string) {
  const page = await prisma.page.findFirst({
    where: { id: pageId, template: VAULT_TEMPLATE_DB },
    select: { id: true },
  })
  return page
}

export async function GET(
  _request: NextRequest,
  { params }: { params: { pageId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return jsonError('Unauthorized', 401)
    }

    const pageId = params?.pageId?.trim()
    if (!pageId) {
      return jsonError('pageId requis', 400)
    }

    const page = await assertVaultPage(pageId)
    if (!page) {
      return jsonError('Page introuvable ou non Vault Builder', 404)
    }

    const pp = await prisma.packagedProduct.findUnique({
      where: { pageId },
      include: {
        lendingPoolProduct: { select: { id: true } },
      },
    })

    return NextResponse.json({
      packagedProduct: pp ? serializePackagedProduct(pp) : null,
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/packaged-products/by-page GET]', err.message)
    return jsonError('Internal server error', 500, { detail: err.message })
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { pageId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return jsonError('Unauthorized', 401)
    }

    const pageId = params?.pageId?.trim()
    if (!pageId) {
      return jsonError('pageId requis', 400)
    }

    const page = await assertVaultPage(pageId)
    if (!page) {
      return jsonError('Page introuvable ou non Vault Builder', 404)
    }

    const raw = await request.json()
    const parsed = packagedProductByPagePutSchema.parse(raw)

    const existing = await prisma.packagedProduct.findUnique({
      where: { pageId },
      include: {
        lendingPoolProduct: { select: { id: true } },
      },
    })

    if (!parsed.enabled) {
      if (!existing) {
        return NextResponse.json({ success: true, packagedProduct: null, action: 'noop' })
      }
      if (existing.lendingPoolProduct) {
        return jsonError(
          'Ce produit packagé est lié au moteur lending. Détachez la liaison (phase 5) avant de désactiver.',
          409,
          { code: 'LENDING_LINKED' }
        )
      }
      await prisma.packagedProduct.delete({ where: { id: existing.id } })
      return NextResponse.json({ success: true, packagedProduct: null, action: 'deleted' })
    }

    const slug = parsed.slug!.trim()
    if (!isValidSlug(slug)) {
      return jsonError('Slug invalide', 400, { path: 'slug' })
    }

    const productType = parsed.productType!
    const commercialStatus = parsed.commercialStatus ?? 'DRAFT'
    const visibility = parsed.visibility ?? 'PUBLIC'
    const featuredRank =
      parsed.featuredRank === undefined ? null : parsed.featuredRank
    const categorySlug =
      parsed.categorySlug === undefined || parsed.categorySlug === null || parsed.categorySlug === ''
        ? null
        : parsed.categorySlug.trim() || null

    const tagsList = parsed.tags ?? []

    const slugOwner = await prisma.packagedProduct.findFirst({
      where: {
        slug,
        NOT: { pageId },
      },
      select: { id: true },
    })
    if (slugOwner) {
      return jsonError(
        'Ce slug est déjà utilisé par un autre produit packagé. Choisissez un slug unique.',
        409,
        { code: 'SLUG_TAKEN' }
      )
    }

    const now = new Date()
    const publishedAtForCreate = commercialStatus === 'PUBLISHED' ? now : null

    const nextPublishedAt = (() => {
      if (commercialStatus !== 'PUBLISHED') {
        return existing?.publishedAt ?? null
      }
      if (existing?.publishedAt) return existing.publishedAt
      return now
    })()

    const result = await prisma.packagedProduct.upsert({
      where: { pageId },
      create: {
        pageId,
        slug,
        productType,
        commercialStatus,
        visibility,
        featuredRank,
        categorySlug,
        tags: tagsList.length > 0 ? tagsList : undefined,
        publishedAt: publishedAtForCreate,
      },
      update: {
        slug,
        productType,
        commercialStatus,
        visibility,
        featuredRank,
        categorySlug,
        tags: tagsList.length > 0 ? tagsList : [],
        publishedAt: nextPublishedAt,
      },
      include: {
        lendingPoolProduct: { select: { id: true } },
      },
    })

    return NextResponse.json({
      success: true,
      packagedProduct: serializePackagedProduct(result),
      action: existing ? 'updated' : 'created',
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 }
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/packaged-products/by-page PUT]', err.message)
    return jsonError('Internal server error', 500, { detail: err.message })
  }
}

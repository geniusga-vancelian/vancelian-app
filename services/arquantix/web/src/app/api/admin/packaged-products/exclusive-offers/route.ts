import { NextRequest, NextResponse } from 'next/server'
import { PackagedCommercialStatus, PackagedVisibility } from '@prisma/client'
import { z } from 'zod'

import { createExclusiveOfferVaultInTransaction } from '@/lib/admin/exclusiveOfferVaultCreate'
import {
  buildExclusiveOffersWhere,
  exclusiveOffersOrderBy,
  type EngineLinkedFilter,
  type ExclusiveOffersSort,
} from '@/lib/admin/exclusiveOffersAdminQuery'
import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { calculateUrlPath, isValidSlug, slugify } from '@/lib/utils/slugify'

const querySchema = z.object({
  q: z.string().optional(),
  commercialStatus: z.nativeEnum(PackagedCommercialStatus).optional(),
  visibility: z.nativeEnum(PackagedVisibility).optional(),
  engineLinked: z.enum(['all', 'linked', 'unlinked']).optional().default('all'),
  sort: z.enum(['updated_desc', 'featured_asc']).optional().default('updated_desc'),
})

const postSchema = z.object({
  title: z.string().max(200).optional(),
  description: z.string().max(1000).nullable().optional(),
  slug: z
    .string()
    .min(1)
    .max(60)
    .optional()
    .refine((s) => s == null || s === '' || isValidSlug(s.trim()), {
      message: 'Slug invalide',
    }),
})

function decToString(v: unknown): string | null {
  if (v == null) return null
  if (typeof v === 'object' && v !== null && 'toString' in v) {
    return (v as { toString: () => string }).toString()
  }
  return String(v)
}

/**
 * GET — liste les Exclusive Offers depuis `packaged_products` (type EXCLUSIVE_OFFER) + page vault_builder.
 *
 * Filtres : q, commercialStatus, visibility, engineLinked, sort.
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const sp = request.nextUrl.searchParams
    const parsed = querySchema.safeParse({
      q: sp.get('q') ?? undefined,
      commercialStatus: sp.get('commercialStatus') ?? undefined,
      visibility: sp.get('visibility') ?? undefined,
      engineLinked: sp.get('engineLinked') ?? undefined,
      sort: sp.get('sort') ?? undefined,
    })
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Paramètres invalides', issues: parsed.error.flatten() },
        { status: 400 }
      )
    }

    const q = parsed.data
    const where = buildExclusiveOffersWhere({
      q: q.q,
      commercialStatus: q.commercialStatus,
      visibility: q.visibility,
      engineLinked: q.engineLinked as EngineLinkedFilter,
      sort: q.sort as ExclusiveOffersSort,
    })
    const orderBy = exclusiveOffersOrderBy(q.sort as ExclusiveOffersSort)

    const rows = await prisma.packagedProduct.findMany({
      where,
      orderBy,
      include: {
        page: {
          select: {
            id: true,
            slug: true,
            title: true,
            urlPath: true,
            template: true,
            updatedAt: true,
          },
        },
        lendingPoolProduct: {
          select: {
            id: true,
            status: true,
            supplyAprBps: true,
            currentRaised: true,
            targetSize: true,
          },
        },
      },
    })

    const items = rows.map((pp) => {
      const page = pp.page
      const lpp = pp.lendingPoolProduct
      const templateOk = page.template === 'vault_builder'
      const integrityIssue = !page.id || !templateOk

      return {
        packagedProductId: pp.id,
        slug: pp.slug,
        productType: pp.productType,
        commercialStatus: pp.commercialStatus,
        visibility: pp.visibility,
        featuredRank: pp.featuredRank,
        categorySlug: pp.categorySlug,
        tags: Array.isArray(pp.tags)
          ? (pp.tags as unknown[]).filter((t): t is string => typeof t === 'string')
          : [],
        engineLinked: lpp != null,
        lendingSnapshot:
          lpp == null
            ? null
            : {
                poolProductId: lpp.id,
                status: lpp.status,
                supplyAprBps: decToString(lpp.supplyAprBps),
                currentRaised: decToString(lpp.currentRaised),
                targetSize: decToString(lpp.targetSize),
              },
        publicationState: pp.commercialStatus,
        page: page
          ? {
              id: page.id,
              slug: page.slug,
              title: page.title,
              urlPath: page.urlPath,
              template: page.template,
              updatedAt: page.updatedAt.toISOString(),
            }
          : null,
        packagedUpdatedAt: pp.updatedAt.toISOString(),
        publishedAt: pp.publishedAt ? pp.publishedAt.toISOString() : null,
        integrityIssue,
        integrityMessage: integrityIssue
          ? !templateOk
            ? 'PAGE_TEMPLATE_NOT_VAULT_BUILDER'
            : 'PAGE_MISSING'
          : null,
      }
    })

    return NextResponse.json({ items, count: items.length })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/packaged-products/exclusive-offers GET]', err.message)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 }
    )
  }
}

function generateDefaultSlug(): string {
  return `eo-${Date.now()}`
}

/**
 * POST — crée page Vault Builder + PackagedProduct EXCLUSIVE_OFFER (transaction).
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json().catch(() => ({}))
    const parsed = postSchema.safeParse(body)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Données invalides', issues: parsed.error.flatten() },
        { status: 400 }
      )
    }

    let slug = (parsed.data.slug ?? '').trim()
    if (!slug) {
      slug = generateDefaultSlug()
    } else {
      slug = slugify(slug)
    }

    if (!isValidSlug(slug)) {
      return NextResponse.json({ error: 'Slug invalide' }, { status: 400 })
    }

    const urlPath = calculateUrlPath(slug)
    const title = (parsed.data.title ?? '').trim() || 'Exclusive Offer'
    const description = parsed.data.description ?? null

    const existingPage = await prisma.page.findFirst({
      where: { OR: [{ slug }, { urlPath }] },
      select: { id: true },
    })
    const existingPp = await prisma.packagedProduct.findFirst({
      where: { slug },
      select: { id: true },
    })
    if (existingPage || existingPp) {
      return NextResponse.json(
        { error: 'Ce slug est déjà utilisé (page ou produit packagé).', code: 'SLUG_CONFLICT' },
        { status: 409 }
      )
    }

    try {
      const result = await prisma.$transaction((tx) =>
        createExclusiveOfferVaultInTransaction(tx, {
          slug,
          title,
          description,
        })
      )

      return NextResponse.json(
        {
          pageId: result.pageId,
          slug: result.slug,
          packagedProductId: result.packagedProductId,
          editUrl: `/admin/vault-builder?slug=${encodeURIComponent(result.slug)}&eo=1`,
        },
        { status: 201 }
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      console.error('[api/admin/packaged-products/exclusive-offers POST]', msg)
      if (msg.includes('Unique constraint') || msg.includes('unique constraint')) {
        return NextResponse.json(
          { error: 'Conflit de slug ou de clé unique. Réessayez avec un autre slug.', code: 'UNIQUE' },
          { status: 409 }
        )
      }
      return NextResponse.json({ error: 'Création impossible', detail: msg }, { status: 500 })
    }
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/packaged-products/exclusive-offers POST outer]', err.message)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 }
    )
  }
}

import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { getSessionFromCookie } from '@/lib/auth'
import {
  applyPageStructurePatch,
  getSiblingSlugsInDbOrder,
} from '@/lib/admin/pageStructureService'

const patchSchema = z
  .object({
    parentId: z.preprocess(
      (v) => (v === '' ? null : v),
      z.union([z.string().cuid(), z.null()]).optional(),
    ),
    sortOrder: z.number().int().min(0).max(999_999).optional(),
    reorderAmongSiblings: z.enum(['up', 'down']).optional(),
    siblingSlugsInOrder: z.array(z.string().min(1)).min(2).max(500).optional(),
  })
  .refine(
    (d) =>
      d.parentId !== undefined ||
      d.sortOrder !== undefined ||
      d.reorderAmongSiblings !== undefined ||
      (d.siblingSlugsInOrder !== undefined && d.siblingSlugsInOrder.length >= 2),
    { message: 'Au moins un champ requis' },
  )
  .refine(
    (d) => {
      const hasList = d.siblingSlugsInOrder !== undefined && d.siblingSlugsInOrder.length >= 2
      if (!hasList) return true
      return (
        d.reorderAmongSiblings === undefined &&
        d.parentId === undefined &&
        d.sortOrder === undefined
      )
    },
    { message: 'siblingSlugsInOrder doit être envoyé seul' },
  )

/**
 * GET /api/admin/pages/[slug]/structure — slugs des frères en base (même parent), ordre courant.
 *
 * PATCH — parentId, sortOrder, réordonnancement relatif (legacy), ou `siblingSlugsInOrder` (permutation complète).
 * Si `parentId` change : synchronise le menu primaire (suppression des liens si la page n’est plus racine,
 * création d’un lien si elle devient racine — hors home / vault). Ne modifie pas les URL publiques stockées.
 */
function normalizeSlug(slug: string | undefined): string {
  if (slug == null || typeof slug !== 'string') return ''
  return slug.trim().replace(/\/+$/, '')
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(context.params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Slug invalide' }, { status: 400 })
    }

    const result = await getSiblingSlugsInDbOrder(slug)
    if (!result.ok) {
      return NextResponse.json(
        { error: result.message, code: result.code },
        { status: result.status },
      )
    }
    return NextResponse.json({ slugs: result.slugs })
  } catch (error) {
    console.error('page structure GET:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ slug: string }> | { slug: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const resolved = await Promise.resolve(context.params)
    const slug = normalizeSlug(resolved?.slug)
    if (!slug) {
      return NextResponse.json({ error: 'Slug invalide' }, { status: 400 })
    }

    const raw = await request.json()
    const body = patchSchema.parse(raw)

    const result = await applyPageStructurePatch(slug, {
      parentId: body.parentId,
      sortOrder: body.sortOrder,
      reorderAmongSiblings: body.reorderAmongSiblings,
      siblingSlugsInOrder: body.siblingSlugsInOrder,
    })

    if (!result.ok) {
      return NextResponse.json(
        { error: result.message, code: result.code },
        { status: result.status },
      )
    }

    return NextResponse.json({ page: result.page })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Données invalides', issues: error.issues },
        { status: 400 },
      )
    }
    console.error('page structure PATCH:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

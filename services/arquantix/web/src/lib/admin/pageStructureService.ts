import type { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import type { Page } from '@prisma/client'
import {
  mustStayStructuralRoot,
  newParentWouldCreateCycle,
  parentCannotBeVaultTemplate,
} from '@/lib/admin/pageStructureValidation'
import { syncPrimaryMenuRootOrderInTx } from '@/lib/admin/syncPrimaryMenuRootOrderInTx'
import {
  deletePrimaryMenuItemsForPageTx,
  ensurePrimaryMenuLinkForRootPageTx,
} from '@/lib/cms/ensurePrimaryMenuTx'

export type StructurePatchBody = {
  parentId?: string | null
  sortOrder?: number
  reorderAmongSiblings?: 'up' | 'down'
  /** Permutation complète des slugs d’une même fratrie (même `parentId` en DB). */
  siblingSlugsInOrder?: string[]
}

export type StructurePatchResult =
  | { ok: true; page: Pick<Page, 'id' | 'slug' | 'parentId' | 'sortOrder'> }
  | { ok: false; status: number; code: string; message: string }

async function loadParentIdMap(): Promise<Map<string, string | null>> {
  const rows = await prisma.page.findMany({ select: { id: true, parentId: true } })
  const m = new Map<string, string | null>()
  for (const r of rows) m.set(r.id, r.parentId)
  return m
}

async function assignSequentialSiblingOrder(
  tx: Prisma.TransactionClient,
  orderedIds: string[],
): Promise<void> {
  for (let i = 0; i < orderedIds.length; i++) {
    await tx.page.update({
      where: { id: orderedIds[i] },
      data: { sortOrder: i },
    })
  }
}

/**
 * Ordre des slugs frères en base (`sort_order` puis `slug`).
 */
export async function getSiblingSlugsInDbOrder(
  slug: string,
): Promise<
  | { ok: true; slugs: string[] }
  | { ok: false; status: number; code: string; message: string }
> {
  const page = await prisma.page.findUnique({ where: { slug } })
  if (!page) {
    return { ok: false, status: 404, code: 'NOT_FOUND', message: 'Page introuvable' }
  }
  const siblings = await prisma.page.findMany({
    where: { parentId: page.parentId },
    orderBy: [{ sortOrder: 'asc' }, { slug: 'asc' }],
    select: { slug: true },
  })
  return { ok: true, slugs: siblings.map((s) => s.slug) }
}

export async function applyFullSiblingSlugOrder(
  contextSlug: string,
  orderedSlugs: string[],
): Promise<StructurePatchResult> {
  const page = await prisma.page.findUnique({ where: { slug: contextSlug } })
  if (!page) {
    return { ok: false, status: 404, code: 'NOT_FOUND', message: 'Page introuvable' }
  }

  const siblings = await prisma.page.findMany({
    where: { parentId: page.parentId },
    orderBy: [{ sortOrder: 'asc' }, { slug: 'asc' }],
    select: { id: true, slug: true },
  })
  const dbSlugs = siblings.map((s) => s.slug)
  if (orderedSlugs.length !== dbSlugs.length) {
    return {
      ok: false,
      status: 400,
      code: 'SIBLING_COUNT',
      message: 'La liste de fratrie doit contenir exactement les mêmes pages qu’en base',
    }
  }
  const dbSet = new Set(dbSlugs)
  if (dbSet.size !== new Set(orderedSlugs).size) {
    return {
      ok: false,
      status: 400,
      code: 'SIBLING_MISMATCH',
      message: 'Les slugs ne correspondent pas à la fratrie en base',
    }
  }
  for (const s of orderedSlugs) {
    if (!dbSet.has(s)) {
      return {
        ok: false,
        status: 400,
        code: 'SIBLING_UNKNOWN',
        message: `Slug inconnu dans la fratrie : ${s}`,
      }
    }
  }

  const bySlug = new Map(siblings.map((s) => [s.slug, s.id] as const))
  const orderedIds = orderedSlugs.map((s) => bySlug.get(s)!)

  const updated = await prisma.$transaction(async (tx) => {
    await assignSequentialSiblingOrder(tx, orderedIds)
    if (page.parentId === null) {
      await syncPrimaryMenuRootOrderInTx(tx, orderedSlugs)
    }
    return tx.page.findUniqueOrThrow({
      where: { id: page.id },
      select: { id: true, slug: true, parentId: true, sortOrder: true },
    })
  })

  return { ok: true, page: updated }
}

async function swapSiblingOrder(
  page: Pick<Page, 'id' | 'parentId' | 'sortOrder' | 'slug'>,
  direction: 'up' | 'down',
): Promise<StructurePatchResult> {
  try {
    const updated = await prisma.$transaction(async (tx) => {
      const siblings = await tx.page.findMany({
        where: { parentId: page.parentId },
        orderBy: [{ sortOrder: 'asc' }, { slug: 'asc' }],
      })
      const idx = siblings.findIndex((s) => s.id === page.id)
      if (idx < 0) {
        throw Object.assign(new Error('SIBLING_NOT_FOUND'), { code: 'SIBLING_NOT_FOUND' })
      }
      const j = direction === 'up' ? idx - 1 : idx + 1
      if (j < 0 || j >= siblings.length) {
        throw Object.assign(new Error('SIBLING_EDGE'), { code: 'SIBLING_EDGE' })
      }
      const order = [...siblings]
      const tmp = order[idx]
      order[idx] = order[j]
      order[j] = tmp
      const ids = order.map((s) => s.id)
      await assignSequentialSiblingOrder(tx, ids)
      return tx.page.findUniqueOrThrow({
        where: { id: page.id },
        select: { id: true, slug: true, parentId: true, sortOrder: true },
      })
    })
    return { ok: true, page: updated }
  } catch (e: unknown) {
    const code = e && typeof e === 'object' && 'code' in e ? String((e as { code: string }).code) : ''
    if (code === 'SIBLING_EDGE') {
      return {
        ok: false,
        status: 400,
        code: 'SIBLING_EDGE',
        message: 'Impossible de déplacer : déjà en tête ou en queue parmi les frères',
      }
    }
    if (code === 'SIBLING_NOT_FOUND') {
      return { ok: false, status: 400, code: 'SIBLING_NOT_FOUND', message: 'Fratrie introuvable' }
    }
    throw e
  }
}

/**
 * Met à jour `parentId` / `sortOrder`, réordonne par liste (`siblingSlugsInOrder`), ou `reorderAmongSiblings`.
 * À la racine (`parentId` null), `siblingSlugsInOrder` met aussi à jour l’ordre des entrées du menu primaire.
 * Ne modifie pas `urlPath` ni template.
 */
export async function applyPageStructurePatch(
  slug: string,
  body: StructurePatchBody,
): Promise<StructurePatchResult> {
  const page = await prisma.page.findUnique({ where: { slug } })
  if (!page) {
    return { ok: false, status: 404, code: 'NOT_FOUND', message: 'Page introuvable' }
  }

  const hasParent = body.parentId !== undefined
  const hasSort = body.sortOrder !== undefined
  const hasReorder = body.reorderAmongSiblings !== undefined
  const hasSiblingList =
    body.siblingSlugsInOrder !== undefined && body.siblingSlugsInOrder.length > 0

  if (hasSiblingList && (hasParent || hasSort || hasReorder)) {
    return {
      ok: false,
      status: 400,
      code: 'CONFLICTING_OPS',
      message: 'Réordonnancement par liste : n’envoyez pas parent, sortOrder ni up/down en même temps',
    }
  }

  if (hasSiblingList) {
    return applyFullSiblingSlugOrder(slug, body.siblingSlugsInOrder!)
  }

  if (hasReorder && (hasParent || hasSort)) {
    return {
      ok: false,
      status: 400,
      code: 'CONFLICTING_OPS',
      message: 'Utilisez « Monter / Descendre » seuls, ou enregistrez parent + ordre sans réordonnancement relatif',
    }
  }

  if (hasReorder) {
    return swapSiblingOrder(page, body.reorderAmongSiblings!)
  }

  if (!hasParent && !hasSort) {
    return { ok: false, status: 400, code: 'EMPTY_PATCH', message: 'Aucun champ à mettre à jour' }
  }

  let nextParentId = page.parentId
  if (hasParent) {
    nextParentId = body.parentId ?? null
  }

  if (mustStayStructuralRoot(page) && nextParentId !== null) {
    return {
      ok: false,
      status: 400,
      code: 'ROOT_REQUIRED',
      message: 'Cette page (accueil ou hub projets) doit rester à la racine de l’arbre',
    }
  }

  if (nextParentId !== null) {
    const parent = await prisma.page.findUnique({ where: { id: nextParentId } })
    if (!parent) {
      return { ok: false, status: 400, code: 'PARENT_NOT_FOUND', message: 'Parent inexistant' }
    }
    if (parent.id === page.id) {
      return { ok: false, status: 400, code: 'SELF_PARENT', message: 'Une page ne peut pas être son propre parent' }
    }
    if (parentCannotBeVaultTemplate(parent.template)) {
      return {
        ok: false,
        status: 400,
        code: 'VAULT_PARENT_FORBIDDEN',
        message: 'Une page vault ne peut pas servir de parent structurel',
      }
    }

    const parentMap = await loadParentIdMap()
    if (newParentWouldCreateCycle(page.id, nextParentId, parentMap)) {
      return {
        ok: false,
        status: 400,
        code: 'CYCLE',
        message: 'Ce parent créerait un cycle dans la hiérarchie',
      }
    }
  }

  const data: { parentId?: string | null; sortOrder?: number } = {}
  if (hasParent) data.parentId = nextParentId
  if (hasSort) {
    if (!Number.isFinite(body.sortOrder) || body.sortOrder! < 0 || body.sortOrder! > 999_999) {
      return {
        ok: false,
        status: 400,
        code: 'INVALID_SORT',
        message: 'sortOrder doit être un entier entre 0 et 999999',
      }
    }
    data.sortOrder = body.sortOrder
  }

  const prevParentId = page.parentId
  const parentChanged = hasParent && prevParentId !== nextParentId

  const updated = await prisma.$transaction(async (tx) => {
    const u = await tx.page.update({
      where: { id: page.id },
      data,
      select: {
        id: true,
        slug: true,
        parentId: true,
        sortOrder: true,
        title: true,
        template: true,
      },
    })

    if (parentChanged) {
      if (u.parentId !== null) {
        await deletePrimaryMenuItemsForPageTx(tx, page.id)
      } else {
        await ensurePrimaryMenuLinkForRootPageTx(tx, u)
      }
    }

    return u
  })

  return {
    ok: true,
    page: {
      id: updated.id,
      slug: updated.slug,
      parentId: updated.parentId,
      sortOrder: updated.sortOrder,
    },
  }
}

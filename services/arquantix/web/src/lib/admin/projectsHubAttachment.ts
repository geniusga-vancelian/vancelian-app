/**
 * Rattachement éditorial des pages Vault sous le hub « projects » (arborescence CMS).
 */
import type { PrismaClient } from '@prisma/client'

type PageDelegate = PrismaClient['page']

/** Client Prisma ou transaction — accès `page` suffit. */
export type PageDb = { page: PageDelegate }

/**
 * Page hub liste projets : préférence `slug = projects`, sinon `pageRole = PROJECTS_HUB`.
 */
export async function resolveProjectsHubPageId(db: PageDb): Promise<string | null> {
  const bySlug = await db.page.findFirst({
    where: { slug: 'projects' },
    select: { id: true },
  })
  if (bySlug) return bySlug.id
  const byRole = await db.page.findFirst({
    where: { pageRole: 'PROJECTS_HUB' },
    select: { id: true },
  })
  return byRole?.id ?? null
}

/** Prochain `sortOrder` parmi les enfants actuels du hub (append). */
export async function nextChildSortOrderUnderHub(db: PageDb, hubId: string): Promise<number> {
  const agg = await db.page.aggregate({
    where: { parentId: hubId },
    _max: { sortOrder: true },
  })
  return (agg._max.sortOrder ?? -1) + 1
}

export interface RepairVaultPagesUnderHubResult {
  hubId: string
  updatedCount: number
}

/**
 * Rattache toutes les pages `vault_builder` (sauf home / projects) sous le hub projets.
 * Idempotent (ne met à jour que si `parentId` est absent ou différent du hub).
 */
export async function repairVaultPagesUnderProjectsHub(
  prisma: PrismaClient,
): Promise<RepairVaultPagesUnderHubResult | { error: string }> {
  const hubId = await resolveProjectsHubPageId(prisma)
  if (!hubId) {
    return { error: 'Aucune page hub trouvée (slug « projects » ou rôle PROJECTS_HUB).' }
  }

  const result = await prisma.page.updateMany({
    where: {
      template: 'vault_builder',
      slug: { notIn: ['home', 'projects'] },
      id: { not: hubId },
      OR: [{ parentId: null }, { parentId: { not: hubId } }],
    },
    data: { parentId: hubId },
  })

  return { hubId, updatedCount: result.count }
}

import type { Prisma } from '@prisma/client'

/**
 * Réordonne les `MenuItem.order` du menu primaire pour refléter `orderedSlugs`
 * (pages à la racine, même ordre qu’après `siblingSlugsInOrder`).
 * Les entrées sans lien vers ces pages gardent leur ordre relatif en queue.
 * Doit être exécuté dans une transaction Prisma déjà ouverte (contrainte unique sur `order`).
 */
export async function syncPrimaryMenuRootOrderInTx(
  tx: Prisma.TransactionClient,
  orderedSlugs: string[],
): Promise<void> {
  const menu = await tx.menu.findUnique({
    where: { key: 'primary' },
    select: { id: true },
  })
  if (!menu) return

  const pages = await tx.page.findMany({
    where: { slug: { in: orderedSlugs } },
    select: { id: true, slug: true, pageRole: true },
  })
  const idBySlug = new Map(pages.map((p) => [p.slug, p.id] as const))
  const homePage = pages.find((p) => p.pageRole === 'HOME' || p.slug === 'home')
  const homeSlug = homePage?.slug ?? 'home'

  const menuItems = await tx.menuItem.findMany({
    where: { menuId: menu.id },
    orderBy: { order: 'asc' },
  })
  if (menuItems.length === 0) return

  const used = new Set<string>()
  const reorderedIds: string[] = []

  for (const slug of orderedSlugs) {
    const pageId = idBySlug.get(slug)
    const match = menuItems.find((mi) => {
      if (used.has(mi.id)) return false
      if (pageId != null && mi.pageId === pageId) return true
      if (slug === homeSlug && mi.isRoot && !mi.pageId) return true
      return false
    })
    if (match) {
      reorderedIds.push(match.id)
      used.add(match.id)
    }
  }

  for (const mi of menuItems) {
    if (!used.has(mi.id)) reorderedIds.push(mi.id)
  }

  const TEMP_BASE = 1_000_000
  for (let i = 0; i < reorderedIds.length; i++) {
    await tx.menuItem.update({
      where: { id: reorderedIds[i] },
      data: { order: TEMP_BASE + i },
    })
  }
  for (let i = 0; i < reorderedIds.length; i++) {
    await tx.menuItem.update({
      where: { id: reorderedIds[i] },
      data: { order: i },
    })
  }
}

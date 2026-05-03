import type { Prisma } from '@prisma/client'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'

/**
 * Retourne l’id du menu `primary`, en le créant avec une entrée Home `isRoot` si absent.
 */
export async function ensurePrimaryMenuIdWithTx(tx: Prisma.TransactionClient): Promise<string> {
  const existing = await tx.menu.findUnique({
    where: { key: 'primary' },
    select: { id: true },
  })
  if (existing) return existing.id
  const created = await tx.menu.create({
    data: {
      key: 'primary',
      name: 'Primary Menu',
      menuItems: {
        create: {
          label: 'Home',
          isRoot: true,
          pageId: null,
          order: 0,
          enabled: true,
        },
      },
    },
    select: { id: true },
  })
  return created.id
}

/**
 * Supprime les entrées du menu primaire qui pointaient vers cette page (i18n en cascade).
 */
export async function deletePrimaryMenuItemsForPageTx(
  tx: Prisma.TransactionClient,
  pageId: string,
): Promise<void> {
  await tx.menuItem.deleteMany({
    where: {
      pageId,
      menu: { key: 'primary' },
    },
  })
}

/**
 * Garantit une entrée LINK dans le menu primaire pour une page **à la racine** CMS.
 * — Pas pour `home` (représentée par l’item `isRoot`).
 * — Pas pour les pages vault builder (filtrées du menu public).
 */
export async function ensurePrimaryMenuLinkForRootPageTx(
  tx: Prisma.TransactionClient,
  page: { id: string; slug: string; title: string | null; template: string },
): Promise<void> {
  if (page.slug === 'home') return
  if (page.template === VAULT_BUILDER_TEMPLATE) return

  const existing = await tx.menuItem.findFirst({
    where: { pageId: page.id, menu: { key: 'primary' } },
    select: { id: true },
  })
  if (existing) return

  const menuId = await ensurePrimaryMenuIdWithTx(tx)
  const lastItem = await tx.menuItem.findFirst({
    where: { menuId },
    orderBy: { order: 'desc' },
    select: { order: true },
  })
  const order = lastItem ? lastItem.order + 1 : 0
  const label =
    (page.title && page.title.trim()) ||
    page.slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

  await tx.menuItem.create({
    data: {
      menuId,
      label,
      type: 'LINK',
      isRoot: false,
      pageId: page.id,
      order,
      enabled: true,
    },
  })
}

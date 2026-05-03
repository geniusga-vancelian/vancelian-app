import type { MenuItem, Page } from '@prisma/client'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'

export type MenuItemWithPage = MenuItem & { page: Page | null }

export type MenuStructureWarning = {
  code: string
  severity: 'info' | 'warning'
  message: string
}

/**
 * Pages à refléter dans le menu (ordre profondeur d’abord) : `showInNav`, hors accueil
 * (l’accueil est représenté par l’item `isRoot` du menu, pas par un lien page).
 */
export function flattenNavTreePreorder(nodes: SiteTreeNode[]): SiteTreeNode[] {
  const out: SiteTreeNode[] = []
  const walk = (list: SiteTreeNode[]) => {
    for (const n of list) {
      if (n.showInNav && n.slug !== 'home' && n.pageRole !== 'HOME') {
        out.push(n)
      }
      if (n.children.length) walk(n.children)
    }
  }
  walk(nodes)
  return out
}

function expectedVaultUrlPath(slug: string): string {
  return `/projects/${slug}`
}

export function extractMenuNavPageSequence(
  items: MenuItemWithPage[],
  navPageIdsOrdered: string[],
): string[] {
  const navSet = new Set(navPageIdsOrdered)
  const sorted = [...items].sort((a, b) => a.order - b.order)
  const seen = new Set<string>()
  const seq: string[] = []
  for (const it of sorted) {
    if (it.type !== 'LINK' || it.isRoot || !it.pageId || !navSet.has(it.pageId)) continue
    if (seen.has(it.pageId)) continue
    seen.add(it.pageId)
    seq.push(it.pageId)
  }
  return seq
}

export function navOrderMatchesMenu(
  navPageIds: string[],
  menuNavSequence: string[],
): boolean {
  if (navPageIds.length !== menuNavSequence.length) return false
  return navPageIds.every((id, i) => id === menuNavSequence[i])
}

export function computeMenuStructureReport(
  tree: SiteTreeNode[],
  items: MenuItemWithPage[],
): {
  navPageOrder: { id: string; slug: string; title: string | null }[]
  warnings: MenuStructureWarning[]
  orderMatchesNavTree: boolean
  missingMenuPageIds: string[]
  menuNavSequence: string[]
} {
  const warnings: MenuStructureWarning[] = []
  const navPages = flattenNavTreePreorder(tree)
  const navIds = navPages.map((p) => p.id)

  const roots = items.filter((i) => i.isRoot)
  if (roots.length === 0) {
    warnings.push({
      code: 'MISSING_ROOT',
      severity: 'warning',
      message: 'Aucun élément « racine » (accueil) dans le menu — ajoutez-en un pour le lien vers la home.',
    })
  } else if (roots.length > 1) {
    warnings.push({
      code: 'MULTIPLE_ROOTS',
      severity: 'warning',
      message: 'Plusieurs éléments racine : corrigez avant d’utiliser la réordonnancement automatique.',
    })
  }

  const linkItems = items.filter((i) => i.type === 'LINK' && !i.isRoot)
  const pageIdToMenuIds = new Map<string, string[]>()
  for (const it of linkItems) {
    if (!it.pageId) continue
    const arr = pageIdToMenuIds.get(it.pageId) ?? []
    arr.push(it.id)
    pageIdToMenuIds.set(it.pageId, arr)
  }
  for (const [pageId, ids] of pageIdToMenuIds) {
    if (ids.length > 1) {
      warnings.push({
        code: 'DUPLICATE_MENU_LINK_PAGE',
        severity: 'warning',
        message: `Plusieurs entrées menu pointent vers la même page (${pageId}).`,
      })
    }
  }

  const linkedPageIds = new Set(
    linkItems.filter((i) => i.pageId && i.page).map((i) => i.pageId!),
  )
  const missingMenuPageIds = navIds.filter((id) => !linkedPageIds.has(id))
  if (missingMenuPageIds.length) {
    warnings.push({
      code: 'TREE_PAGE_NOT_IN_MENU',
      severity: 'info',
      message: `${missingMenuPageIds.length} page(s) visibles dans la structure (showInNav) sans entrée lien dans le menu.`,
    })
  }

  for (const it of linkItems) {
    if (it.pageId && it.page && !it.page.showInNav) {
      warnings.push({
        code: 'MENU_LINK_PAGE_HIDDEN_FROM_NAV',
        severity: 'warning',
        message: `Le menu lie « ${it.page.slug} » mais la page a showInNav = false.`,
      })
    }
    if (it.pageId && !it.page) {
      warnings.push({
        code: 'MENU_ORPHAN_LINK',
        severity: 'warning',
        message: `Entrée menu « ${it.label} » : page supprimée ou cible invalide.`,
      })
    }
    const p = it.page
    if (p && p.template === VAULT_BUILDER_TEMPLATE && p.slug !== 'home') {
      const expected = expectedVaultUrlPath(p.slug)
      if (p.urlPath !== expected) {
        warnings.push({
          code: 'VAULT_URL_PATH_MISMATCH',
          severity: 'warning',
          message: `Vault « ${p.slug} » : urlPath en base (${p.urlPath}) ≠ attendu (${expected}).`,
        })
      }
    }
  }

  const menuNavSequence = extractMenuNavPageSequence(items, navIds)
  const orderMatchesNavTree = navOrderMatchesMenu(navIds, menuNavSequence)
  if (!orderMatchesNavTree && missingMenuPageIds.length === 0 && navIds.length > 0) {
    warnings.push({
      code: 'ORDER_DIVERGENCE',
      severity: 'info',
      message: "L'ordre des liens (pages showInNav) ne suit pas l'ordre de l'arborescence.",
    })
  }

  return {
    navPageOrder: navPages.map((p) => ({ id: p.id, slug: p.slug, title: p.title })),
    warnings,
    orderMatchesNavTree,
    missingMenuPageIds,
    menuNavSequence,
  }
}

/**
 * Ordre cible après sync : racine (si une seule utilisée en tête), puis un lien par page
 * `nav` dans l’ordre arbre, puis toutes les autres entrées (ordre précédent conservé).
 */
export function buildPostSyncItemOrder(
  menuItems: MenuItemWithPage[],
  tree: SiteTreeNode[],
): string[] {
  const sorted = [...menuItems].sort((a, b) => a.order - b.order)
  const navPages = flattenNavTreePreorder(tree)
  const used = new Set<string>()
  const orderedIds: string[] = []

  const roots = sorted.filter((i) => i.isRoot)
  const root = roots[0]
  if (root) {
    orderedIds.push(root.id)
    used.add(root.id)
  }

  for (const p of navPages) {
    const link = sorted.find(
      (i) =>
        !used.has(i.id) && i.type === 'LINK' && !i.isRoot && i.pageId === p.id,
    )
    if (link) {
      orderedIds.push(link.id)
      used.add(link.id)
    }
  }

  for (const i of sorted) {
    if (!used.has(i.id)) {
      orderedIds.push(i.id)
      used.add(i.id)
    }
  }

  if (orderedIds.length !== menuItems.length) {
    throw new Error('buildPostSyncItemOrder: nombre d’items incohérent')
  }
  return orderedIds
}

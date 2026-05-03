import type { Page, PackagedProduct, PageRole } from '@prisma/client'
import { PackagedProductType } from '@prisma/client'
import type { Locale } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'

export type SiteTreePackagedProductRef = {
  id: string
  slug: string
  productType: string
}

/** Zone droite du menu public : sélecteur de langue + boutons d’action (ordre unifié). */
export type SiteTreeNavRightRailRow =
  | {
      kind: 'language_switcher'
      id: string
      order: number
      label: string
      /** Faux si l’entrée existe en base mais est désactivée (visible admin uniquement). */
      enabled: boolean
    }
  | {
      kind: 'button'
      id: string
      label: string
      order: number
      buttonStyle: string | null
      externalUrl: string | null
      enabled: boolean
      /** Libellés par locale (pastilles comme les pages). */
      localeCompleteness: Record<Locale, LocaleCompletenessLevel>
    }

/** Modules réutilisables sur tout le site (footer, etc.) — section « Modules communs » dans la structure. */
export type SiteTreeGlobalCommonModuleRow = {
  id: string
  kind: 'footer' | 'common_reusable'
  label: string
  description: string
  /** Présent pour les modules optionnels (ex. `cta`). */
  sectionKey?: string
  localeCompleteness: Record<Locale, LocaleCompletenessLevel>
  editHref: string
  /** Footer : verrouillé ; modules créés en Zone 2 : supprimables. */
  systemLocked: boolean
}

export type SiteTreeNode = {
  id: string
  slug: string
  title: string | null
  urlPath: string
  template: string
  parentId: string | null
  sortOrder: number
  pageRole: PageRole
  showInNav: boolean
  isSystemPage: boolean
  children: SiteTreeNode[]
  packagedProduct: SiteTreePackagedProductRef | null
  /** Lot 6 — complétude éditoriale par locale (API site-tree enrichie). */
  localeCompleteness?: Record<Locale, LocaleCompletenessLevel>
  /**
   * Lien barre de navigation (niveau 1) pointant vers cette page : complétude des libellés `MenuItem`.
   */
  menuNavLink?: {
    menuItemId: string
    labelCompleteness: Record<Locale, LocaleCompletenessLevel>
  }
  /**
   * Entrée injectée pour l’admin (ex. article `Article` Prisma) — pas une ligne `pages`.
   * `id` préfixé `blog-article:` ; la structure réelle des pages ne change pas.
   */
  isVirtual?: boolean
  articleId?: string
}

type PageRow = Page & {
  packagedProduct: Pick<PackagedProduct, 'id' | 'slug' | 'productType'> | null
}

/**
 * Construit une forêt d’arbres depuis des lignes `Page` plates (parentId + sortOrder).
 * Parents manquants → nœuds traités comme racines.
 */
export function buildSiteTreeFromPages(pages: PageRow[]): SiteTreeNode[] {
  const byId = new Map<string, SiteTreeNode>()

  for (const p of pages) {
    byId.set(p.id, {
      id: p.id,
      slug: p.slug,
      title: p.title,
      urlPath: p.urlPath,
      template: p.template,
      parentId: p.parentId,
      sortOrder: p.sortOrder,
      pageRole: p.pageRole,
      showInNav: p.showInNav,
      isSystemPage: p.isSystemPage,
      children: [],
      packagedProduct: p.packagedProduct
        ? {
            id: p.packagedProduct.id,
            slug: p.packagedProduct.slug,
            productType: p.packagedProduct.productType,
          }
        : null,
    })
  }

  const roots: SiteTreeNode[] = []
  const cmp = (a: SiteTreeNode, b: SiteTreeNode) => {
    if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
    return a.slug.localeCompare(b.slug)
  }

  for (const p of pages) {
    const node = byId.get(p.id)!
    if (p.parentId && byId.has(p.parentId)) {
      byId.get(p.parentId)!.children.push(node)
    } else {
      roots.push(node)
    }
  }

  const sortRecursive = (nodes: SiteTreeNode[]) => {
    nodes.sort(cmp)
    for (const n of nodes) sortRecursive(n.children)
  }
  sortRecursive(roots)
  return roots
}

/**
 * Masque dans l’arborescence admin les pages `vault_builder` liées à une offre exclusive :
 * le détail éditorial reste dans Vault Builder / Exclusive Offers, comme les articles hors arbre.
 */
export function pruneExclusiveOfferVaultPagesFromTree(nodes: SiteTreeNode[]): SiteTreeNode[] {
  return nodes.map((n) => ({
    ...n,
    children: pruneExclusiveOfferVaultPagesFromTree(
      n.children.filter(
        (c) =>
          !(
            c.template === VAULT_BUILDER_TEMPLATE &&
            c.packagedProduct?.productType === PackagedProductType.EXCLUSIVE_OFFER
          ),
      ),
    ),
  }))
}

function isExclusiveOfferVaultNode(n: SiteTreeNode): boolean {
  return (
    n.template === VAULT_BUILDER_TEMPLATE &&
    n.packagedProduct?.productType === PackagedProductType.EXCLUSIVE_OFFER
  )
}

/**
 * Retire toutes les pages vault « offre exclusive » de leur parent actuel (souvent le hub projets)
 * et les rattache en enfants du gabarit CMS `exclusive-offer` (affichage admin uniquement).
 * Si le gabarit est absent, les pages restent sous le hub `projects` (fallback).
 */
export function reparentExclusiveOfferVaultsUnderGabarit(roots: SiteTreeNode[]): SiteTreeNode[] {
  const collected: SiteTreeNode[] = []

  const stripNode = (n: SiteTreeNode): SiteTreeNode => {
    const children: SiteTreeNode[] = []
    for (const c of n.children) {
      if (isExclusiveOfferVaultNode(c)) {
        collected.push({ ...c, children: [] })
      } else {
        children.push(stripNode(c))
      }
    }
    return { ...n, children }
  }

  const stripped = roots.map(stripNode)
  if (collected.length === 0) return stripped

  collected.sort((a, b) => {
    if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
    return a.slug.localeCompare(b.slug)
  })

  const injectUnderGabarit = (nodes: SiteTreeNode[]): { ok: boolean; out: SiteTreeNode[] } => {
    let ok = false
    const out = nodes.map((n) => {
      if (n.slug === EXCLUSIVE_OFFER_GABARIT_SLUG && n.template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE) {
        ok = true
        return { ...n, children: [...n.children, ...collected] }
      }
      const sub = injectUnderGabarit(n.children)
      if (sub.ok) {
        ok = true
        return { ...n, children: sub.out }
      }
      return n
    })
    return { ok, out }
  }

  const { ok, out } = injectUnderGabarit(stripped)
  if (ok) return out

  const attachToProjectsHub = (nodes: SiteTreeNode[]): SiteTreeNode[] =>
    nodes.map((n) => {
      if (n.pageRole === 'PROJECTS_HUB' || n.slug === 'projects') {
        return { ...n, children: [...n.children, ...collected] }
      }
      return { ...n, children: attachToProjectsHub(n.children) }
    })

  return attachToProjectsHub(stripped)
}

/** Remonte le gabarit `exclusive-offer` juste sous le hub projets (tri d’affichage admin). */
export function sortProjectsHubChildrenForAdminTree(nodes: SiteTreeNode[]): SiteTreeNode[] {
  return nodes.map((n) => {
    const children = sortProjectsHubChildrenForAdminTree(n.children)
    if (n.pageRole === 'PROJECTS_HUB' || n.slug === 'projects') {
      children.sort((a, b) => {
        if (a.slug === EXCLUSIVE_OFFER_GABARIT_SLUG) return -1
        if (b.slug === EXCLUSIVE_OFFER_GABARIT_SLUG) return 1
        if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
        return a.slug.localeCompare(b.slug)
      })
    }
    return { ...n, children }
  })
}

/** Données menu alignées sur `getPrimaryMenu` / `Navigation` (tri par `order`, types normalisés). */
export type PrimaryMenuItemForPageOrder = {
  type: string
  isRoot: boolean
  pageId: string | null
  order: number
  enabled?: boolean
  buttonStyle?: string | null
  buttonAction?: string | null
  externalUrl?: string | null
  page?: { template: string; slug?: string | null } | null
  /** @see MenuNavigationNodeKind — défaut métier `PAGE` si absent. */
  navigationNodeKind?: string | null
}

/**
 * Ordre des pages tel qu’à la racine du menu primaire sur le site (liens triés par `MenuItem.order`).
 * — Entrée d’accueil (`isRoot`) → `homePageId` ; pages vault builder exclues comme en nav publique.
 * — Même normalisation BUTTON → « lien » que `getPrimaryMenu` pour les entrées type texte / interne.
 * — Si aucune entrée ne pointe vers la page blog et `blogPageId` est fourni, append comme le fallback blog du layout.
 */
/**
 * Page CMS ciblée par une entrée du menu primaire lorsqu’elle se comporte comme un lien
 * de navigation racine (même logique que l’ordre d’affichage du menu).
 */
export function primaryMenuItemContributesNavRootPageId(
  item: PrimaryMenuItemForPageOrder,
  context: { homePageId: string | null },
): string | null {
  if (item.page?.template === VAULT_BUILDER_TEMPLATE) return null

  const itemType = item.type || 'LINK'
  if (itemType === 'LANGUAGE_SWITCHER') {
    return null
  }
  const buttonStyle = (item.buttonStyle || '').toLowerCase()
  const buttonLooksLikeNavLink =
    itemType === 'BUTTON' &&
    !item.buttonAction &&
    (buttonStyle === '' ||
      buttonStyle === 'text' ||
      buttonStyle === 'ghost' ||
      buttonStyle === 'link') &&
    (!!item.page ||
      !item.externalUrl ||
      (item.externalUrl ?? '').trim() === '' ||
      (item.externalUrl ?? '').trim() === '#' ||
      (item.externalUrl ?? '').trim().startsWith('/'))

  const normalizedType: 'LINK' | 'BUTTON' = buttonLooksLikeNavLink
    ? 'LINK'
    : (itemType as 'LINK' | 'BUTTON')

  if (normalizedType === 'LINK' && !item.isRoot && !item.pageId) {
    const kind = (item.navigationNodeKind || 'PAGE').toString()
    if (kind !== 'EXTERNAL_LINK') {
      return null
    }
  }

  if (normalizedType === 'BUTTON') {
    return null
  }

  if (item.isRoot && context.homePageId) {
    return context.homePageId
  }

  if (item.pageId) {
    return item.pageId
  }

  return null
}

export function extractPrimaryMenuPageIdOrder(
  items: PrimaryMenuItemForPageOrder[],
  context: { homePageId: string | null; blogPageId: string | null },
): string[] {
  const sorted = [...items].filter((i) => i.enabled !== false).sort((a, b) => a.order - b.order)
  const seen = new Set<string>()
  const out: string[] = []

  const push = (id: string | null | undefined) => {
    if (!id || seen.has(id)) return
    seen.add(id)
    out.push(id)
  }

  for (const item of sorted) {
    const id = primaryMenuItemContributesNavRootPageId(item, {
      homePageId: context.homePageId,
    })
    if (id) push(id)
  }

  const blogLinked = sorted.some(
    (item) =>
      item.page?.slug === 'blog' ||
      (context.blogPageId != null && item.pageId === context.blogPageId),
  )
  if (context.blogPageId && !blogLinked) {
    push(context.blogPageId)
  }

  return out
}

function sortTreeLevelByPrimaryMenu(
  nodes: SiteTreeNode[],
  menuIndex: Map<string, number>,
  baseRank: number,
): SiteTreeNode[] {
  const ordered = [...nodes].sort((a, b) => {
    const ia = menuIndex.has(a.id) ? menuIndex.get(a.id)! : baseRank + a.sortOrder
    const ib = menuIndex.has(b.id) ? menuIndex.get(b.id)! : baseRank + b.sortOrder
    if (ia !== ib) return ia - ib
    if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
    return a.slug.localeCompare(b.slug)
  })

  return ordered.map((node) => ({
    ...node,
    children: sortTreeLevelByPrimaryMenu(node.children, menuIndex, baseRank),
  }))
}

/**
 * Réordonne chaque niveau de l’arbre : entrées présentes dans le menu primaire
 * dans l’ordre du menu, puis les autres par `sortOrder` / slug.
 */
export function orderSiteTreeLikePrimaryMenu(
  roots: SiteTreeNode[],
  menuPageIdsInOrder: string[],
): SiteTreeNode[] {
  if (menuPageIdsInOrder.length === 0) return roots
  const menuIndex = new Map<string, number>()
  menuPageIdsInOrder.forEach((id, i) => {
    if (!menuIndex.has(id)) menuIndex.set(id, i)
  })
  const baseRank = menuPageIdsInOrder.length
  return sortTreeLevelByPrimaryMenu(roots, menuIndex, baseRank)
}

/**
 * Arbre « Pages » admin : toutes les pages CMS y compris les vaults offre exclusive,
 * présentés sous le gabarit `exclusive-offer` + ordre gabarit sous projets + optionnellement menu primaire.
 */
export function buildAdminSiteDisplayTreeFromPages(
  pages: PageRow[],
  primaryMenuPageIdOrder?: string[],
): SiteTreeNode[] {
  let roots = sortProjectsHubChildrenForAdminTree(
    reparentExclusiveOfferVaultsUnderGabarit(buildSiteTreeFromPages(pages)),
  )
  if (primaryMenuPageIdOrder && primaryMenuPageIdOrder.length > 0) {
    roots = orderSiteTreeLikePrimaryMenu(roots, primaryMenuPageIdOrder)
  }
  return roots
}

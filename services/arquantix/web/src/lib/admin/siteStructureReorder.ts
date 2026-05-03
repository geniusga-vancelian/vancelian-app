import { PackagedProductType } from '@prisma/client'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'
import { findNodeById } from '@/lib/admin/siteStructureTreeEditing'

/** Vault offre exclusive : affiché ailleurs dans l’arbre admin — pas de ↑↓ ici. */
export function isExclusiveOfferVaultPage(node: SiteTreeNode): boolean {
  return (
    node.template === VAULT_BUILDER_TEMPLATE &&
    node.packagedProduct?.productType === PackagedProductType.EXCLUSIVE_OFFER
  )
}

/**
 * Frères affichés sous le même parent dans l’arbre (ordre à l’écran), pour un `parentId` DB donné.
 * Exclut les entrées virtuelles et les vaults offre exclusive.
 */
export function collectVisualSiblingsForReorder(
  roots: SiteTreeNode[],
  node: SiteTreeNode,
): SiteTreeNode[] {
  if (node.isVirtual) return []
  const pid = node.parentId
  const bucket = pid === null ? roots : findNodeById(roots, pid)?.children ?? []
  return bucket.filter(
    (n) =>
      !n.isVirtual && n.parentId === pid && !isExclusiveOfferVaultPage(n),
  )
}

/**
 * Réordonne les slugs « visibles » tout en laissant les autres frères (même parent en DB mais absents du bucket,
 * ex. vaults sous un autre nœud d’affichage) à leur place dans la séquence complète.
 */
export function mergeSiblingOrderPreservingHidden(
  fullDbOrder: string[],
  visNewOrder: string[],
  visSlotSlugs: Set<string>,
): string[] {
  let i = 0
  return fullDbOrder.map((slug) => {
    if (!visSlotSlugs.has(slug)) return slug
    return visNewOrder[i++]
  })
}

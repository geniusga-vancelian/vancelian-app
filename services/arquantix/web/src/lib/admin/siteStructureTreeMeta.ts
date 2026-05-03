import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'

export type SiteStructureTreeMeta = {
  /** Pages vault (`vault_builder`) présentes à la racine de l’arbre (parent absent ou non hub). */
  vaultPagesAtRoot: number
  /** Au moins un nœud hub projets (rôle ou slug `projects`). */
  hasProjectsHub: boolean
}

/**
 * Métadonnées pour bannières d’aide (pages hub absentes, vaults non rattachés, etc.).
 */
export function analyzeSiteTreeStructure(tree: SiteTreeNode[]): SiteStructureTreeMeta {
  let vaultPagesAtRoot = 0
  let hasProjectsHub = false

  const visit = (nodes: SiteTreeNode[], depth: number) => {
    for (const n of nodes) {
      if (n.pageRole === 'PROJECTS_HUB' || n.slug === 'projects') {
        hasProjectsHub = true
      }
      if (
        depth === 0 &&
        n.template === VAULT_BUILDER_TEMPLATE &&
        n.slug !== 'home' &&
        n.slug !== 'projects'
      ) {
        vaultPagesAtRoot += 1
      }
      if (n.children.length) visit(n.children, depth + 1)
    }
  }

  visit(tree, 0)
  return { vaultPagesAtRoot, hasProjectsHub }
}

import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'

export function findNodeById(nodes: SiteTreeNode[], id: string): SiteTreeNode | null {
  for (const n of nodes) {
    if (n.id === id) return n
    const c = findNodeById(n.children, id)
    if (c) return c
  }
  return null
}

/** La page sélectionnée et toute sa descendance ne peuvent pas être choisies comme parent (évite cycles). */
export function collectDescendantIds(root: SiteTreeNode): Set<string> {
  const s = new Set<string>()
  const dfs = (x: SiteTreeNode) => {
    s.add(x.id)
    for (const c of x.children) dfs(c)
  }
  dfs(root)
  return s
}

export type ParentOption = { value: string; label: string }

/**
 * Options pour le `<select>` parent : racine + tous les nœuds hors sous-arbre interdit.
 */
export function buildParentSelectOptions(
  tree: SiteTreeNode[],
  selected: SiteTreeNode,
): ParentOption[] {
  const blocked = collectDescendantIds(selected)
  const out: ParentOption[] = [{ value: '', label: '(Racine)' }]

  const walk = (nodes: SiteTreeNode[], depth: number) => {
    for (const n of nodes) {
      if (n.isVirtual) {
        continue
      }
      if (blocked.has(n.id)) continue
      const title = n.title?.trim() || n.slug
      const prefix = depth > 0 ? `${'· '.repeat(depth)}` : ''
      out.push({ value: n.id, label: `${prefix}${title} — ${n.slug}` })
      walk(n.children, depth + 1)
    }
  }

  walk(tree, 0)
  return out
}

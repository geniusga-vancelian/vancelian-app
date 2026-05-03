import type { PrimaryMenuItemForPageOrder, SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { primaryMenuItemContributesNavRootPageId } from '@/lib/cms/buildSiteTree'
import type { Locale } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'
import { computeNavActionButtonLabelCompleteness } from '@/lib/admin/pageLocaleCompleteness'

/** Données menu primaire suffisantes pour les pastilles « libellé barre nav » sur les racines de l’arbre. */
export type PrimaryMenuItemForNavLinkStrip = PrimaryMenuItemForPageOrder & {
  id: string
  label: string | null
  order: number
  i18n: Array<{ locale: string; label: string; translationStatus: string }>
}

/**
 * Sur les seules racines de l’arbre admin : rattache le premier `MenuItem` (par `order`) qui cible chaque page
 * comme entrée de navigation niveau 1, avec complétude i18n des libellés.
 */
export function attachRootMenuNavLinkCompleteness(
  roots: SiteTreeNode[],
  menuItems: PrimaryMenuItemForNavLinkStrip[],
  homePageId: string | null,
): SiteTreeNode[] {
  const context = { homePageId }
  const sorted = [...menuItems].sort((a, b) => a.order - b.order)
  const byPageId = new Map<string, PrimaryMenuItemForNavLinkStrip>()
  for (const item of sorted) {
    const pid = primaryMenuItemContributesNavRootPageId(item, context)
    if (!pid) continue
    if (!byPageId.has(pid)) byPageId.set(pid, item)
  }

  return roots.map((node) => {
    if (node.isVirtual) return node
    const mi = byPageId.get(node.id)
    if (!mi) return node
    return {
      ...node,
      menuNavLink: {
        menuItemId: mi.id,
        labelCompleteness: computeNavActionButtonLabelCompleteness(mi.label || '', [
          ...(mi.i18n ?? []).map((r) => ({
            locale: r.locale,
            label: r.label,
            translationStatus: String(r.translationStatus),
          })),
        ]),
      },
    }
  })
}

export function attachLocaleCompletenessToTree(
  nodes: SiteTreeNode[],
  byPageId: Map<string, Record<Locale, LocaleCompletenessLevel>>,
): SiteTreeNode[] {
  return nodes.map((node) => ({
    ...node,
    localeCompleteness: byPageId.get(node.id),
    children: attachLocaleCompletenessToTree(node.children, byPageId),
  }))
}

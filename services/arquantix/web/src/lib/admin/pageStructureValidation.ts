import type { PageRole } from '@prisma/client'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'

/** Remontée depuis `newParentId` : si on rencontre `pageId`, le parent serait un descendant de la page → cycle. */
export function newParentWouldCreateCycle(
  pageId: string,
  newParentId: string,
  parentById: Map<string, string | null>,
): boolean {
  let cur: string | null = newParentId
  const seen = new Set<string>()
  while (cur) {
    if (cur === pageId) return true
    if (seen.has(cur)) break
    seen.add(cur)
    cur = parentById.get(cur) ?? null
  }
  return false
}

/** Pages qui doivent rester à la racine (contrainte éditoriale conservative). */
export function mustStayStructuralRoot(page: {
  slug: string
  pageRole: PageRole
}): boolean {
  return (
    page.slug === 'home' ||
    page.slug === 'projects' ||
    page.pageRole === 'HOME' ||
    page.pageRole === 'PROJECTS_HUB'
  )
}

export function parentCannotBeVaultTemplate(parentTemplate: string | null | undefined): boolean {
  return parentTemplate === VAULT_BUILDER_TEMPLATE
}

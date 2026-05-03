import type { CommonModulesDocument } from '@/lib/cms/commonModulesStorage'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'

/**
 * Types catalogue considérés comme « Hero » : une page ne peut en porter qu’un seul au total
 * (y compris via module commun `common_module_ref`).
 */
export const HERO_CANONICAL_TYPE_KEYS = new Set([
  'hero',
  'hero_secondary',
  'blog_hero',
  /** Bandeau + corps article — occupe le même « slot » visuel qu’un hero (un seul par page). */
  'blog_article_reader',
  'blog_article_hero',
  'figma_simple_hero',
  'help_hero_v1',
])

/** Message affiché admin (toast / 409) lorsqu’un second hero est refusé. */
export const HERO_SLOT_ALREADY_USED_MESSAGE_FR =
  'Cette page comporte déjà un module Hero (en-tête principal). Une seule zone Hero est autorisée par page : retirez ou remplacez le bloc existant avant d’en ajouter un autre.'

export function isHeroSectionCanonicalKey(canonical: string | null | undefined): boolean {
  if (!canonical) return false
  return HERO_CANONICAL_TYPE_KEYS.has(canonical)
}

/** Groupe d’affichage catalogue « Ajouter un module » : Hero vs reste du contenu. */
export type CatalogLayoutGroupId = 'hero' | 'content'

export function getCatalogLayoutGroupForTypeKey(typeKey: string): CatalogLayoutGroupId {
  const c = resolveCanonicalSectionKey(typeKey) ?? typeKey
  return isHeroSectionCanonicalKey(c) ? 'hero' : 'content'
}

export function commonModuleIdToSectionKeyMap(doc: CommonModulesDocument): Map<string, string> {
  const m = new Map<string, string>()
  for (const mod of doc.modules) {
    m.set(mod.id, mod.sectionKey)
  }
  return m
}

/**
 * La ligne d’instance `Section` est-elle un hero (type direct ou ref commune vers un type hero) ?
 */
export function sectionRowUsesHeroSlot(
  sectionKey: string,
  contentData: unknown,
  idToSectionKey: Map<string, string>,
): boolean {
  const canonical = resolveCanonicalSectionKey(sectionKey) ?? sectionKey
  if (canonical === 'common_module_ref') {
    const raw = contentData as Record<string, unknown> | null | undefined
    const id = typeof raw?.commonModuleId === 'string' ? raw.commonModuleId.trim() : ''
    if (!id) return false
    const targetKey = idToSectionKey.get(id)
    if (!targetKey) return false
    const c2 = resolveCanonicalSectionKey(targetKey) ?? targetKey
    return isHeroSectionCanonicalKey(c2)
  }
  return isHeroSectionCanonicalKey(canonical)
}

export function pageHasAnyHeroSection(
  sections: { key: string; contents?: { data: unknown }[] }[],
  doc: CommonModulesDocument,
): boolean {
  const idToKey = commonModuleIdToSectionKeyMap(doc)
  for (const s of sections) {
    const data = s.contents?.[0]?.data
    if (sectionRowUsesHeroSlot(s.key, data, idToKey)) return true
  }
  return false
}

/** Type ou module commun ajouté : occupe-t-il le slot hero ? */
export function additionUsesHeroSlot(
  typeKey: string,
  doc: CommonModulesDocument,
  commonModuleId?: string | null,
): boolean {
  if (typeKey === 'common_module_ref') {
    const mid = commonModuleId?.trim()
    if (!mid) return false
    const entry = doc.modules.find((m) => m.id === mid)
    if (!entry) return false
    const c = resolveCanonicalSectionKey(entry.sectionKey) ?? entry.sectionKey
    return isHeroSectionCanonicalKey(c)
  }
  const c = resolveCanonicalSectionKey(typeKey) ?? typeKey
  return isHeroSectionCanonicalKey(c)
}

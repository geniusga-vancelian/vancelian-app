import { VAULT_SECTION_KEY } from '@/lib/catalog/packagedCatalogHelpers'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'

/**
 * Page Vault Builder : première section = `vault_builder_v1` avec image header (média back-office) ou image TitlePage.
 * Même comportement barre nav que hero_secondary + image.
 */
export function shouldUseVaultBuilderHeroOverlay(
  sections: { key: string; data?: Record<string, unknown> }[] | undefined | null,
): boolean {
  const first = sections?.[0]
  if (!first || first.key !== VAULT_SECTION_KEY) return false
  const data = first.data
  if (!data || typeof data !== 'object') return false
  const d = data as Record<string, unknown>
  const headerId = typeof d.headerMediaId === 'string' ? d.headerMediaId.trim() : ''
  if (headerId.length > 0) return true
  const modules = Array.isArray(d.modules) ? d.modules : []
  const tp = modules.find(
    (m: unknown) =>
      m != null &&
      typeof m === 'object' &&
      (m as Record<string, unknown>).type === 'TitlePage',
  ) as Record<string, unknown> | undefined
  const content = tp?.content as Record<string, unknown> | undefined
  const imageUrl = content && typeof content.imageUrl === 'string' ? content.imageUrl.trim() : ''
  return imageUrl.length > 0
}

/**
 * Première section = Hero Secondary → nav transparente au-dessus du fond hero.
 */
export function isFirstSectionHeroSecondary(
  sections: { key: string }[] | undefined | null,
): boolean {
  return sections?.[0]?.key === 'hero_secondary'
}

/**
 * Image de fond CMS résolue (`backgroundMediaUrl` après `getPageSections`).
 * Sans image : nav pleine « light » (fond blanc, actif noir / inactifs gris).
 */
export function heroSecondaryHasBackgroundImage(
  sections: { key: string; data?: Record<string, unknown> }[] | undefined | null,
): boolean {
  const first = sections?.[0]
  if (!first || first.key !== 'hero_secondary') return false
  const url =
    typeof first.data?.backgroundMediaUrl === 'string'
      ? first.data.backgroundMediaUrl.trim()
      : ''
  return url.length > 0
}

/** Nav transparente + thème « dark » au scroll (tant que le hero image est sous la barre). */
export function shouldUseHeroSecondaryImageOverlay(
  sections: { key: string; data?: Record<string, unknown> }[] | undefined | null,
): boolean {
  return (
    (isFirstSectionHeroSecondary(sections) && heroSecondaryHasBackgroundImage(sections)) ||
    shouldUseVaultBuilderHeroOverlay(sections)
  )
}

export function isFirstSectionHero(
  sections: { key: string }[] | undefined | null,
): boolean {
  return sections?.[0]?.key === 'hero'
}

/**
 * Première section = hero (homepage) avec image CMS → nav transparente, **liens en light**,
 * même transition blur / givré qu’au hero-secondary au scroll.
 */
export function heroHomeHasBackgroundImage(
  sections: { key: string; data?: Record<string, unknown> }[] | undefined | null,
): boolean {
  const first = sections?.[0]
  if (!first || first.key !== 'hero') return false
  const url =
    typeof first.data?.backgroundMediaUrl === 'string'
      ? first.data.backgroundMediaUrl.trim()
      : ''
  return url.length > 0
}

export function shouldUseHeroHomeImageOverlayLight(
  sections: { key: string; data?: Record<string, unknown> }[] | undefined | null,
): boolean {
  return isFirstSectionHero(sections) && heroHomeHasBackgroundImage(sections)
}

/**
 * Page blog (template CMS) : premier bloc = `blog_hero` → bandeau sous le menu primaire
 * (fond neutre, pas photo) comme le hero secondary avec image.
 */
export function shouldUseBlogHeroUnderNav(
  sections: { key: string }[] | undefined | null,
): boolean {
  const first = sections?.[0]
  if (!first) return false
  const c = resolveCanonicalSectionKey(first.key) ?? first.key
  return c === 'blog_hero' || c === 'blog_article_hero'
}

/**
 * Gabarit article : premier bloc = lecteur → même logique nav que `blog_hero` (fond neutre sous le menu).
 */
export function shouldUseArticleReaderHeroUnderNav(
  sections: { key: string }[] | undefined | null,
): boolean {
  const first = sections?.[0]
  if (!first) return false
  const c = resolveCanonicalSectionKey(first.key) ?? first.key
  return c === 'blog_article_reader'
}

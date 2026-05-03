/**
 * Allowlist stricte — Vault Builder auto-translate (FR → en|it).
 * Seuls les chemins listés par type de module sont traduits ; tout le reste est préservé tel quel.
 */

/** Clés de contenu jamais traduites (identifiants, médias, navigation technique). */
export const VAULT_CONTENT_KEYS_NEVER_TRANSLATE = new Set([
  'id',
  'type',
  'enabled',
  'key',
  'displayMode',
  'size',
  'carousel',
  'showBullets',
  'visibleCardsCount',
  'cardAspectRatio',
  'heightSize',
  'imageAssetPath',
  'imageUrl',
  'redirectUrl',
  'videoUrl',
  'embedUrl',
  'posterMediaId',
  'posterImageUrl',
  'imageMediaIds',
  'documentMediaIds',
  'promoVideoUrl',
  'promoVideoUrls',
  'promoVideoMediaId',
  'articleSlug',
  'footerCollectionSlug',
  'footerCategorySlug',
  'infoLinkArticle',
  'ctaHref',
  'icon',
  'iconBackgroundColor',
  'category',
  'showInfoIcon',
  'colorHex',
  'percentage',
  'progressPct',
  'limit',
])

/** Heuristique : ne pas envoyer à OpenAI (URLs seules, UUID, nombre pur). */
export function shouldSkipPlainString(value: string): boolean {
  const s = value.trim()
  if (s.length === 0) return true
  if (/^https?:\/\//i.test(s)) return true
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s)) return true
  if (/^[+-]?[0-9]+([.,][0-9]+)?\s*%?$/.test(s) && s.length < 24) return true
  return false
}

import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { getLocaleOrDefault } from '@/config/locales'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { localizedExclusiveOfferDetailPath } from '@/lib/i18n/localizedExclusiveOfferPath'

function isArticleGabaritPage(node: SiteTreeNode): boolean {
  return node.slug === 'article' && node.template === 'article'
}

function isExclusiveOfferGabaritPage(node: SiteTreeNode): boolean {
  return node.slug === EXCLUSIVE_OFFER_GABARIT_SLUG && node.template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE
}

function isVaultStylePublicUrl(node: SiteTreeNode): boolean {
  if (node.template === VAULT_BUILDER_TEMPLATE) return true
  if (node.slug === 'home') return false
  const normalized = (node.urlPath || '').replace(/\/$/, '') || ''
  return normalized === `/projects/${node.slug}`
}

/**
 * URL publique indicative pour l’admin (Structure du site, aperçu).
 * Alignée sur le routing localisé : vault → `localizedExclusiveOfferDetailPath` ; home → `/{locale}` ; sinon `/{locale}{urlPath}`.
 * `locale` : prioriser la langue éditoriale (contexte admin) ; `getLocaleOrDefault` évite chaîne vide / invalide.
 */
export function siteStructurePublicUrl(
  node: SiteTreeNode,
  locale: string,
): string {
  const loc = getLocaleOrDefault(locale)

  if (node.isVirtual && node.articleId) {
    const slug = node.slug.replace(/^\/+|\/+$/g, '')
    return `/${loc}/blog/${slug}`
  }

  if (node.slug === 'home' || node.urlPath === '/') {
    return `/${loc}`
  }

  if (isArticleGabaritPage(node) || isExclusiveOfferGabaritPage(node)) {
    return `/${loc}/gabarit-preview/${node.slug}`
  }

  if (isVaultStylePublicUrl(node)) {
    return localizedExclusiveOfferDetailPath(loc, node.slug)
  }

  const path = node.urlPath.startsWith('/') ? node.urlPath : `/${node.urlPath}`
  return `/${loc}${path}`
}

export function cmsPagePreviewUrl(slug: string, locale: string): string {
  const loc = getLocaleOrDefault(locale)
  return `/preview/${encodeURIComponent(slug)}?locale=${encodeURIComponent(loc)}`
}

/**
 * URL d’aperçu admin (iframe CMS) — toujours sous `/preview/*`.
 *
 * Sur `console.*`, les URLs publiques `/{locale}` sont redirigées vers `/admin/pages` ;
 * l’iframe doit donc cibler les routes d’aperçu brouillon (auth admin), identiques en local et en prod.
 */
export function siteStructurePreviewUrl(
  node: SiteTreeNode,
  locale: string,
): string {
  const loc = getLocaleOrDefault(locale)
  const q = `locale=${encodeURIComponent(loc)}`

  if (node.isVirtual && node.articleId) {
    return `/preview/article/${encodeURIComponent(node.articleId)}?${q}`
  }

  return `/preview/${encodeURIComponent(node.slug)}?${q}`
}
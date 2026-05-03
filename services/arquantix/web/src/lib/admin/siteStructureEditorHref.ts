import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import type { Locale } from '@/config/locales'
import { PackagedProductType } from '@prisma/client'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'

function isArticleGabaritPage(node: SiteTreeNode): boolean {
  return node.slug === 'article' && node.template === 'article'
}

function isExclusiveOfferGabaritPage(node: SiteTreeNode): boolean {
  return node.slug === EXCLUSIVE_OFFER_GABARIT_SLUG && node.template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE
}

function isVaultStyleProjectsPage(node: SiteTreeNode): boolean {
  if (node.slug === 'home') return false
  const normalized = (node.urlPath || '').replace(/\/$/, '') || ''
  return normalized === `/projects/${node.slug}`
}

/**
 * URL d’édition CMS pour un nœud de l’arborescence « Structure du site »
 * (pages, gabarits, vaults, articles blog injectés).
 */
export function siteStructureEditorHref(node: SiteTreeNode, editingLocale: Locale): string | null {
  if (node.isVirtual && node.articleId) {
    return `/admin/articles/${encodeURIComponent(node.articleId)}`
  }

  if (isArticleGabaritPage(node) || isExclusiveOfferGabaritPage(node)) {
    return `/admin/pages/${encodeURIComponent(node.slug)}?editingLocale=${encodeURIComponent(editingLocale)}`
  }

  if (node.template === VAULT_BUILDER_TEMPLATE || isVaultStyleProjectsPage(node)) {
    const q = new URLSearchParams({ slug: node.slug })
    if (node.packagedProduct?.productType === PackagedProductType.EXCLUSIVE_OFFER) {
      q.set('eo', '1')
    }
    return `/admin/vault-builder?${q.toString()}`
  }

  return `/admin/pages/${encodeURIComponent(node.slug)}?editingLocale=${encodeURIComponent(editingLocale)}`
}

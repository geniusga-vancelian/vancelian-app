/**
 * Registre des types de modules Vault Builder (admin) vs rendu web explicite.
 * Source admin : `MODULE_CATALOG` dans `app/admin/vault-builder/page.tsx`.
 * Rendu web : switch de `components/exclusive-offer/VaultModuleWeb.tsx`.
 */

/** Types présents dans le catalogue admin (add-module). */
export const VAULT_MODULE_TYPES_ADMIN = new Set<string>([
  'TitlePage',
  'TagsModule',
  'FundingModule',
  'SimpleMarkdownContentModule',
  'CompetitiveAdvantagesModule',
  'FaqAccordionModule',
  'ContentBasDePageSansModuleBlanc',
  'MarktingCardLargePortrait',
  'MarketingCardsSmallCarouselModule',
  'MarketingCardsSmallSlidingCarrousel_Portrait',
  'MarketingCardsSmallSlidingCarrousel_Paysage',
  'TransactionLatest10Module',
  'BlogALaUne',
  'AllocationModule',
  'KeyInformationModule',
  'MediaImageCarouselModule',
  'DocumentsListModule',
  'PerformanceChart',
  'StepsModule',
  'VideoBlockArticleModule',
  'LocalisationModule',
  'VirtualVisualizationModule',
])

/**
 * Types avec une branche dédiée dans `VaultModuleWeb` (hors `default`).
 * Le `default` affiche encore un placeholder — ces types sont les « vrais » blocs métier web.
 */
export const VAULT_MODULE_TYPES_WEB_EXPLICIT = new Set<string>([
  'TitlePage',
  'VideoBlockArticleModule',
  'LocalisationModule',
  'VirtualVisualizationModule',
  'MediaImageCarouselModule',
  'DocumentsListModule',
  'SimpleMarkdownContentModule',
  'FundingModule',
  'TagsModule',
  'CompetitiveAdvantagesModule',
  'KeyInformationModule',
  'StepsModule',
  'FaqAccordionModule',
  'ContentBasDePageSansModuleBlanc',
])

export function isAdminRegisteredVaultModuleType(type: string): boolean {
  return VAULT_MODULE_TYPES_ADMIN.has(type)
}

export function hasWebExplicitRenderer(type: string): boolean {
  return VAULT_MODULE_TYPES_WEB_EXPLICIT.has(type)
}

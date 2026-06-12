/**
 * Mapping Vault Builder → design system portail (Webapp4).
 * Référence : `PortalVaultModuleWeb` + `PortalVaultExtendedModules`.
 */

export { PORTAL_NATIVE_VAULT_MODULE_TYPES, usesPortalVaultRenderer } from '@/components/portal/invest/vault/PortalVaultModuleWeb'

/** Couverture complète des 27 types Vault Builder côté portail. */
export const PORTAL_VAULT_MODULE_MAP = {
  TitlePage: { portal: 'hero (payload)', ds: 'dh-article' },
  TagsModule: { portal: 'hero chips (payload)', ds: 'dh-article__chip' },
  KeyInformationModule: { portal: 'PortalVaultKeyInformation', ds: 'stats stats--lined' },
  FundingModule: { portal: 'PortalVaultFunding', ds: 'funding' },
  CompetitiveAdvantagesModule: { portal: 'PortalVaultCompetitiveAdvantages', ds: 'pillars' },
  StepsModule: { portal: 'PortalVaultSteps', ds: 'stepper' },
  FaqAccordionModule: { portal: 'PortalVaultFaq', ds: 'faq' },
  DocumentsListModule: { portal: 'PortalVaultDocuments', ds: 'docs .row' },
  LocalisationModule: { portal: 'PortalVaultLocalisation', ds: 'map-card' },
  SimpleMarkdownContentModule: { portal: 'PortalVaultMarkdown', ds: 'overview / ofd-narrative / ai-tip' },
  PARAGRAPH: { portal: 'PortalVaultParagraph', ds: 'overview__body' },
  HEADING: { portal: 'PortalVaultHeading', ds: 'ofd-section__title' },
  ContentBasDePageSansModuleBlanc: { portal: 'PortalVaultLegalFooter', ds: 'ofd-narrative__prose' },
  BlogALaUne: { portal: 'PortalVaultBlogALaUne', ds: 'AppNewsDeck + AppActuCard/Flash' },
  MediaImageCarouselModule: {
    portal: 'PortalVaultMediaCarousel (+ photos hero si 1er carrousel)',
    ds: 'gallery rounded 16px',
  },
  AllocationModule: { portal: 'PortalVaultAllocation', ds: 'AppPortfolioAllocationDonut' },
  PerformanceChart: { portal: 'PortalVaultPerformanceChart', ds: 'cfd-perf + PortalPerformanceChart' },
  TransactionLatest10Module: { portal: 'PortalVaultTransactions', ds: 'AppDataList + AppDataRow' },
  MarktingCardLargePortrait: { portal: 'PortalVaultMarketingLargePortrait', ds: 'AppCard portrait' },
  MarketingCardsSmallCarouselModule: { portal: 'PortalVaultMarketingCards', ds: 'AppCard grid' },
  MarketingCardsSmallSlidingCarrousel_Portrait: {
    portal: 'PortalVaultMarketingCards (portrait)',
    ds: 'AppCard grid',
  },
  MarketingCardsSmallSlidingCarrousel_Paysage: { portal: 'PortalVaultMarketingCards', ds: 'AppCard grid' },
  VideoBlockArticleModule: { portal: 'PortalVaultVideos', ds: 'AppCard + iframe YouTube' },
  VirtualVisualizationModule: { portal: 'PortalVaultVirtualVisualization', ds: 'map-card iframe' },
  QUOTE: { portal: 'PortalVaultQuote', ds: 'blockquote overview' },
  BULLET_LIST: { portal: 'PortalVaultBulletList', ds: 'overview list-disc' },
  NUMBERED_LIST: { portal: 'PortalVaultNumberedList', ds: 'overview list-decimal' },
} as const

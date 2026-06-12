/**
 * Mapping Article Builder (CMS) → design system portail article (`art-*`).
 * Référence handoff : `Article.html` · `article-view.js` (Webapp7).
 * Rendu : `PortalArticleBlockStream`.
 */

export const PORTAL_ARTICLE_MODULE_MAP = {
  HEADING: { portal: 'PortalArticleHeading', ds: 'art-prose__h2' },
  PARAGRAPH: { portal: 'PortalArticleParagraph', ds: 'art-prose__p' },
  QUOTE: { portal: 'PortalArticleQuote', ds: 'art-prose__quote' },
  BULLET_LIST: { portal: 'PortalArticleBulletList', ds: 'art-prose__check' },
  NUMBERED_LIST: { portal: 'PortalArticleNumberedList', ds: 'art-prose__ol' },
  IMAGE: { portal: 'PortalArticleImage', ds: 'art-prose__grid-cell' },
  VIDEO: { portal: 'PortalArticleVideo', ds: 'art-prose__video' },
  DOCUMENT: { portal: 'PortalArticleDocument', ds: 'docs .row' },
  MEDIA_IMAGE_CAROUSEL: {
    portal: 'PortalArticleMediaCarousel',
    ds: 'carousel carousel--gallery (PortalDsImageCarousel)',
  },
  LOCALISATION: { portal: 'PortalArticleLocalisation', ds: 'map-card' },
  DOCUMENTS_LIST: { portal: 'PortalArticleDocumentsList', ds: 'docs .row' },
  KEY_INFORMATION: { portal: 'PortalArticleKeyInformation', ds: 'stats stats--lined' },
  VIDEO_BLOCK_ARTICLE: {
    portal: 'PortalArticleVideoBlock',
    ds: 'art-prose__video + AppCard (poster + iframe)',
  },
  STEPS_MODULE: { portal: 'PortalArticleSteps', ds: 'stepper' },
  HOW_IT_WORKS_CAROUSEL: {
    portal: 'PortalArticleHowItWorks',
    ds: 'art-prose__h2 + art-prose__ol + art-prose__grid',
  },
} as const

export type PortalArticleModuleType = keyof typeof PORTAL_ARTICLE_MODULE_MAP

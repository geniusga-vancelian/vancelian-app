import { ArticleBlockType, ContentStatus, TranslationStatus } from '@prisma/client'
import type { Locale } from '@/config/locales'
import type { PublicArticle } from '@/lib/blog/getPublicArticle'

const DEMO_COPY: Record<
  Locale,
  { title: string; standfirst: string; h1: string; h2: string; h3: string; p1: string; p2: string }
> = {
  fr: {
    title: 'Article de démonstration (aperçu catalogue)',
    standfirst:
      'En-tête fictif pour prévisualiser le module « Article (lecture) » avec menu primaire et fond gris sous la barre.',
    h1: 'Contexte',
    h2: 'Points clés',
    h3: 'Pour aller plus loin',
    p1:
      'Ce contenu est généré uniquement pour l’aperçu admin. Il n’existe pas en base et ne doit pas être publié tel quel.',
    p2: 'Le corps sert à valider le sommaire, la mise en page et la transition de la navigation au défilement.',
  },
  en: {
    title: 'Demo article (catalog preview)',
    standfirst:
      'Fictional header to preview the article reader module with primary nav and gray band under the bar.',
    h1: 'Context',
    h2: 'Key points',
    h3: 'Next steps',
    p1:
      'This copy exists only for the admin preview. It is not stored in the database and must not be published as-is.',
    p2: 'The body validates the table of contents, layout, and nav blend on scroll.',
  },
  it: {
    title: 'Articolo dimostrativo (anteprima catalogo)',
    standfirst:
      'Intestazione fittizia per anteprima del modulo lettura articolo con menu primario e fascia grigia sotto la barra.',
    h1: 'Contesto',
    h2: 'Punti chiave',
    h3: 'Approfondimenti',
    p1:
      'Questo testo è solo per l’anteprima admin. Non è nel database e non va pubblicato così com’è.',
    p2: 'Il corpo serve a validare indice, impaginazione e transizione della barra di navigazione.',
  },
}

/**
 * Article minimal pour l’aperçu `/preview/section-demo/blog_article_reader` (sans requête Prisma).
 */
export function buildDemoPublicArticleForSectionPreview(locale: Locale): PublicArticle {
  const c = DEMO_COPY[locale] ?? DEMO_COPY.fr
  const now = new Date()
  const articleId = 'demo-section-blog-article-reader'

  return {
    id: articleId,
    slug: 'demo-article-reader-preview',
    status: ContentStatus.PUBLISHED,
    createdAt: now,
    updatedAt: now,
    publishedAt: now,
    authorName: 'Arquantix',
    authorRole: 'Rédaction',
    articleType: 'NEWS',
    isCompanyNews: false,
    categorySlugs: [],
    /** Visuel stable pour l’aperçu admin (catalogue / add-module). */
    coverUrl: 'https://picsum.photos/seed/arquantix-hero-article/1440/960',
    galleryUrls: [],
    documents: [],
    blocks: [
      {
        id: 'demo-b0',
        type: ArticleBlockType.HEADING,
        order: 0,
        data: { text: c.h1 },
      },
      {
        id: 'demo-b1',
        type: ArticleBlockType.PARAGRAPH,
        order: 1,
        data: { text: c.p1 },
      },
      {
        id: 'demo-b2',
        type: ArticleBlockType.HEADING,
        order: 2,
        data: { text: c.h2 },
      },
      {
        id: 'demo-b3',
        type: ArticleBlockType.PARAGRAPH,
        order: 3,
        data: { text: c.p2 },
      },
      {
        id: 'demo-b4',
        type: ArticleBlockType.HEADING,
        order: 4,
        data: { text: c.h3 },
      },
    ],
    projects: [],
    categories: [],
    locale,
    i18n: {
      id: 'demo-i18n',
      articleId,
      locale,
      title: c.title,
      standfirst: c.standfirst,
      metaTitle: null,
      metaDescription: null,
      coverTitle: null,
      createdAt: now,
      updatedAt: now,
      translationStatus: TranslationStatus.ORIGINAL,
    },
  } as unknown as PublicArticle
}

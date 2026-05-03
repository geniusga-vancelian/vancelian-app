/**
 * Catalogue des « types de contenu » applicatifs portés par le modèle
 * `Article` (colonne SQL `article_type`, pas un enum Prisma — initialement
 * créée via `ensureArticleTypeColumn`). Cette liste est la source de vérité
 * partagée par l'admin (filtre, création) et l'API (validation, normalisation
 * du GET).
 *
 * Phase 1 (Lot 1.1) : NEWS, ANALYSIS, RESEARCH, ACADEMY, USER_BLOG sont portés
 * par `Article`.
 * Phase 3 (Lot 3.3) : HELP est ajouté. Un article HELP doit toujours être
 * rattaché à une `HelpCollection` (via `Article.helpCollectionId`) et une
 * `HelpCategory` (via `Article.helpCategoryId`), avec un `helpSlug` (slug
 * d'origine côté hiérarchie Help, distinct du `slug` global). L'URL publique
 * reste `/help/[collection]/[category]/[helpSlug]`.
 * Pendant la transition, les `HelpArticle` non encore migrés restent lus en
 * fallback côté public (cf. `getHelpArticle` dans `lib/help/get-help-data.ts`).
 */

export const ARTICLE_TYPE_KEYS = [
  'NEWS',
  'ANALYSIS',
  'RESEARCH',
  'ACADEMY',
  'USER_BLOG',
  'HELP',
] as const

export type ArticleTypeKey = (typeof ARTICLE_TYPE_KEYS)[number]

export interface ArticleTypeDescriptor {
  key: ArticleTypeKey
  /** Libellé court affiché dans les badges et boutons. */
  label: string
  /** Libellé long pour le menu de création (« Nouvelle Analyse », etc.). */
  createLabel: string
  /** Préfixe de slug auto-généré à la création. */
  slugPrefix: string
  /** Classes Tailwind du badge (background + texte). */
  badgeClassName: string
  /** Description courte pour le menu de sélection. */
  description: string
}

export const ARTICLE_TYPES: Record<ArticleTypeKey, ArticleTypeDescriptor> = {
  NEWS: {
    key: 'NEWS',
    label: 'News',
    createLabel: 'Nouvelle News',
    slugPrefix: 'news',
    badgeClassName: 'bg-sky-100 text-sky-800',
    description: 'Article éditorial pour le blog public.',
  },
  ANALYSIS: {
    key: 'ANALYSIS',
    label: 'Analysis',
    createLabel: 'Nouvelle Analysis',
    slugPrefix: 'analysis',
    badgeClassName: 'bg-purple-100 text-purple-800',
    description: 'Analyse de marché ou décryptage approfondi.',
  },
  RESEARCH: {
    key: 'RESEARCH',
    label: 'Research',
    createLabel: 'Nouvelle Research',
    slugPrefix: 'research',
    badgeClassName: 'bg-emerald-100 text-emerald-800',
    description: 'Note de recherche financière (publication produit).',
  },
  ACADEMY: {
    key: 'ACADEMY',
    label: 'Academy',
    createLabel: 'Nouvel article Academy',
    slugPrefix: 'academy',
    badgeClassName: 'bg-amber-100 text-amber-800',
    description:
      'Contenu pédagogique rattaché à une collection + catégorie Academy (hiérarchie pédagogique).',
  },
  USER_BLOG: {
    key: 'USER_BLOG',
    label: 'User Blog',
    createLabel: 'Nouveau User Blog',
    slugPrefix: 'user-blog',
    badgeClassName: 'bg-pink-100 text-pink-800',
    description: 'Article de blog tenu par un client (futur, social in-app).',
  },
  HELP: {
    key: 'HELP',
    label: 'Help / FAQ',
    createLabel: 'Nouvel article Help',
    slugPrefix: 'help',
    badgeClassName: 'bg-indigo-100 text-indigo-800',
    description:
      "Article d'aide / FAQ rattaché à une collection + catégorie (hiérarchie Help conservée).",
  },
}

/**
 * Normalise une chaîne potentiellement inconnue (legacy DB, payload externe)
 * vers un `ArticleTypeKey` valide. Fallback : `NEWS`.
 */
export function normalizeArticleType(raw: unknown): ArticleTypeKey {
  if (typeof raw !== 'string') return 'NEWS'
  const upper = raw.trim().toUpperCase()
  return (ARTICLE_TYPE_KEYS as readonly string[]).includes(upper)
    ? (upper as ArticleTypeKey)
    : 'NEWS'
}

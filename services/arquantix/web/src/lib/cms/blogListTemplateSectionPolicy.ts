/**
 * Politique des modules sur la **page liste blog** (template CMS `blog`, slug `blog`).
 *
 * `BlogTemplatePageView` ne rend que ces clés canoniques. Tout autre bloc présent
 * en base (ou résolu depuis un module commun) est ignoré côté public — d’où le
 * même filtre côté admin à l’ajout pour éviter les « modules fantômes ».
 *
 * ## `blog_category_nav` (retiré)
 *
 * Le type catalogue est `deprecated`. Il n’était plus proposé à l’ajout via le
 * catalogue (filtre `deprecated`), mais pouvait encore être rendu s’il existait
 * en base ou dans d’anciens scripts d’init. Il est **exclu** de cette liste :
 * les instances résiduelles ne s’affichent plus sur la liste blog. Pour un filtre
 * par catégorie, s’appuyer sur les URLs / paramètres de requête (`category`, …)
 * et les composants blog existants (mosaïque, flux), pas sur ce module.
 */

/** Clés canoniques effectivement rendues sur `/blog` (template CMS). */
export const BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS = new Set<string>([
  'blog_hero',
  'blog_mosaic',
  'blog_feed',
  'cta',
])

/** Sous-ensemble : largeur pleine (pas de `max-w-7xl` sur l’enveloppe). */
export const BLOG_LIST_TEMPLATE_FULL_BLEED_CANONICAL_KEYS = new Set<string>(['cta'])

/**
 * Premier bloc de la page : `blog_hero` ou en-tête article CMS sous le menu primaire.
 */
export function blogListTemplateFirstSectionBleedsUnderNav(
  firstCanonical: string | null,
): boolean {
  return firstCanonical === 'blog_hero' || firstCanonical === 'blog_article_hero'
}

/**
 * Bandeau blog sous la nav fixe (fond pleine largeur jusqu’au haut du viewport) :
 * même compensation que le hero secondary avec image et que `BlogFeaturedModule`.
 *
 * À combiner sur le conteneur racine du module (pas de `pt-20` parent — voir ArticleReadingLayout).
 */
export const CMS_BLOG_HERO_BLEED_UNDER_NAV_SECTION_CLASSNAME =
  '-mt-14 pt-[calc(128px+30px+3.5rem)] md:-mt-[60px] md:pt-[calc(128px+30px+60px)]' as const

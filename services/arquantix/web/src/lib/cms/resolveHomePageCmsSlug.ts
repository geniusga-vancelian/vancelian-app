/**
 * Choisit quel `pages.slug` alimente la route `/` (sections CMS).
 *
 * Priorité :
 * 1. `ARQUANTIX_HOME_CMS_SLUG` si défini (override explicite, ex. staging).
 * 2. Sinon toujours `home` (page racine, `urlPath` `/`).
 */
export async function resolveHomePageCmsSlug(): Promise<string> {
  const env = process.env.ARQUANTIX_HOME_CMS_SLUG?.trim()
  if (env && env.length > 0) {
    return env
  }
  return 'home'
}

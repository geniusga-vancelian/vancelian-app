/**
 * Override serveur uniquement : force le slug Prisma des sections pour `/`.
 * Sinon voir `resolveHomePageCmsSlug` (défaut : slug `home`).
 */
export function getHomePageCmsSlugFromEnv(): string | null {
  const raw = process.env.ARQUANTIX_HOME_CMS_SLUG?.trim()
  return raw && raw.length > 0 ? raw : null
}

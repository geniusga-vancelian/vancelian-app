import { ContentStatus } from '@prisma/client'
import { getLocaleOrDefault, type Locale } from '@/config/locales'
import {
  getExclusiveOfferCardsByPackagedProductIds,
  getExclusiveOfferCardsNewestFirst,
} from '@/lib/cms/exclusiveOfferGallery'
import { getProjectsByIds, type ProjectShrink } from '@/lib/cms/projects'
import type { SectionWithContent } from '@/lib/cms/content'
import { injectMediaUrls } from '@/lib/cms/content'
import { extractMediaIds, resolveMediaMap, rewriteMediaUrlsToSiteProxyDeep } from '@/lib/storage/media'
import { getSectionType, resolveCanonicalSectionKey } from '@/lib/sections/library'
import { hasSectionComponent } from '@/lib/sections/registry'
import { applySectionDemoEnrichment } from '@/lib/cms/sectionDemoEnrichment'
import { buildDemoPublicArticleForSectionPreview } from '@/lib/cms/demoPublicArticle'

const FORBIDDEN_DEMO_KEYS = new Set(['common_module_ref', 'footer'])

/**
 * Aperçu catalogue : une section synthétique à partir des `defaultData` du type,
 * avec résolution médias et cartes projet comme sur `getPageSections`.
 */
export async function getSectionTypeDemoSection(
  sectionKeyParam: string,
  locale: string,
): Promise<SectionWithContent | null> {
  const raw = decodeURIComponent(sectionKeyParam).trim()
  if (!raw || FORBIDDEN_DEMO_KEYS.has(raw)) return null

  const st = getSectionType(raw)
  if (!st) return null

  const renderKeyProbe = resolveCanonicalSectionKey(st.key) ?? st.key
  if (!hasSectionComponent(renderKeyProbe) && !hasSectionComponent(st.key)) return null

  const loc = getLocaleOrDefault(locale) as Locale
  let effectiveKey = resolveCanonicalSectionKey(raw) ?? st.key
  if (effectiveKey === 'projects') effectiveKey = 'project_grid'

  const effectiveData = JSON.parse(JSON.stringify(st.defaultData ?? {})) as Record<string, unknown>
  applySectionDemoEnrichment(effectiveKey, effectiveData, loc)

  const mediaIds = extractMediaIds(effectiveData as object)
  const mediaMap = await resolveMediaMap(mediaIds)
  let resolvedData = injectMediaUrls(effectiveData as object, mediaMap) as Record<string, unknown>
  resolvedData = rewriteMediaUrlsToSiteProxyDeep(resolvedData) as Record<string, unknown>

  if ((effectiveKey === 'projects' || effectiveKey === 'project_grid') && resolvedData) {
    const rawLimit = resolvedData.limit
    const limit =
      typeof rawLimit === 'number' && Number.isFinite(rawLimit) && rawLimit > 0
        ? Math.min(20, Math.floor(rawLimit))
        : undefined
    const showAllExclusiveOffers = resolvedData.showAllExclusiveOffers === true
    const effectiveLimitForAll = limit ?? 3

    const selectedPackagedProductIds = resolvedData.selectedPackagedProductIds as string[] | undefined
    const selectedProjectIds = resolvedData.selectedProjectIds as string[] | undefined

    const packagedIds =
      selectedPackagedProductIds && selectedPackagedProductIds.length > 0
        ? limit
          ? selectedPackagedProductIds.slice(0, limit)
          : selectedPackagedProductIds
        : undefined
    const legacyProjectIds =
      selectedProjectIds && selectedProjectIds.length > 0
        ? limit
          ? selectedProjectIds.slice(0, limit)
          : selectedProjectIds
        : undefined

    let resolvedProjects: ProjectShrink[] = []

    if (showAllExclusiveOffers) {
      resolvedProjects = await getExclusiveOfferCardsNewestFirst(loc, effectiveLimitForAll)
    } else if (packagedIds && packagedIds.length > 0) {
      resolvedProjects = await getExclusiveOfferCardsByPackagedProductIds(packagedIds, loc)
    } else if (legacyProjectIds && legacyProjectIds.length > 0) {
      resolvedProjects = await getProjectsByIds(legacyProjectIds, loc)
    } else {
      /** Aperçu : montrer quelques cartes réelles si la config par défaut ne cible rien. */
      resolvedProjects = await getExclusiveOfferCardsNewestFirst(loc, Math.min(3, effectiveLimitForAll))
    }

    resolvedData = {
      ...resolvedData,
      resolvedProjects,
    }
  }

  if (effectiveKey === 'blog_article_reader') {
    resolvedData = {
      ...resolvedData,
      __demoBlogArticle: buildDemoPublicArticleForSectionPreview(loc),
    }
  }

  return {
    id: `demo-section-type:${effectiveKey}`,
    key: effectiveKey,
    order: 0,
    schemaVersion: st.schemaVersion,
    data: resolvedData,
    locale: loc,
    status: ContentStatus.DRAFT,
  }
}

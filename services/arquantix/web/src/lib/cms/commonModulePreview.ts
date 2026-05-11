import { ContentStatus } from '@prisma/client'
import { getLocaleOrDefault, type Locale } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import { extractMediaIds, resolveMediaMap, rewriteMediaUrlsToSiteProxyDeep } from '@/lib/storage/media'
import {
  getCommonModuleById,
  normalizeCommonModuleEntry,
  parseCommonModulesDocument,
  resolveCommonModuleDataForLocale,
} from '@/lib/cms/commonModulesStorage'
import { injectMediaUrls } from '@/lib/cms/content'
import { getSectionType, resolveCanonicalSectionKey } from '@/lib/sections/library'
import type { SectionWithContent } from '@/lib/cms/content'
import {
  getExclusiveOfferCardsByPackagedProductIds,
  getExclusiveOfferCardsNewestFirst,
} from '@/lib/cms/exclusiveOfferGallery'
import { readShowAllExclusiveOffersFlag } from '@/lib/cms/showAllExclusiveOffersFlag'
import { getProjectsByIds, type ProjectShrink } from '@/lib/cms/projects'

/**
 * Section résolue pour l’iframe d’aperçu admin (un seul bloc, médias injectés).
 */
export async function getCommonModulePreviewSection(
  moduleId: string,
  locale: string,
): Promise<SectionWithContent | null> {
  const loc = getLocaleOrDefault(locale)
  const row = await prisma.globalSettings.findFirst({
    select: { commonModulesJson: true },
  })
  const doc = parseCommonModulesDocument(row?.commonModulesJson ?? null)
  const rawEntry = getCommonModuleById(doc, moduleId)
  if (!rawEntry) return null

  /** Même forme que l’admin (`design` + locales texte) pour résolution identique au site. */
  const entry = normalizeCommonModuleEntry(rawEntry)

  const st = getSectionType(entry.sectionKey)
  if (!st) return null

  let data = resolveCommonModuleDataForLocale(entry, loc) as Record<string, unknown>
  const mediaIds = extractMediaIds(data as any)
  const mediaMap = await resolveMediaMap(mediaIds)
  let resolvedData = injectMediaUrls(data, mediaMap) as Record<string, unknown>
  /** Iframe admin : forcer proxy same-origin (les présignatures R2 peuvent ne pas charger dans <img>). */
  resolvedData = rewriteMediaUrlsToSiteProxyDeep(resolvedData) as Record<string, unknown>

  const key = entry.sectionKey
  const canonicalGridKey = resolveCanonicalSectionKey(key) ?? key
  if (canonicalGridKey === 'project_grid' && resolvedData) {
    const rawLimit = resolvedData.limit
    const limit =
      typeof rawLimit === 'number' && Number.isFinite(rawLimit) && rawLimit > 0
        ? Math.min(20, Math.floor(rawLimit))
        : undefined
    const showAllExclusiveOffers = readShowAllExclusiveOffersFlag(resolvedData.showAllExclusiveOffers)
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
    }
    resolvedData = { ...resolvedData, resolvedProjects }
  }

  return {
    id: `preview-common-module:${moduleId}`,
    key,
    order: 0,
    schemaVersion: st.schemaVersion,
    data: resolvedData,
    locale: loc,
    status: ContentStatus.PUBLISHED,
  }
}

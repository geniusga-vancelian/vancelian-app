import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault, defaultLocale, type Locale } from '@/config/locales'
import { ContentStatus } from '@prisma/client'
import { extractMediaIds, resolveMediaMap, type MediaInfo } from '@/lib/storage/media'
import {
  getExclusiveOfferCardsByPackagedProductIds,
  getExclusiveOfferCardsNewestFirst,
} from './exclusiveOfferGallery'
import { getProjectsByIds, type ProjectShrink } from './projects'
import {
  getCommonModuleById,
  parseCommonModulesDocument,
  resolveCommonModuleDataForLocale,
} from '@/lib/cms/commonModulesStorage'
import { commonModuleRefSchema, resolveCanonicalSectionKey } from '@/lib/sections/library'

export type ContentMode = 'published' | 'draft'

export interface SectionWithContent {
  id: string
  key: string
  order: number
  schemaVersion: string
  data: any
  locale: Locale
  status: ContentStatus
}

/**
 * Get all sections for a page with their content
 * @param slug Page slug (e.g., "home")
 * @param locale Locale code (e.g., "fr", "en")
 * @param mode "published" to read published content, "draft" to read draft (for preview)
 * @returns Ordered array of sections with their content data
 */
export async function getPageSections(
  slug: string,
  locale: string,
  mode: ContentMode = 'published'
): Promise<SectionWithContent[]> {
  const [page, globalModsRow] = await Promise.all([
    prisma.page.findUnique({
      where: { slug },
      include: {
        sections: {
          orderBy: { order: 'asc' },
          include: {
            contents: {
              where: {
                locale: getLocaleOrDefault(locale),
              },
            },
          },
        },
      },
    }),
    prisma.globalSettings.findFirst({ select: { commonModulesJson: true } }),
  ])

  if (!page) {
    return []
  }

  const resolvedLocale = getLocaleOrDefault(locale)
  const sections: SectionWithContent[] = []
  const commonDoc = parseCommonModulesDocument(globalModsRow?.commonModulesJson ?? null)

  // First pass: collect all content and extract all mediaIds
  const allMediaIds: string[] = []
  const sectionContents: Array<{
    section: typeof page.sections[0]
    content: any
    locale: Locale
    status: ContentStatus
    effectiveKey: string
    effectiveData: Record<string, unknown>
  }> = []

  for (const section of page.sections) {
    let content = section.contents.find(
      (c) => c.status === (mode === 'draft' ? 'DRAFT' : 'PUBLISHED')
    )

    // Fallback: if draft not found, try published
    if (mode === 'draft' && !content) {
      content = section.contents.find((c) => c.status === 'PUBLISHED')
    }

    // Fallback: if published not found for requested locale, try DRAFT for same locale
    if (mode === 'published' && !content) {
      content = section.contents.find((c) => c.status === 'DRAFT')
    }

    // Fallback: if still not found, try default locale (PUBLISHED first, then DRAFT)
    if (!content && resolvedLocale !== defaultLocale) {
      const defaultContent = await prisma.sectionContent.findFirst({
        where: {
          sectionId: section.id,
          locale: defaultLocale,
          status: mode === 'draft' ? 'DRAFT' : 'PUBLISHED',
        },
      })
      if (defaultContent) {
        content = defaultContent
      } else if (mode === 'published') {
        // Try DRAFT for default locale as last resort
        const defaultDraftContent = await prisma.sectionContent.findFirst({
          where: {
            sectionId: section.id,
            locale: defaultLocale,
            status: 'DRAFT',
          },
        })
        if (defaultDraftContent) {
          content = defaultDraftContent
        }
      }
    }

    if (content) {
      const contentLocale = content.locale as Locale
      const sk = typeof section.key === 'string' ? section.key.trim() : section.key
      const canonical = resolveCanonicalSectionKey(sk) ?? sk
      let effectiveKey = sk
      let effectiveData = (content.data ?? {}) as Record<string, unknown>

      if (canonical === 'common_module_ref') {
        const ref = commonModuleRefSchema.safeParse(effectiveData)
        const rawId = ref.success ? String(ref.data.commonModuleId ?? '').trim() : ''
        const idOk = isCommonModuleUuid(rawId)
        if (idOk) {
          const entry = getCommonModuleById(commonDoc, rawId)
          if (entry) {
            effectiveKey = entry.sectionKey
            effectiveData = resolveCommonModuleDataForLocale(entry, contentLocale)
          }
        }
      }

      sectionContents.push({
        section,
        content,
        locale: contentLocale,
        status: content.status,
        effectiveKey,
        effectiveData,
      })
      const mediaIds = extractMediaIds(effectiveData as any)
      if (
        process.env.NODE_ENV === 'development' &&
        (effectiveKey === 'hero' || effectiveKey === 'hero_secondary') &&
        mediaIds.length > 0
      ) {
        console.log('[getPageSections] Hero section - Extracted mediaIds:', mediaIds)
        console.log('[getPageSections] Hero section - Content data:', JSON.stringify(effectiveData, null, 2))
      }
      allMediaIds.push(...mediaIds)
    }
  }

  // Batch resolve all mediaIds
  const mediaMap = await resolveMediaMap(allMediaIds)
  
  if (process.env.NODE_ENV === 'development' && allMediaIds.length > 0) {
    console.log('[getPageSections] Resolved media map:', Array.from(mediaMap.entries()).map(([id, info]) => ({ id, url: info.url })))
  }

  // Second pass: inject media URLs into data and resolve projects if needed
  for (const { section, content, locale: contentLocale, status, effectiveKey, effectiveData } of sectionContents) {
    let resolvedData = injectMediaUrls(effectiveData as any, mediaMap)
    
    // Debug: log media resolution for hero sections
    if (
      process.env.NODE_ENV === 'development' &&
      (effectiveKey === 'hero' || effectiveKey === 'hero_secondary')
    ) {
      console.log('[getPageSections] Hero section - Original data:', JSON.stringify(effectiveData, null, 2))
      console.log('[getPageSections] Hero section - Resolved data:', JSON.stringify(resolvedData, null, 2))
      console.log('[getPageSections] Hero section - Media map size:', mediaMap.size)
    }

    // Special handling for projects/project_grid: exclusive offers (packaged_products) ou legacy projects
    if ((effectiveKey === 'projects' || effectiveKey === 'project_grid') && resolvedData) {
      const rawLimit = resolvedData.limit
      const limit =
        typeof rawLimit === 'number' && Number.isFinite(rawLimit) && rawLimit > 0
          ? Math.min(20, Math.floor(rawLimit))
          : undefined
      const showAllExclusiveOffers = resolvedData.showAllExclusiveOffers === true
      /** Même défaut que le formulaire CMS (`limit` absent ou invalide → 3). */
      const effectiveLimitForAll = limit ?? 3

      const selectedPackagedProductIds = resolvedData.selectedPackagedProductIds as
        | string[]
        | undefined
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
        resolvedProjects = await getExclusiveOfferCardsNewestFirst(
          contentLocale,
          effectiveLimitForAll,
        )
      } else if (packagedIds && packagedIds.length > 0) {
        resolvedProjects = await getExclusiveOfferCardsByPackagedProductIds(
          packagedIds,
          contentLocale,
        )
      } else if (legacyProjectIds && legacyProjectIds.length > 0) {
        resolvedProjects = await getProjectsByIds(legacyProjectIds, contentLocale)
      }

      resolvedData = {
        ...resolvedData,
        resolvedProjects,
      }
    }

    sections.push({
      id: section.id,
      key: effectiveKey,
      order: section.order,
      schemaVersion: section.schemaVersion,
      data: resolvedData,
      locale: contentLocale,
      status,
    })
  }

  return sections
}

/**
 * Aperçu admin : un seul bloc CMS d’une page (même résolution médias / common_module_ref que `getPageSections`).
 */
export async function getSectionPreviewById(
  sectionId: string,
  locale: string,
  mode: ContentMode = 'draft',
): Promise<SectionWithContent | null> {
  const row = await prisma.section.findUnique({
    where: { id: sectionId },
    select: { id: true, page: { select: { slug: true } } },
  })
  if (!row?.page?.slug) return null
  const all = await getPageSections(row.page.slug, locale, mode)
  return all.find((s) => s.id === sectionId) ?? null
}

const COMMON_MODULE_ID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function isCommonModuleUuid(s: string): boolean {
  return COMMON_MODULE_ID_RE.test(s)
}

/**
 * Ré-applique les URLs depuis les IDs après le parcours des clés : certaines données
 * fusionnées portent encore `backgroundMediaUrl: ""` (ou équivalent) qui écrasait
 * alors la valeur résolue via `backgroundMediaId` (ordre des clés dans `Object.entries`).
 */
function reconcileMediaUrlFieldsFromMap(
  resolved: Record<string, unknown>,
  mediaMap: Map<string, MediaInfo>,
): void {
  const apply = (
    idKey: string,
    urlKey: string,
    altKey?: string,
    wKey?: string,
    hKey?: string,
  ) => {
    const id = resolved[idKey]
    if (typeof id !== 'string' || !mediaMap.has(id)) return
    const media = mediaMap.get(id)!
    resolved[urlKey] = media.url
    if (altKey) resolved[altKey] = media.alt
    if (wKey) resolved[wKey] = media.width
    if (hKey) resolved[hKey] = media.height
  }
  apply(
    'backgroundMediaId',
    'backgroundMediaUrl',
    'backgroundMediaAlt',
    'backgroundMediaWidth',
    'backgroundMediaHeight',
  )
  apply(
    'imageMediaId',
    'imageMediaUrl',
    'imageMediaAlt',
    'imageMediaWidth',
    'imageMediaHeight',
  )
  apply('mediaId', 'mediaUrl', 'mediaAlt', 'mediaWidth', 'mediaHeight')
  apply('avatarMediaId', 'avatarMediaUrl')
}

/**
 * Helper to inject media URLs into section data
 * Exporté pour l’aperçu isolé d’un module commun (`/preview/common-module/...`).
 */
export function injectMediaUrls(data: any, mediaMap: Map<string, MediaInfo>): any {
  if (data === null || data === undefined) {
    return data
  }

  if (Array.isArray(data)) {
    return data.map((item) => injectMediaUrls(item, mediaMap))
  }

  if (typeof data === 'object') {
    const resolved: any = {}

    for (const [key, value] of Object.entries(data)) {
      if (key === 'mediaId' && typeof value === 'string' && mediaMap.has(value)) {
        const media = mediaMap.get(value)!
        resolved.mediaId = value
        resolved.mediaUrl = media.url
        resolved.mediaAlt = media.alt
        resolved.mediaWidth = media.width
        resolved.mediaHeight = media.height
      } else if (key === 'backgroundMediaId' && typeof value === 'string') {
        if (mediaMap.has(value)) {
          const media = mediaMap.get(value)!
          resolved.backgroundMediaId = value
          resolved.backgroundMediaUrl = media.url
          resolved.backgroundMediaAlt = media.alt
          resolved.backgroundMediaWidth = media.width
          resolved.backgroundMediaHeight = media.height
          if (process.env.NODE_ENV === 'development') {
            console.log('[injectMediaUrls] Resolved backgroundMediaId:', value, 'to URL:', media.url)
          }
        } else {
          // Keep the ID even if not found in map (for debugging)
          resolved.backgroundMediaId = value
          if (process.env.NODE_ENV === 'development') {
            console.warn('[injectMediaUrls] backgroundMediaId not found in mediaMap:', value, 'Available IDs:', Array.from(mediaMap.keys()))
          }
        }
      } else if (key === 'imageMediaId' && typeof value === 'string') {
        if (mediaMap.has(value)) {
          const media = mediaMap.get(value)!
          resolved.imageMediaId = value
          resolved.imageMediaUrl = media.url
          resolved.imageMediaAlt = media.alt
          resolved.imageMediaWidth = media.width
          resolved.imageMediaHeight = media.height
        } else {
          resolved.imageMediaId = value
        }
      } else if (key === 'avatarMediaId' && typeof value === 'string') {
        if (mediaMap.has(value)) {
          const media = mediaMap.get(value)!
          resolved.avatarMediaId = value
          resolved.avatarMediaUrl = media.url
        } else {
          resolved.avatarMediaId = value
        }
      } else {
        resolved[key] = injectMediaUrls(value, mediaMap)
      }
    }

    reconcileMediaUrlFieldsFromMap(resolved, mediaMap)

    return resolved
  }

  return data
}


import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault, defaultLocale, type Locale } from '@/config/locales'
import { ContentStatus } from '@prisma/client'
import { extractMediaIds, resolveMediaMap, type MediaInfo } from '@/lib/storage/media'
import { getProjectsByIds, type ProjectShrink } from './projects'

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
  const page = await prisma.page.findUnique({
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
  })

  if (!page) {
    return []
  }

  const resolvedLocale = getLocaleOrDefault(locale)
  const sections: SectionWithContent[] = []

  // First pass: collect all content and extract all mediaIds
  const allMediaIds: string[] = []
  const sectionContents: Array<{
    section: typeof page.sections[0]
    content: any
    locale: Locale
    status: ContentStatus
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
      sectionContents.push({
        section,
        content,
        locale: content.locale as Locale,
        status: content.status,
      })
      // Extract mediaIds from this section's data
      const mediaIds = extractMediaIds(content.data as any)
      if (process.env.NODE_ENV === 'development' && section.key === 'hero' && mediaIds.length > 0) {
        console.log('[getPageSections] Hero section - Extracted mediaIds:', mediaIds)
        console.log('[getPageSections] Hero section - Content data:', JSON.stringify(content.data, null, 2))
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
  for (const { section, content, locale: contentLocale, status } of sectionContents) {
    const data = content.data as any
    let resolvedData = injectMediaUrls(data, mediaMap)
    
    // Debug: log media resolution for hero sections
    if (process.env.NODE_ENV === 'development' && section.key === 'hero') {
      console.log('[getPageSections] Hero section - Original data:', JSON.stringify(data, null, 2))
      console.log('[getPageSections] Hero section - Resolved data:', JSON.stringify(resolvedData, null, 2))
      console.log('[getPageSections] Hero section - Media map size:', mediaMap.size)
    }

    // Special handling for projects/project_grid sections: resolve projects from DB
    if ((section.key === 'projects' || section.key === 'project_grid') && resolvedData) {
      const selectedProjectIds = resolvedData.selectedProjectIds as string[] | undefined

      let resolvedProjects: ProjectShrink[] = []

      // Only fetch projects if they are explicitly selected in the page admin
      // No fallback to latest projects - only show what's been selected
      if (selectedProjectIds && selectedProjectIds.length > 0) {
        // Fetch selected projects in order
        resolvedProjects = await getProjectsByIds(selectedProjectIds, contentLocale)
      }
      // If no projects are selected, resolvedProjects remains empty array

      // Inject resolved projects into data
      resolvedData = {
        ...resolvedData,
        resolvedProjects,
      }
    }

    sections.push({
      id: section.id,
      key: section.key,
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
 * Helper to inject media URLs into section data
 */
function injectMediaUrls(data: any, mediaMap: Map<string, MediaInfo>): any {
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
      } else {
        resolved[key] = injectMediaUrls(value, mediaMap)
      }
    }

    return resolved
  }

  return data
}


import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault, type Locale } from '@/config/locales'
import { ContentStatus } from '@prisma/client'

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

  for (const section of page.sections) {
    let content = section.contents.find(
      (c) => c.status === (mode === 'draft' ? 'DRAFT' : 'PUBLISHED')
    )

    // Fallback: if draft not found, try published
    if (mode === 'draft' && !content) {
      content = section.contents.find((c) => c.status === 'PUBLISHED')
    }

    // Fallback: if published not found, try default locale
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
      }
    }

    if (content) {
      sections.push({
        id: section.id,
        key: section.key,
        order: section.order,
        schemaVersion: section.schemaVersion,
        data: content.data as any,
        locale: content.locale as Locale,
        status: content.status,
      })
    }
  }

  return sections
}


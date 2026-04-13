/**
 * Helper functions to fetch and resolve projects for CMS sections
 */

import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getLocaleOrDefault, defaultLocale } from '@/config/locales'
import { getPresignedUrl } from '@/lib/storage/storageClient'

export interface ProjectShrink {
  id: string
  slug: string
  title: string
  location: string | null
  shortDescription: string | null
  /** Description longue (ex. page détail offre exclusive). */
  description: string | null
  /** Liens associés au module description (label + URL). */
  descriptionLinks: Array<{
    label: string
    url: string
  }> | null
  /** Configuration localisée du module "How it works". */
  howItWorks: {
    title: string | null
    content: string | null
    links: Array<{
      label: string
      url: string
    }>
  } | null
  /** Configuration localisée du module "Key information". */
  keyInformation: {
    title: string | null
    rows: Array<{
      categoryKey: string
      label: string
      value: string
      showInfoIcon: boolean
      infoTitle: string | null
      infoContent: string | null
    }>
  } | null
  /** Configuration FAQ projet (articles sélectionnés + toggle redirection tags). */
  faq: {
    enableTagRedirect: boolean
    tagRedirectLabel: string | null
    items: Array<{
      articleId: string
      articleSlug: string
      collectionSlug: string
      categorySlug: string
      question: string
      standfirst: string | null
    }>
  } | null
  coverUrl: string | null
  coverAlt: string | null
  /** Catégorie d'investissement (Real estate, Energy, Commodity, etc.) — peut être null. */
  investmentCategory: string | null
  /** URL vidéo teaser (ex. YouTube) pour la page détail. Null si pas de vidéo. */
  teaserVideoUrl: string | null
  /** True si le projet a au moins une photo en galerie (carrousel). */
  hasGallery: boolean
  /** Configuration du module "competitive advantages" spécifique au projet. */
  competitiveAdvantages: {
    title: string | null
    rows: Array<{
      icon: string
      iconBackgroundColor: string
      title: string
      description: string
    }>
  } | null
}

function buildI18nCompetitiveAdvantagesKey(projectId: string, locale: string) {
  return `${projectId}::${locale}`
}

type LocalizedProjectContent = {
  descriptionLinks: ProjectShrink['descriptionLinks']
  competitiveAdvantages: ProjectShrink['competitiveAdvantages']
  howItWorks: ProjectShrink['howItWorks']
  keyInformation: ProjectShrink['keyInformation']
  faq: ProjectShrink['faq']
}

async function getI18nCompetitiveAdvantagesByProjectIds(projectIds: string[]) {
  if (projectIds.length === 0) return new Map<string, LocalizedProjectContent>()

  let rows: Array<{
    project_id: string
    locale: string
    description_links: unknown
    competitive_advantages: unknown
    how_it_works: unknown
    key_information: unknown
    faq: unknown
  }>
  try {
    rows = await prisma.$queryRawUnsafe<
      Array<{
        project_id: string
        locale: string
        description_links: unknown
        competitive_advantages: unknown
        how_it_works: unknown
        key_information: unknown
        faq: unknown
      }>
    >(
      `SELECT "project_id", "locale", "description_links", "competitive_advantages", "how_it_works", "key_information", "faq" FROM "project_i18n" WHERE "project_id" = ANY($1::text[])`,
      projectIds
    )
  } catch (_) {
    const fallbackRows = await prisma.$queryRawUnsafe<
      Array<{
        project_id: string
        locale: string
        competitive_advantages: unknown
        how_it_works: unknown
      }>
    >(
      `SELECT "project_id", "locale", "competitive_advantages", "how_it_works" FROM "project_i18n" WHERE "project_id" = ANY($1::text[])`,
      projectIds
    )
    rows = fallbackRows.map((row) => ({
      ...row,
      description_links: null,
      key_information: null,
      faq: null,
    }))
  }

  return new Map(
    rows.map((row) => [
      buildI18nCompetitiveAdvantagesKey(row.project_id, row.locale),
      {
        descriptionLinks: (row.description_links as ProjectShrink['descriptionLinks']) ?? null,
        competitiveAdvantages:
          (row.competitive_advantages as ProjectShrink['competitiveAdvantages']) ?? null,
        howItWorks: (row.how_it_works as ProjectShrink['howItWorks']) ?? null,
        keyInformation: (row.key_information as ProjectShrink['keyInformation']) ?? null,
        faq: (row.faq as ProjectShrink['faq']) ?? null,
      },
    ])
  )
}

function resolveLocalizedCompetitiveAdvantages(
  projectId: string,
  locale: string | null | undefined,
  i18nValue: unknown,
  byProjectLocale: Map<
    string,
    LocalizedProjectContent
  >
): ProjectShrink['competitiveAdvantages'] {
  const currentLocale = locale ?? defaultLocale
  const directValue =
    i18nValue !== undefined
      ? ((i18nValue as ProjectShrink['competitiveAdvantages']) ?? null)
      : (byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, currentLocale))
            ?.competitiveAdvantages ?? null)

  if (directValue) return directValue
  if (currentLocale === defaultLocale) return directValue

  return (
    byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, defaultLocale))
      ?.competitiveAdvantages ?? directValue
  )
}

function resolveLocalizedDescriptionLinks(
  projectId: string,
  locale: string | null | undefined,
  i18nValue: unknown,
  byProjectLocale: Map<
    string,
    LocalizedProjectContent
  >
): ProjectShrink['descriptionLinks'] {
  const currentLocale = locale ?? defaultLocale
  const directValue =
    i18nValue !== undefined
      ? ((i18nValue as ProjectShrink['descriptionLinks']) ?? null)
      : (byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, currentLocale))
            ?.descriptionLinks ?? null)

  if (directValue) return directValue
  if (currentLocale === defaultLocale) return directValue

  return (
    byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, defaultLocale))
      ?.descriptionLinks ?? directValue
  )
}

function resolveLocalizedHowItWorks(
  projectId: string,
  locale: string | null | undefined,
  i18nValue: unknown,
  byProjectLocale: Map<
    string,
    LocalizedProjectContent
  >
): ProjectShrink['howItWorks'] {
  const currentLocale = locale ?? defaultLocale
  const directValue =
    i18nValue !== undefined
      ? ((i18nValue as ProjectShrink['howItWorks']) ?? null)
      : (byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, currentLocale))
            ?.howItWorks ?? null)

  if (directValue) return directValue
  if (currentLocale === defaultLocale) return directValue

  return (
    byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, defaultLocale))
      ?.howItWorks ?? directValue
  )
}

function resolveLocalizedKeyInformation(
  projectId: string,
  locale: string | null | undefined,
  i18nValue: unknown,
  byProjectLocale: Map<
    string,
    LocalizedProjectContent
  >
): ProjectShrink['keyInformation'] {
  const currentLocale = locale ?? defaultLocale
  const directValue =
    i18nValue !== undefined
      ? ((i18nValue as ProjectShrink['keyInformation']) ?? null)
      : (byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, currentLocale))
            ?.keyInformation ?? null)

  if (directValue) return directValue
  if (currentLocale === defaultLocale) return directValue

  return (
    byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, defaultLocale))
      ?.keyInformation ?? directValue
  )
}

function resolveLocalizedFaq(
  projectId: string,
  locale: string | null | undefined,
  i18nValue: unknown,
  byProjectLocale: Map<
    string,
    LocalizedProjectContent
  >
): ProjectShrink['faq'] {
  const currentLocale = locale ?? defaultLocale
  const directValue =
    i18nValue !== undefined
      ? ((i18nValue as ProjectShrink['faq']) ?? null)
      : (byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, currentLocale))
            ?.faq ?? null)

  if (directValue) return directValue
  if (currentLocale === defaultLocale) return directValue

  return (
    byProjectLocale.get(buildI18nCompetitiveAdvantagesKey(projectId, defaultLocale))
      ?.faq ?? directValue
  )
}

/**
 * Fetch projects by IDs (in order) and resolve media URLs
 */
export async function getProjectsByIds(
  projectIds: string[],
  locale: string
): Promise<ProjectShrink[]> {
  if (projectIds.length === 0) {
    return []
  }

  const resolvedLocale = getLocaleOrDefault(locale)

  // Fetch projects with i18n
  const projects = await prisma.project.findMany({
    where: {
      id: { in: projectIds },
      status: ContentStatus.PUBLISHED,
    },
    include: {
      coverMedia: true,
      projectMedia: true,
      i18n: {
        where: {
          locale: resolvedLocale,
        },
        take: 1,
      },
    },
  })

  // Maintain order from projectIds
  const orderedProjects = projectIds
    .map((id) => projects.find((p) => p.id === id))
    .filter((p): p is typeof projects[0] => p !== undefined)
  const competitiveAdvantagesByProjectLocale = await getI18nCompetitiveAdvantagesByProjectIds(
    orderedProjects.map((project) => project.id)
  )

  // Resolve i18n with fallback and media URLs
  const projectsWithData: ProjectShrink[] = await Promise.all(
    orderedProjects.map(async (project) => {
      let i18n = project.i18n[0] || null

      // Fallback to default locale
      if (!i18n && resolvedLocale !== defaultLocale) {
        const defaultI18n = await prisma.projectI18n.findFirst({
          where: {
            projectId: project.id,
            locale: defaultLocale,
          },
        })
        if (defaultI18n) {
          i18n = defaultI18n
        }
      }

      // Resolve cover media URL
      let coverUrl: string | null = null
      let coverAlt: string | null = null

      if (project.coverMedia) {
        try {
          coverUrl = await getPresignedUrl(project.coverMedia.key, 3600)
          coverAlt = project.coverMedia.alt || i18n?.title || project.slug
        } catch (error) {
          console.error(`Failed to get presigned URL for ${project.coverMedia.key}:`, error)
          coverUrl = project.coverMedia.url
          coverAlt = project.coverMedia.alt || i18n?.title || project.slug
        }
      }

      return {
        id: project.id,
        slug: project.slug,
        title: i18n?.title || project.slug,
        location: i18n?.location || null,
        shortDescription: i18n?.shortDescription || null,
        description: i18n?.description ?? null,
        descriptionLinks: resolveLocalizedDescriptionLinks(
          project.id,
          i18n?.locale,
          (i18n as any)?.descriptionLinks,
          competitiveAdvantagesByProjectLocale
        ),
        howItWorks: resolveLocalizedHowItWorks(
          project.id,
          i18n?.locale,
          (i18n as any)?.howItWorks,
          competitiveAdvantagesByProjectLocale
        ),
        keyInformation: resolveLocalizedKeyInformation(
          project.id,
          i18n?.locale,
          (i18n as any)?.keyInformation,
          competitiveAdvantagesByProjectLocale
        ),
        faq: resolveLocalizedFaq(
          project.id,
          i18n?.locale,
          (i18n as any)?.faq,
          competitiveAdvantagesByProjectLocale
        ),
        coverUrl,
        coverAlt,
        investmentCategory: project.investmentCategory ?? null,
        teaserVideoUrl: project.youtubeUrl ?? null,
        hasGallery: (project.projectMedia?.length ?? 0) > 0,
        competitiveAdvantages: resolveLocalizedCompetitiveAdvantages(
          project.id,
          i18n?.locale,
          (i18n as any)?.competitiveAdvantages,
          competitiveAdvantagesByProjectLocale
        ),
      }
    })
  )

  return projectsWithData
}

/**
 * Fetch latest published projects (fallback if no selectedProjectIds)
 */
export async function getLatestProjects(
  limit: number,
  locale: string
): Promise<ProjectShrink[]> {
  const resolvedLocale = getLocaleOrDefault(locale)

  const projects = await prisma.project.findMany({
    where: {
      status: ContentStatus.PUBLISHED,
    },
    include: {
      coverMedia: true,
      projectMedia: true,
      i18n: {
        where: {
          locale: resolvedLocale,
        },
        take: 1,
      },
    },
    orderBy: { updatedAt: 'desc' },
    take: limit,
  })
  const competitiveAdvantagesByProjectLocale = await getI18nCompetitiveAdvantagesByProjectIds(
    projects.map((project) => project.id)
  )
  // Resolve i18n with fallback and media URLs
  const projectsWithData: ProjectShrink[] = await Promise.all(
    projects.map(async (project) => {
      let i18n = project.i18n[0] || null

      // Fallback to default locale
      if (!i18n && resolvedLocale !== defaultLocale) {
        const defaultI18n = await prisma.projectI18n.findFirst({
          where: {
            projectId: project.id,
            locale: defaultLocale,
          },
        })
        if (defaultI18n) {
          i18n = defaultI18n
        }
      }

      // Resolve cover media URL
      let coverUrl: string | null = null
      let coverAlt: string | null = null

      if (project.coverMedia) {
        try {
          coverUrl = await getPresignedUrl(project.coverMedia.key, 3600)
          coverAlt = project.coverMedia.alt || i18n?.title || project.slug
        } catch (error) {
          console.error(`Failed to get presigned URL for ${project.coverMedia.key}:`, error)
          coverUrl = project.coverMedia.url
          coverAlt = project.coverMedia.alt || i18n?.title || project.slug
        }
      }

      return {
        id: project.id,
        slug: project.slug,
        title: i18n?.title || project.slug,
        location: i18n?.location || null,
        shortDescription: i18n?.shortDescription || null,
        description: i18n?.description ?? null,
        descriptionLinks: resolveLocalizedDescriptionLinks(
          project.id,
          i18n?.locale,
          (i18n as any)?.descriptionLinks,
          competitiveAdvantagesByProjectLocale
        ),
        howItWorks: resolveLocalizedHowItWorks(
          project.id,
          i18n?.locale,
          (i18n as any)?.howItWorks,
          competitiveAdvantagesByProjectLocale
        ),
        keyInformation: resolveLocalizedKeyInformation(
          project.id,
          i18n?.locale,
          (i18n as any)?.keyInformation,
          competitiveAdvantagesByProjectLocale
        ),
        faq: resolveLocalizedFaq(
          project.id,
          i18n?.locale,
          (i18n as any)?.faq,
          competitiveAdvantagesByProjectLocale
        ),
        coverUrl,
        coverAlt,
        investmentCategory: project.investmentCategory ?? null,
        teaserVideoUrl: project.youtubeUrl ?? null,
        hasGallery: (project.projectMedia?.length ?? 0) > 0,
        competitiveAdvantages: resolveLocalizedCompetitiveAdvantages(
          project.id,
          i18n?.locale,
          (i18n as any)?.competitiveAdvantages,
          competitiveAdvantagesByProjectLocale
        ),
      }
    })
  )

  return projectsWithData
}


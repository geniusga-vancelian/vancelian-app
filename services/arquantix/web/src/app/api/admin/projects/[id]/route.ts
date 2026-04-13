import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { z } from 'zod'
import { isValidSlug } from '@/lib/utils/slugify'

const updateProjectSchema = z.object({
  slug: z.string().min(1).max(60).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }).optional(),
  status: z.enum(['DRAFT', 'PUBLISHED']).optional(),
  coverMediaId: z.string().optional().nullable(),
  heroMediaId: z.string().optional().nullable(),
  youtubeUrl: z.string().url().optional().or(z.literal('')).nullable(),
  investmentCategory: z.string().max(200).optional().nullable(),
})

async function getProjectI18nLocalizedContentMap(projectId: string) {
  let rows: Array<{
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
        locale: string
        description_links: unknown
        competitive_advantages: unknown
        how_it_works: unknown
        key_information: unknown
        faq: unknown
      }>
    >(
      `SELECT "locale", "description_links", "competitive_advantages", "how_it_works", "key_information", "faq" FROM "project_i18n" WHERE "project_id" = $1`,
      projectId
    )
  } catch (error) {
    const fallbackRows = await prisma.$queryRawUnsafe<
      Array<{ locale: string; competitive_advantages: unknown; how_it_works: unknown }>
    >(
      `SELECT "locale", "competitive_advantages", "how_it_works" FROM "project_i18n" WHERE "project_id" = $1`,
      projectId
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
      row.locale,
      {
        descriptionLinks: row.description_links ?? null,
        competitiveAdvantages: row.competitive_advantages ?? null,
        howItWorks: row.how_it_works ?? null,
        keyInformation: row.key_information ?? null,
        faq: row.faq ?? null,
      },
    ])
  )
}

// GET /api/admin/projects/[id]
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const project = await prisma.project.findUnique({
      where: { id: params.id },
      include: {
        coverMedia: true,
        heroMedia: true,
        i18n: {
          orderBy: { locale: 'asc' },
        },
        projectMedia: {
          include: {
            media: true,
          },
          orderBy: { order: 'asc' },
        },
      },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Generate presigned URLs for cover media, hero media and gallery media
    let coverUrl: string | null = null
    let heroUrl: string | null = null
    let galleryWithUrls: any[] = []

    try {
      const promises: Promise<any>[] = []
      
      if (project.coverMedia?.key) {
        promises.push(
          getPresignedUrl(project.coverMedia.key, 3600)
            .then((url) => { coverUrl = url })
            .catch(() => { coverUrl = project.coverMedia!.url })
        )
      } else if (project.coverMedia) {
        coverUrl = project.coverMedia.url
      }
      
      if (project.heroMedia?.key) {
        promises.push(
          getPresignedUrl(project.heroMedia.key, 3600)
            .then((url) => { heroUrl = url })
            .catch(() => { heroUrl = project.heroMedia!.url })
        )
      } else if (project.heroMedia) {
        heroUrl = project.heroMedia.url
      }
      
      promises.push(
        Promise.all(
          project.projectMedia.map(async (item) => {
            try {
              const url = item.media?.key
                ? await getPresignedUrl(item.media.key, 3600)
                : item.media.url
              return {
                ...item,
                media: {
                  ...item.media,
                  url,
                },
              }
            } catch (error) {
              return {
                ...item,
                media: {
                  ...item.media,
                  url: item.media.url,
                },
              }
            }
          })
        ).then((result) => { galleryWithUrls = result })
      )
      
      await Promise.all(promises)
    } catch (error) {
      console.error('Error generating presigned URLs:', error)
      // Fallback to original URLs
      coverUrl = project.coverMedia?.url || null
      heroUrl = project.heroMedia?.url || null
      galleryWithUrls = project.projectMedia.map((item) => ({
        ...item,
        media: {
          ...item.media,
          url: item.media.url,
        },
      }))
    }

    const localizedByLocale = await getProjectI18nLocalizedContentMap(params.id)
    const { projectMedia: _galleryRows, ...projectJsonBase } = project
    const projectWithPresignedUrls = {
      ...projectJsonBase,
      i18n: project.i18n.map((item: any) => ({
        ...item,
        descriptionLinks:
          item.descriptionLinks !== undefined
            ? item.descriptionLinks
            : (localizedByLocale.get(item.locale)?.descriptionLinks ?? null),
        competitiveAdvantages:
          item.competitiveAdvantages !== undefined
            ? item.competitiveAdvantages
            : (localizedByLocale.get(item.locale)?.competitiveAdvantages ?? null),
        howItWorks:
          item.howItWorks !== undefined
            ? item.howItWorks
            : (localizedByLocale.get(item.locale)?.howItWorks ?? null),
        keyInformation:
          item.keyInformation !== undefined
            ? item.keyInformation
            : (localizedByLocale.get(item.locale)?.keyInformation ?? null),
        faq:
          item.faq !== undefined
            ? item.faq
            : (localizedByLocale.get(item.locale)?.faq ?? null),
      })),
      coverMedia: project.coverMedia
        ? {
            ...project.coverMedia,
            url: coverUrl || project.coverMedia.url,
          }
        : null,
      heroMedia: project.heroMedia
        ? {
            ...project.heroMedia,
            url: heroUrl || project.heroMedia.url,
          }
        : null,
      gallery: galleryWithUrls,
    }

    return NextResponse.json({ project: projectWithPresignedUrls })
  } catch (error) {
    console.error('Error fetching project:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/projects/[id]
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { slug, status, coverMediaId, heroMediaId, youtubeUrl, investmentCategory } = updateProjectSchema.parse(body)

    const currentProject = await prisma.project.findUnique({
      where: { id: params.id },
    })

    if (!currentProject) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Check if new slug already exists (if changed)
    if (slug && slug !== currentProject.slug) {
      const existing = await prisma.project.findUnique({
        where: { slug },
      })
      if (existing) {
        return NextResponse.json(
          { error: 'Project with this slug already exists' },
          { status: 409 }
        )
      }
    }

    const updateData: any = {}
    if (slug !== undefined) updateData.slug = slug
    if (status !== undefined) updateData.status = status
    if (coverMediaId !== undefined) {
      if (!coverMediaId) {
        updateData.coverMediaId = null
      } else {
        const mediaExists = await prisma.media.findUnique({
          where: { id: coverMediaId },
          select: { id: true },
        })
        updateData.coverMediaId = mediaExists ? coverMediaId : null
      }
    }
    if (heroMediaId !== undefined) {
      if (!heroMediaId) {
        updateData.heroMediaId = null
      } else {
        const mediaExists = await prisma.media.findUnique({
          where: { id: heroMediaId },
          select: { id: true },
        })
        updateData.heroMediaId = mediaExists ? heroMediaId : null
      }
    }
    if (youtubeUrl !== undefined) updateData.youtubeUrl = youtubeUrl || null
    if (investmentCategory !== undefined) updateData.investmentCategory = investmentCategory ?? null

    let project
    const includePayload = {
      coverMedia: true,
      heroMedia: true,
      i18n: {
        orderBy: { locale: 'asc' as const },
      },
      projectMedia: {
        include: {
          media: true,
        },
        orderBy: { order: 'asc' as const },
      },
    }
    const hasOtherUpdates = Object.keys(updateData).length > 0
    if (hasOtherUpdates) {
      project = await prisma.project.update({
        where: { id: params.id },
        data: updateData,
        include: includePayload,
      })
    } else {
      project = await prisma.project.findUnique({
        where: { id: params.id },
        include: includePayload,
      })
    }

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Generate presigned URLs for cover media, hero media and gallery media
    let coverUrl: string | null = null
    let heroUrl: string | null = null
    let galleryWithUrls: any[] = []

    try {
      const promises: Promise<any>[] = []
      
      if (project.coverMedia?.key) {
        promises.push(
          getPresignedUrl(project.coverMedia.key, 3600)
            .then((url) => { coverUrl = url })
            .catch(() => { coverUrl = project.coverMedia!.url })
        )
      } else if (project.coverMedia) {
        coverUrl = project.coverMedia.url
      }
      
      if (project.heroMedia?.key) {
        promises.push(
          getPresignedUrl(project.heroMedia.key, 3600)
            .then((url) => { heroUrl = url })
            .catch(() => { heroUrl = project.heroMedia!.url })
        )
      } else if (project.heroMedia) {
        heroUrl = project.heroMedia.url
      }
      
      promises.push(
        Promise.all(
          project.projectMedia.map(async (item) => {
            try {
              const url = item.media?.key
                ? await getPresignedUrl(item.media.key, 3600)
                : item.media.url
              return {
                ...item,
                media: {
                  ...item.media,
                  url,
                },
              }
            } catch (error) {
              return {
                ...item,
                media: {
                  ...item.media,
                  url: item.media.url,
                },
              }
            }
          })
        ).then((result) => { galleryWithUrls = result })
      )
      
      await Promise.all(promises)
    } catch (error) {
      console.error('Error generating presigned URLs:', error)
      // Fallback to original URLs
      coverUrl = project.coverMedia?.url || null
      heroUrl = project.heroMedia?.url || null
      galleryWithUrls = project.projectMedia.map((item) => ({
        ...item,
        media: {
          ...item.media,
          url: item.media.url,
        },
      }))
    }

    const localizedByLocale = await getProjectI18nLocalizedContentMap(params.id)
    const { projectMedia: _galleryRowsPut, ...projectJsonBasePut } = project
    const projectWithPresignedUrls = {
      ...projectJsonBasePut,
      i18n: project.i18n.map((item: any) => ({
        ...item,
        descriptionLinks:
          item.descriptionLinks !== undefined
            ? item.descriptionLinks
            : (localizedByLocale.get(item.locale)?.descriptionLinks ?? null),
        competitiveAdvantages:
          item.competitiveAdvantages !== undefined
            ? item.competitiveAdvantages
            : (localizedByLocale.get(item.locale)?.competitiveAdvantages ?? null),
        howItWorks:
          item.howItWorks !== undefined
            ? item.howItWorks
            : (localizedByLocale.get(item.locale)?.howItWorks ?? null),
        keyInformation:
          item.keyInformation !== undefined
            ? item.keyInformation
            : (localizedByLocale.get(item.locale)?.keyInformation ?? null),
        faq:
          item.faq !== undefined
            ? item.faq
            : (localizedByLocale.get(item.locale)?.faq ?? null),
      })),
      coverMedia: project.coverMedia
        ? {
            ...project.coverMedia,
            url: coverUrl || project.coverMedia.url,
          }
        : null,
      heroMedia: project.heroMedia
        ? {
            ...project.heroMedia,
            url: heroUrl || project.heroMedia.url,
          }
        : null,
      gallery: galleryWithUrls,
    }

    return NextResponse.json({ project: projectWithPresignedUrls })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating project:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    return NextResponse.json(
      {
        error: 'Internal server error',
        message: errorMessage,
        ...(process.env.NODE_ENV === 'development' && {
          stack: error instanceof Error ? error.stack : undefined,
        }),
      },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/projects/[id]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const project = await prisma.project.findUnique({
      where: { id: params.id },
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Delete project (cascade will handle related records: i18n, gallery, etc.)
    await prisma.project.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ message: 'Project deleted successfully' })
  } catch (error) {
    console.error('Error deleting project:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

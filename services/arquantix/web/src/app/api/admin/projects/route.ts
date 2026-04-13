import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'
import { slugify, isValidSlug } from '@/lib/utils/slugify'
import { defaultLocale } from '@/config/locales'
import { isProjectBasedExclusiveOfferCreationBlocked } from '@/lib/admin/projectExclusiveOfferGuards'

const createProjectSchema = z.object({
  slug: z.string().min(1).max(60).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }),
  status: z.enum(['DRAFT', 'PUBLISHED']).optional(),
  coverMediaId: z.string().optional(),
  youtubeUrl: z.string().url().optional().or(z.literal('')),
})

const updateProjectSchema = z.object({
  slug: z.string().min(1).max(60).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }).optional(),
  status: z.enum(['DRAFT', 'PUBLISHED']).optional(),
  coverMediaId: z.string().optional().nullable(),
  youtubeUrl: z.string().url().optional().or(z.literal('')).nullable(),
})

// GET /api/admin/projects?query=&status=&page=&pageSize=
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const query = searchParams.get('query') || ''
    const status = searchParams.get('status') as ContentStatus | null
    const page = parseInt(searchParams.get('page') || '1', 10)
    const pageSize = parseInt(searchParams.get('pageSize') || '20', 10)

    const where: any = {}

    // Filter by status
    if (status) {
      where.status = status
    }

    // Search in i18n titles
    if (query) {
      where.i18n = {
        some: {
          title: {
            contains: query,
            mode: 'insensitive',
          },
        },
      }
    }

    const [projects, total] = await Promise.all([
      prisma.project.findMany({
        where,
        include: {
          coverMedia: true,
          i18n: {
            where: {
              locale: defaultLocale,
            },
            take: 1,
          },
        },
        orderBy: { updatedAt: 'desc' },
        skip: (page - 1) * pageSize,
        take: pageSize,
      }),
      prisma.project.count({ where }),
    ])

    // Generate presigned URLs for cover media
    const projectsWithPresignedUrls = await Promise.all(
      projects.map(async (project) => ({
        ...project,
        coverMedia: project.coverMedia
          ? {
              ...project.coverMedia,
              url: await getPresignedUrl(project.coverMedia.key, 3600).catch(
                () => project.coverMedia!.url
              ),
            }
          : null,
      }))
    )

    return NextResponse.json({
      projects: projectsWithPresignedUrls,
      pagination: {
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
      },
    })
  } catch (error) {
    console.error('Error fetching projects:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/projects
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    if (isProjectBasedExclusiveOfferCreationBlocked()) {
      return NextResponse.json(
        {
          error: 'Project-based creation disabled',
          detail:
            'New CMS Projects cannot be created here for Exclusive Offers. Use Vault Builder + Product Registry. Set ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true to temporarily allow (rollback).',
          code: 'PROJECT_BASED_EO_BLOCKED',
        },
        { status: 403 },
      )
    }

    const body = await request.json()
    const { slug, status, coverMediaId, youtubeUrl } = createProjectSchema.parse(body)

    // Check if slug already exists
    const existing = await prisma.project.findUnique({
      where: { slug },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Project with this slug already exists' },
        { status: 409 }
      )
    }

    // Create project with default i18n
    const project = await prisma.project.create({
      data: {
        slug,
        status: status || 'DRAFT',
        coverMediaId: coverMediaId || null,
        youtubeUrl: youtubeUrl || null,
        i18n: {
          create: {
            locale: defaultLocale,
            title: '', // Empty title, to be filled in editor
          },
        },
      },
      include: {
        coverMedia: true,
        i18n: {
          where: {
            locale: defaultLocale,
          },
        },
      },
    })

    return NextResponse.json({ project }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating project:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


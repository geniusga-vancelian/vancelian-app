import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { ContentStatus } from '@prisma/client'
import { z } from 'zod'
import { slugify, isValidSlug, calculateUrlPath } from '@/lib/utils/slugify'

const createPageSchema = z.object({
  template: z.string().default('homepage'),
  title: z.string().max(200).optional(),
  slug: z.string().min(1).max(60).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }),
  description: z.string().max(1000).optional(),
})

// GET /api/admin/pages - List all pages
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const pages = await prisma.page.findMany({
      orderBy: { createdAt: 'asc' },
      include: {
        sections: {
          orderBy: { order: 'asc' },
        },
      },
    })

    // Add computedUrlPath to each page
    const pagesWithComputedUrl = pages.map((page) => ({
      id: page.id,
      slug: page.slug,
      title: page.title,
      computedUrlPath: page.slug === 'home' ? '/' : `/${page.slug}`,
      urlPath: page.urlPath,
      template: page.template,
      description: page.description,
      createdAt: page.createdAt,
      updatedAt: page.updatedAt,
      sections: page.sections,
    }))

    return NextResponse.json({ pages: pagesWithComputedUrl })
  } catch (error) {
    console.error('Error fetching pages:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/pages - Create a new page
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { template, title, slug, description } = createPageSchema.parse(body)

    const urlPath = calculateUrlPath(slug)

    // Check if page with this slug or urlPath already exists
    const existing = await prisma.page.findFirst({
      where: {
        OR: [{ slug }, { urlPath }],
      },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Page with this slug or URL path already exists' },
        { status: 409 }
      )
    }

    const page = await prisma.page.create({
      data: {
        slug,
        urlPath,
        title: title || null,
        template,
        description: description || null,
      },
    })

    // If creating "home" page, create default sections
    // Only create sections for the "home" slug, not all homepage templates
    if (slug === 'home') {
      const defaultLocale = 'fr'
      const sectionsData = [
        { key: 'hero', order: 0, schemaVersion: 'v1', data: { title: 'Bienvenue sur Arquantix', subtitle: 'Fractional Real Estate, Institutional Rigor.', ctaText: 'Découvrir', ctaLink: '/projects' } },
        { key: 'features', order: 1, schemaVersion: 'v1', data: { title: 'Nos Avantages', items: [{ title: 'Service 1', description: 'Description du service 1' }] } },
        { key: 'projects', order: 2, schemaVersion: 'v1', data: { title: 'Nos Projets', description: 'Découvrez nos opportunités', items: [] } },
        { key: 'pricing', order: 3, schemaVersion: 'v1', data: { title: 'Tarification Simple', plans: [] } },
        { key: 'footer', order: 4, schemaVersion: 'v1', data: { copyright: '© 2026 Arquantix. Tous droits réservés.', links: [] } },
      ]

      for (const sectionData of sectionsData) {
        const section = await prisma.section.create({
          data: {
            pageId: page.id,
            key: sectionData.key,
            order: sectionData.order,
            schemaVersion: sectionData.schemaVersion,
            contents: {
              create: [
                {
                  locale: defaultLocale,
                  status: ContentStatus.DRAFT,
                  data: sectionData.data,
                  updatedByUserId: session.userId,
                },
                {
                  locale: defaultLocale,
                  status: ContentStatus.PUBLISHED,
                  data: sectionData.data,
                  updatedByUserId: session.userId,
                },
              ],
            },
          },
        })
      }
    }

    return NextResponse.json({ page }, { status: 201 })
  } catch (error) {
    console.error('Error creating page:', error)
    
    // Log more details about the error
    if (error instanceof z.ZodError) {
      console.error('Validation error:', error.issues)
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    
    // Log Prisma errors in detail
    if (error && typeof error === 'object' && 'code' in error) {
      console.error('Prisma error code:', error.code)
      console.error('Prisma error message:', (error as any).message)
      console.error('Prisma error meta:', (error as any).meta)
    }
    
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
        details: process.env.NODE_ENV === 'development' ? String(error) : undefined
      },
      { status: 500 }
    )
  }
}


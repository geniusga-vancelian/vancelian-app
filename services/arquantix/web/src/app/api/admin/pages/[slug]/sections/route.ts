import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const createSectionSchema = z.object({
  key: z.string().min(1),
  order: z.number().int().min(0),
  schemaVersion: z.string().default('v1'),
})

// GET /api/admin/pages/[slug]/sections - Get all sections for a page
export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
      include: {
        sections: {
          orderBy: { order: 'asc' },
          include: {
            contents: {
              orderBy: [{ locale: 'asc' }, { status: 'asc' }],
            },
          },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    return NextResponse.json({ sections: page.sections })
  } catch (error) {
    console.error('Error fetching sections:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/pages/[slug]/sections - Create a new section
export async function POST(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = createSectionSchema.parse(body)

    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Check if section with same key already exists
    const existing = await prisma.section.findUnique({
      where: {
        pageId_key: {
          pageId: page.id,
          key: validated.key,
        },
      },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Section with this key already exists' },
        { status: 409 }
      )
    }

    const section = await prisma.section.create({
      data: {
        pageId: page.id,
        key: validated.key,
        order: validated.order,
        schemaVersion: validated.schemaVersion,
      },
    })

    return NextResponse.json({ section }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}










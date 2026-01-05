import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale } from '@/config/locales'

const updateContentSchema = z.object({
  locale: z.string().refine(isValidLocale, {
    message: 'Invalid locale',
  }),
  data: z.any(), // JSON data, validated per section type
})

// GET /api/admin/sections/[sectionId]?locale=xx&status=draft|published
export async function GET(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const locale = searchParams.get('locale')
    const status = searchParams.get('status')?.toUpperCase()

    if (!locale || !isValidLocale(locale)) {
      return NextResponse.json(
        { error: 'Valid locale is required' },
        { status: 400 }
      )
    }

    if (status !== 'DRAFT' && status !== 'PUBLISHED') {
      return NextResponse.json(
        { error: 'Status must be draft or published' },
        { status: 400 }
      )
    }

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
      include: {
        page: true,
        contents: {
          where: {
            locale,
            status: status as 'DRAFT' | 'PUBLISHED',
          },
        },
      },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    const content = section.contents[0] || null

    return NextResponse.json({
      section: {
        id: section.id,
        key: section.key,
        order: section.order,
        schemaVersion: section.schemaVersion,
        page: {
          slug: section.page.slug,
        },
      },
      content,
    })
  } catch (error) {
    console.error('Error fetching section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/sections/[sectionId] - Save draft for locale
export async function PUT(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updateContentSchema.parse(body)

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    // Upsert draft content
    const content = await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: params.sectionId,
          locale: validated.locale,
          status: 'DRAFT',
        },
      },
      update: {
        data: validated.data,
        updatedByUserId: session.userId,
      },
      create: {
        sectionId: params.sectionId,
        locale: validated.locale,
        status: 'DRAFT',
        data: validated.data,
        updatedByUserId: session.userId,
      },
    })

    return NextResponse.json({ content })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error saving draft:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


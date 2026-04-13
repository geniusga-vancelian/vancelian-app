import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getSectionType } from '@/lib/sections/library'
import { ContentStatus } from '@prisma/client'
import { defaultLocale } from '@/config/locales'
import { z } from 'zod'

const addSectionSchema = z.object({
  typeKey: z.string().min(1, 'Section type key is required'),
})

/**
 * POST /api/admin/pages/[slug]/sections/add
 * Add a new section to a page from the section library
 */
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
    const validated = addSectionSchema.parse(body)

    // Get page
    const page = await prisma.page.findUnique({
      where: { slug: params.slug },
      include: {
        sections: {
          orderBy: { order: 'desc' },
          take: 1,
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Get section type from library
    const sectionType = getSectionType(validated.typeKey)
    if (!sectionType) {
      return NextResponse.json(
        { error: `Unknown section type: ${validated.typeKey}` },
        { status: 400 }
      )
    }

    // Check if template allows this section type
    if (!sectionType.allowedOnTemplates.includes(page.template) && !sectionType.allowedOnTemplates.includes('default')) {
      return NextResponse.json(
        { error: `Section type "${sectionType.label}" is not allowed on template "${page.template}"` },
        { status: 400 }
      )
    }

    // Calculate next order (last section order + 1, or 0 if no sections)
    const nextOrder = page.sections.length > 0 ? page.sections[0].order + 1 : 0

    // Check if section with same key already exists on this page
    const existingSection = await prisma.section.findUnique({
      where: {
        pageId_key: {
          pageId: page.id,
          key: validated.typeKey,
        },
      },
    })

    if (existingSection) {
      return NextResponse.json(
        { error: `A section with key "${validated.typeKey}" already exists on this page` },
        { status: 409 }
      )
    }

    // Create section with default content (DRAFT and PUBLISHED)
    const section = await prisma.section.create({
      data: {
        pageId: page.id,
        key: validated.typeKey,
        order: nextOrder,
        schemaVersion: sectionType.schemaVersion,
        contents: {
          create: [
            {
              locale: defaultLocale,
              status: ContentStatus.DRAFT,
              data: sectionType.defaultData,
              updatedByUserId: session.userId,
            },
            {
              locale: defaultLocale,
              status: ContentStatus.PUBLISHED,
              data: sectionType.defaultData,
              updatedByUserId: session.userId,
            },
          ],
        },
      },
      include: {
        contents: {
          select: {
            id: true,
            locale: true,
            status: true,
          },
        },
      },
    })

    return NextResponse.json({ section }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error adding section:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}










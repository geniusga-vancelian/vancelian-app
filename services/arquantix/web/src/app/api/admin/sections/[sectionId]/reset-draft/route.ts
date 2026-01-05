import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale } from '@/config/locales'

const resetDraftSchema = z.object({
  locale: z.string().refine(isValidLocale, {
    message: 'Invalid locale',
  }),
})

// POST /api/admin/sections/[sectionId]/reset-draft - Copy published -> draft
export async function POST(
  request: NextRequest,
  { params }: { params: { sectionId: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = resetDraftSchema.parse(body)

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    // Get published content
    const published = await prisma.sectionContent.findUnique({
      where: {
        sectionId_locale_status: {
          sectionId: params.sectionId,
          locale: validated.locale,
          status: 'PUBLISHED',
        },
      },
    })

    if (!published) {
      return NextResponse.json(
        { error: 'No published content found' },
        { status: 404 }
      )
    }

    // Upsert draft content (copy from published)
    const draft = await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: params.sectionId,
          locale: validated.locale,
          status: 'DRAFT',
        },
      },
      update: {
        data: published.data,
        updatedByUserId: session.userId,
      },
      create: {
        sectionId: params.sectionId,
        locale: validated.locale,
        status: 'DRAFT',
        data: published.data,
        updatedByUserId: session.userId,
      },
    })

    return NextResponse.json({ content: draft })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error resetting draft:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale } from '@/config/locales'
import { TranslationStatus } from '@prisma/client'

const publishSchema = z.object({
  locale: z.string().refine(isValidLocale, {
    message: 'Invalid locale',
  }),
})

// POST /api/admin/sections/[sectionId]/publish - Copy draft -> published
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
    const validated = publishSchema.parse(body)

    const section = await prisma.section.findUnique({
      where: { id: params.sectionId },
    })

    if (!section) {
      return NextResponse.json({ error: 'Section not found' }, { status: 404 })
    }

    // Get draft content
    const draft = await prisma.sectionContent.findUnique({
      where: {
        sectionId_locale_status: {
          sectionId: params.sectionId,
          locale: validated.locale,
          status: 'DRAFT',
        },
      },
    })

    if (!draft) {
      return NextResponse.json(
        { error: 'No draft content found' },
        { status: 404 }
      )
    }

    // Check if draft has unapproved machine translation
    const hasUnapprovedMachine = draft.translationStatus === TranslationStatus.MACHINE

    // Upsert published content (copy from draft, including translationStatus)
    const published = await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: params.sectionId,
          locale: validated.locale,
          status: 'PUBLISHED',
        },
      },
      update: {
        data: draft.data as any, // Prisma Json type compatibility
        translationStatus: draft.translationStatus, // Copy translation status
        updatedByUserId: session.userId,
      },
      create: {
        sectionId: params.sectionId,
        locale: validated.locale,
        status: 'PUBLISHED',
        data: draft.data as any, // Prisma Json type compatibility
        translationStatus: draft.translationStatus, // Copy translation status
        updatedByUserId: session.userId,
      },
    })

    return NextResponse.json({
      content: published,
      warning: hasUnapprovedMachine
        ? `Locale ${validated.locale} contains machine translation not approved yet.`
        : undefined,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error publishing content:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


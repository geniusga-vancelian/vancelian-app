import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidLocale } from '@/config/locales'

const updateI18nSchema = z.object({
  locale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
  title: z.string().min(1),
  subtitle: z.string().optional().nullable(),
  description: z.string().optional().nullable(),
})

// PUT /api/admin/academy/collections/[id]/i18n
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updateI18nSchema.parse(body)

    const i18n = await prisma.academyCollectionI18n.upsert({
      where: {
        collectionId_locale: {
          collectionId: params.id,
          locale: validated.locale,
        },
      },
      update: {
        title: validated.title,
        subtitle: validated.subtitle,
        description: validated.description,
      },
      create: {
        collectionId: params.id,
        locale: validated.locale,
        title: validated.title,
        subtitle: validated.subtitle,
        description: validated.description,
        translationStatus: 'ORIGINAL',
      },
    })

    return NextResponse.json({ i18n })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 },
      )
    }
    console.error('Error updating academy collection i18n:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

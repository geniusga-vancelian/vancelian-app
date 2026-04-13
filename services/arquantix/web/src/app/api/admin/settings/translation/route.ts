import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { supportedLocales, defaultLocale } from '@/config/locales'
import { Prisma } from '@prisma/client'

const updateTranslationSettingsSchema = z.object({
  supportedLocales: z.array(z.string()).optional(),
  defaultLocale: z.string().optional(),
  translationGlossary: z
    .object({
      brandTerms: z
        .array(
          z.object({
            term: z.string(),
            keep: z.boolean(),
          })
        )
        .optional(),
      preferred: z
        .array(
          z.object({
            from: z.string(),
            to: z.string(),
          })
        )
        .optional(),
    })
    .optional()
    .nullable(),
})

// GET /api/admin/settings/translation
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    let settings = await prisma.appSettings.findUnique({
      where: { id: 'default' },
    })

    // Create default if doesn't exist
    if (!settings) {
      settings = await prisma.appSettings.create({
        data: {
          id: 'default',
          supportedLocales: JSON.stringify(supportedLocales),
          defaultLocale,
          translationGlossary: Prisma.JsonNull,
        },
      })
    }

    // Parse supportedLocales safely
    let parsedLocales = supportedLocales
    if (settings.supportedLocales) {
      try {
        parsedLocales = typeof settings.supportedLocales === 'string'
          ? JSON.parse(settings.supportedLocales)
          : (settings.supportedLocales as unknown as string[])
      } catch (error) {
        console.warn('Failed to parse supportedLocales, using default:', error)
        parsedLocales = supportedLocales
      }
    }

    // Parse translationGlossary safely (it's Json type from Prisma)
    let parsedGlossary = null
    if (settings.translationGlossary) {
      try {
        parsedGlossary = typeof settings.translationGlossary === 'string'
          ? JSON.parse(settings.translationGlossary)
          : settings.translationGlossary
      } catch (error) {
        console.warn('Failed to parse translationGlossary:', error)
        parsedGlossary = settings.translationGlossary
      }
    }

    return NextResponse.json({
      settings: {
        id: settings.id,
        supportedLocales: parsedLocales,
        defaultLocale: settings.defaultLocale || defaultLocale,
        translationGlossary: parsedGlossary,
        updatedAt: settings.updatedAt,
      },
    })
  } catch (error) {
    console.error('Error fetching translation settings:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    const errorStack = error instanceof Error ? error.stack : undefined
    console.error('Error details:', { errorMessage, errorStack })
    return NextResponse.json(
      { error: 'Internal server error', details: errorMessage },
      { status: 500 }
    )
  }
}

// PUT /api/admin/settings/translation
export async function PUT(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { supportedLocales: locales, defaultLocale: defLocale, translationGlossary } =
      updateTranslationSettingsSchema.parse(body)

    const updateData: any = {}

    if (locales !== undefined) {
      updateData.supportedLocales = JSON.stringify(locales)
    }

    if (defLocale !== undefined) {
      updateData.defaultLocale = defLocale
    }

    if (translationGlossary !== undefined) {
      updateData.translationGlossary = translationGlossary
    }

    const settings = await prisma.appSettings.upsert({
      where: { id: 'default' },
      create: {
        id: 'default',
        supportedLocales: JSON.stringify(locales || supportedLocales),
        defaultLocale: defLocale || defaultLocale,
        translationGlossary: translationGlossary ? translationGlossary : Prisma.JsonNull,
      },
      update: updateData,
    })

    // Parse supportedLocales safely
    let parsedLocales = supportedLocales
    if (settings.supportedLocales) {
      try {
        parsedLocales = typeof settings.supportedLocales === 'string'
          ? JSON.parse(settings.supportedLocales)
          : (settings.supportedLocales as unknown as string[])
      } catch (error) {
        console.warn('Failed to parse supportedLocales in PUT, using default:', error)
        parsedLocales = supportedLocales
      }
    }

    // Parse translationGlossary safely
    let parsedGlossary = null
    if (settings.translationGlossary) {
      try {
        parsedGlossary = typeof settings.translationGlossary === 'string'
          ? JSON.parse(settings.translationGlossary)
          : settings.translationGlossary
      } catch (error) {
        console.warn('Failed to parse translationGlossary in PUT:', error)
        parsedGlossary = settings.translationGlossary
      }
    }

    return NextResponse.json({
      settings: {
        id: settings.id,
        supportedLocales: parsedLocales,
        defaultLocale: settings.defaultLocale || defaultLocale,
        translationGlossary: parsedGlossary,
        updatedAt: settings.updatedAt,
      },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating translation settings:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}


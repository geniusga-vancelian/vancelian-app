import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { supportedLocales, defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { Prisma } from '@prisma/client'
import { ARQUANTIX_LOCALE_COOKIE } from '@/lib/i18n/locale-server'
import {
  ARQUANTIX_SITE_I18N_COOKIE,
  encodeSiteI18nCookie,
  buildSiteI18nCookieSetOptions,
} from '@/lib/i18n/siteI18nPolicyCookie'

const updateTranslationSettingsSchema = z.object({
  supportedLocales: z.array(z.string()).optional(),
  defaultLocale: z.string().optional(),
  multilingualEnabled: z.boolean().optional(),
  translationGlossary: z
    .object({
      brandTerms: z
        .array(
          z.object({
            term: z.string(),
            keep: z.boolean(),
          }),
        )
        .optional(),
      preferred: z
        .array(
          z.object({
            from: z.string(),
            to: z.string(),
          }),
        )
        .optional(),
    })
    .optional()
    .nullable(),
})

function parseStoredLocales(raw: string | null | undefined): Locale[] {
  if (!raw) return [...supportedLocales]
  try {
    const p = JSON.parse(raw) as unknown
    if (!Array.isArray(p)) return [...supportedLocales]
    return p.filter((x): x is Locale => typeof x === 'string' && isValidLocale(x))
  } catch {
    return [...supportedLocales]
  }
}

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

    if (!settings) {
      settings = await prisma.appSettings.create({
        data: {
          id: 'default',
          supportedLocales: JSON.stringify(supportedLocales),
          defaultLocale,
          multilingualEnabled: true,
          translationGlossary: Prisma.JsonNull,
        },
      })
    }

    let parsedLocales: string[] = [...supportedLocales]
    if (settings.supportedLocales) {
      try {
        parsedLocales = typeof settings.supportedLocales === 'string'
          ? JSON.parse(settings.supportedLocales)
          : (settings.supportedLocales as unknown as string[])
        if (!Array.isArray(parsedLocales) || parsedLocales.length === 0) {
          parsedLocales = [...supportedLocales]
        }
      } catch (error) {
        console.warn('Failed to parse supportedLocales, using default:', error)
        parsedLocales = [...supportedLocales]
      }
    }

    let parsedGlossary = null
    if (settings.translationGlossary) {
      try {
        parsedGlossary =
          typeof settings.translationGlossary === 'string'
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
        multilingualEnabled: settings.multilingualEnabled !== false,
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
      { status: 500 },
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
    const {
      supportedLocales: localesBody,
      defaultLocale: defLocaleBody,
      multilingualEnabled: multiBody,
      translationGlossary,
    } = updateTranslationSettingsSchema.parse(body)

    const existing = await prisma.appSettings.findUnique({ where: { id: 'default' } })
    const prevSupported = parseStoredLocales(existing?.supportedLocales)
    const prevDefault =
      existing?.defaultLocale && isValidLocale(existing.defaultLocale)
        ? existing.defaultLocale
        : defaultLocale
    const prevMulti = existing?.multilingualEnabled !== false

    let nextSupported = prevSupported
    if (localesBody !== undefined) {
      const filtered = localesBody.filter((l): l is Locale => isValidLocale(l))
      if (filtered.length === 0) {
        return NextResponse.json(
          { error: 'At least one supported locale is required' },
          { status: 400 },
        )
      }
      nextSupported = filtered
    }

    let nextDefault = prevDefault
    if (defLocaleBody !== undefined) {
      if (!isValidLocale(defLocaleBody)) {
        return NextResponse.json({ error: 'Invalid defaultLocale' }, { status: 400 })
      }
      if (!nextSupported.includes(defLocaleBody)) {
        return NextResponse.json(
          { error: 'defaultLocale must be included in supportedLocales' },
          { status: 400 },
        )
      }
      nextDefault = defLocaleBody
    } else if (!nextSupported.includes(nextDefault)) {
      nextDefault = nextSupported[0]
    }

    const nextMulti = multiBody !== undefined ? multiBody : prevMulti

    const updatePayload: {
      supportedLocales: string
      defaultLocale: string
      multilingualEnabled: boolean
      translationGlossary?: Prisma.InputJsonValue | typeof Prisma.JsonNull
    } = {
      supportedLocales: JSON.stringify(nextSupported),
      defaultLocale: nextDefault,
      multilingualEnabled: nextMulti,
    }
    if (translationGlossary !== undefined) {
      updatePayload.translationGlossary = translationGlossary ?? Prisma.JsonNull
    }

    const settings = await prisma.appSettings.upsert({
      where: { id: 'default' },
      create: {
        id: 'default',
        supportedLocales: JSON.stringify(nextSupported),
        defaultLocale: nextDefault,
        multilingualEnabled: nextMulti,
        translationGlossary: translationGlossary ? translationGlossary : Prisma.JsonNull,
      },
      update: updatePayload,
    })

    let parsedLocales = nextSupported
    if (settings.supportedLocales) {
      try {
        parsedLocales = typeof settings.supportedLocales === 'string'
          ? JSON.parse(settings.supportedLocales)
          : (settings.supportedLocales as unknown as string[])
      } catch (error) {
        console.warn('Failed to parse supportedLocales in PUT, using default:', error)
        parsedLocales = nextSupported
      }
    }

    let parsedGlossary = null
    if (settings.translationGlossary) {
      try {
        parsedGlossary =
          typeof settings.translationGlossary === 'string'
            ? JSON.parse(settings.translationGlossary)
            : settings.translationGlossary
      } catch (error) {
        console.warn('Failed to parse translationGlossary in PUT:', error)
        parsedGlossary = settings.translationGlossary
      }
    }

    const res = NextResponse.json({
      settings: {
        id: settings.id,
        supportedLocales: parsedLocales,
        defaultLocale: settings.defaultLocale || defaultLocale,
        multilingualEnabled: settings.multilingualEnabled !== false,
        translationGlossary: parsedGlossary,
        updatedAt: settings.updatedAt,
      },
    })
    const dl =
      settings.defaultLocale && isValidLocale(settings.defaultLocale)
        ? settings.defaultLocale
        : defaultLocale
    const multi = settings.multilingualEnabled !== false
    const cookieOpts = buildSiteI18nCookieSetOptions()
    res.cookies.set(
      ARQUANTIX_SITE_I18N_COOKIE,
      encodeSiteI18nCookie({ multilingual: multi, defaultLocale: dl }),
      cookieOpts,
    )
    if (!multi) {
      res.cookies.set(ARQUANTIX_LOCALE_COOKIE, '', { path: '/', maxAge: 0, sameSite: 'lax' })
    }
    return res
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 },
      )
    }
    console.error('Error updating translation settings:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

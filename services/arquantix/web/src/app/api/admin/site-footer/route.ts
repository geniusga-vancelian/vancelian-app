import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import {
  footerJsonV2Schema,
  footerSchema,
  type FooterSocialPlatform,
} from '@/lib/sections/library'
import {
  buildFooterJsonV2AfterLocaleEdit,
  getAdminFooterLoadPayload,
  parseFooterStorage,
} from '@/lib/cms/footerStorage'

const putLocaleModeSchema = z.object({
  mode: z.literal('locale'),
  locale: z.enum(['fr', 'en', 'it']),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  block: footerSchema,
})

/**
 * GET /api/admin/site-footer — payload normalisé pour l’éditeur multilingue
 */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const row = await prisma.globalSettings.findFirst()
    const raw = row?.footerJson
    const payload = getAdminFooterLoadPayload(raw ?? {})

    return NextResponse.json(payload)
  } catch (e) {
    console.error('GET /api/admin/site-footer', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * PUT /api/admin/site-footer
 * - `mode: "locale"` : met à jour une seule langue + `defaultLocale` du document v2 (recommandé).
 * - corps plat (legacy) : compat éditeurs anciens ; fusion dans la locale par défaut si stockage v2.
 * - `version: 2` : document v2 complet (import / usages avancés).
 */
export async function PUT(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const existing = await prisma.globalSettings.findFirst()
    const existingRaw = existing?.footerJson

    let footerToStore: object

    if (body && typeof body === 'object' && (body as { mode?: unknown }).mode === 'locale') {
      const parsed = putLocaleModeSchema.parse(body)
      footerToStore = buildFooterJsonV2AfterLocaleEdit({
        existingRaw,
        locale: parsed.locale,
        defaultLocale: parsed.defaultLocale,
        block: parsed.block,
      })
    } else if (body && typeof body === 'object' && (body as { version?: unknown }).version === 2) {
      footerToStore = footerJsonV2Schema.parse(body)
    } else {
      const legacy = footerSchema.parse(body)
      const parsedExisting = parseFooterStorage(existingRaw ?? {})

      if (parsedExisting.kind === 'v2') {
        const v = parsedExisting.doc
        const dl = v.defaultLocale
        const previousBlock = v.locales[dl]
        footerToStore = buildFooterJsonV2AfterLocaleEdit({
          existingRaw,
          locale: dl,
          defaultLocale: dl,
          block: { ...(previousBlock ?? {}), ...legacy },
        })
      } else {
        footerToStore = legacy
      }
    }

    if (existing) {
      await prisma.globalSettings.update({
        where: { id: existing.id },
        data: {
          footerJson: footerToStore as object,
          updatedAt: new Date(),
        },
      })
    } else {
      await prisma.globalSettings.create({
        data: {
          siteName: 'Arquantix',
          footerJson: footerToStore as object,
        },
      })
    }

    return NextResponse.json({ ok: true, footer: footerToStore })
  } catch (e) {
    console.error('PUT /api/admin/site-footer', e)
    if (e instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid payload', details: e.issues }, { status: 400 })
    }
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

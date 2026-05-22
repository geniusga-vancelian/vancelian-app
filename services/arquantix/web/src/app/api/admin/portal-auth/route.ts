import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { portalAuthLocaleBlockSchema } from '@/lib/cms/portalAuthSchema'
import {
  buildPortalAuthJsonV2AfterLocaleEdit,
  getAdminPortalAuthLoadPayload,
} from '@/lib/cms/portalAuthStorage'

const putLocaleModeSchema = z.object({
  mode: z.literal('locale'),
  locale: z.enum(['fr', 'en', 'it']),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  resendSeconds: z.number().int().min(15).max(300),
  ssoEnabled: z.boolean(),
  block: portalAuthLocaleBlockSchema,
})

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const row = await prisma.globalSettings.findFirst({ select: { portalAuthJson: true } })
    const payload = getAdminPortalAuthLoadPayload(row?.portalAuthJson ?? null)
    return NextResponse.json(payload)
  } catch (e) {
    console.error('GET /api/admin/portal-auth', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = putLocaleModeSchema.parse(body)
    const existing = await prisma.globalSettings.findFirst()

    const portalAuthToStore = buildPortalAuthJsonV2AfterLocaleEdit({
      existingRaw: existing?.portalAuthJson ?? null,
      locale: parsed.locale,
      defaultLocale: parsed.defaultLocale,
      resendSeconds: parsed.resendSeconds,
      ssoEnabled: parsed.ssoEnabled,
      block: parsed.block,
    })

    if (existing) {
      await prisma.globalSettings.update({
        where: { id: existing.id },
        data: {
          portalAuthJson: portalAuthToStore as object,
          updatedAt: new Date(),
        },
      })
    } else {
      await prisma.globalSettings.create({
        data: {
          portalAuthJson: portalAuthToStore as object,
        },
      })
    }

    return NextResponse.json({ ok: true })
  } catch (e) {
    console.error('PUT /api/admin/portal-auth', e)
    if (e instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid payload', details: e.flatten() }, { status: 400 })
    }
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

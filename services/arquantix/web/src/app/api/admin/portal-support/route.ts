import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { portalSupportLocaleBlockSchema } from '@/lib/cms/portalSupportSchema'
import {
  buildPortalSupportJsonV2AfterLocaleEdit,
  getAdminPortalSupportLoadPayload,
} from '@/lib/cms/portalSupportStorage'

const putLocaleModeSchema = z.object({
  mode: z.literal('locale'),
  locale: z.enum(['fr', 'en', 'it']),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  block: portalSupportLocaleBlockSchema,
})

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const row = await prisma.globalSettings.findFirst({ select: { portalSupportJson: true } })
    const payload = getAdminPortalSupportLoadPayload(row?.portalSupportJson ?? null)
    return NextResponse.json(payload)
  } catch (e) {
    console.error('GET /api/admin/portal-support', e)
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

    const portalSupportToStore = buildPortalSupportJsonV2AfterLocaleEdit({
      existingRaw: existing?.portalSupportJson ?? null,
      locale: parsed.locale,
      defaultLocale: parsed.defaultLocale,
      block: parsed.block,
    })

    if (existing) {
      await prisma.globalSettings.update({
        where: { id: existing.id },
        data: {
          portalSupportJson: portalSupportToStore as object,
          updatedAt: new Date(),
        },
      })
    } else {
      await prisma.globalSettings.create({
        data: {
          portalSupportJson: portalSupportToStore as object,
        },
      })
    }

    return NextResponse.json({ ok: true })
  } catch (e) {
    console.error('PUT /api/admin/portal-support', e)
    if (e instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid payload', details: e.flatten() }, { status: 400 })
    }
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

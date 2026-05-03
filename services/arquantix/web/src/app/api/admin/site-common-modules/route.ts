import { NextRequest, NextResponse } from 'next/server'
import { randomUUID } from 'crypto'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { getSectionTypesEligibleAsCommonModule } from '@/lib/sections/library'
import {
  buildCommonModulesDocAfterCreate,
  commonModulesDocumentSchema,
  parseCommonModulesDocument,
} from '@/lib/cms/commonModulesStorage'
import { computeCommonModuleLocalesCompleteness } from '@/lib/admin/commonModuleLocaleCompleteness'

const postSchema = z.object({
  label: z.string().min(1).max(200),
  sectionKey: z.string().min(1),
  defaultLocale: z.enum(['fr', 'en', 'it']).optional(),
})

async function getOrCreateGlobalRow() {
  let row = await prisma.globalSettings.findFirst()
  if (!row) {
    row = await prisma.globalSettings.create({
      data: { siteName: 'Arquantix' },
    })
  }
  return row
}

/**
 * GET /api/admin/site-common-modules — liste courte (sélecteurs admin).
 */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const row = await prisma.globalSettings.findFirst({
      select: { commonModulesJson: true },
    })
    const doc = parseCommonModulesDocument(row?.commonModulesJson ?? null)
    const modules = doc.modules.map((m) => ({
      id: m.id,
      label: m.label,
      sectionKey: m.sectionKey,
      defaultLocale: m.defaultLocale,
      localeCompleteness: computeCommonModuleLocalesCompleteness(m),
    }))
    return NextResponse.json({ modules })
  } catch (e) {
    console.error('GET /api/admin/site-common-modules', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * POST /api/admin/site-common-modules — crée un module (type catalogue CMS + libellé).
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = postSchema.parse(await request.json())
    const eligible = getSectionTypesEligibleAsCommonModule()
    if (!eligible.some((t) => t.key === body.sectionKey)) {
      return NextResponse.json(
        { error: 'Ce type de section ne peut pas être utilisé comme module commun.' },
        { status: 400 },
      )
    }

    const dl: Locale =
      body.defaultLocale && isValidLocale(body.defaultLocale) ? body.defaultLocale : defaultLocale

    const existing = await getOrCreateGlobalRow()
    const nextDoc = buildCommonModulesDocAfterCreate({
      existingRaw: existing.commonModulesJson ?? null,
      id: randomUUID(),
      label: body.label,
      sectionKey: body.sectionKey,
      defaultLocale: dl,
    })

    const parsed = commonModulesDocumentSchema.parse(nextDoc)
    await prisma.globalSettings.update({
      where: { id: existing.id },
      data: {
        commonModulesJson: parsed as object,
        updatedAt: new Date(),
      },
    })

    const created = parsed.modules[parsed.modules.length - 1]
    return NextResponse.json({ module: created }, { status: 201 })
  } catch (e) {
    console.error('POST /api/admin/site-common-modules', e)
    if (e instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid payload', details: e.issues }, { status: 400 })
    }
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Internal server error' },
      { status: 500 },
    )
  }
}

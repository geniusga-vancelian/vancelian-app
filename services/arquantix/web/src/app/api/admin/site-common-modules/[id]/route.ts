import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { getSectionType } from '@/lib/sections/library'
import {
  buildCommonModulesDocAfterDelete,
  buildCommonModulesDocAfterDesignEdit,
  buildCommonModulesDocAfterLabelEdit,
  buildCommonModulesDocAfterLocaleEdit,
  commonModulesDocumentSchema,
  getCommonModuleById,
  normalizeCommonModuleEntry,
  parseCommonModulesDocument,
} from '@/lib/cms/commonModulesStorage'

const patchSchema = z
  .object({
    label: z.string().min(1).max(200).optional(),
    defaultLocale: z.enum(['fr', 'en', 'it']).optional(),
    mode: z.enum(['locale', 'design']).optional(),
    locale: z.enum(['fr', 'en', 'it']).optional(),
    block: z.record(z.string(), z.any()).optional(),
    designBlock: z.record(z.string(), z.any()).optional(),
  })
  .refine(
    (b) => {
      if (b.mode === 'locale') {
        return b.locale != null && b.block != null
      }
      if (b.mode === 'design') {
        return b.designBlock != null
      }
      return true
    },
    { message: 'mode locale requiert locale et block ; mode design requiert designBlock' },
  )

/**
 * GET /api/admin/site-common-modules/[id]
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const row = await prisma.globalSettings.findFirst({
      select: { commonModulesJson: true },
    })
    const doc = parseCommonModulesDocument(row?.commonModulesJson ?? null)
    const mod = getCommonModuleById(doc, params.id)
    if (!mod) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    const st = getSectionType(mod.sectionKey)
    return NextResponse.json({
      module: normalizeCommonModuleEntry(mod),
      sectionType: st
        ? { key: st.key, label: st.label, description: st.description }
        : null,
    })
  } catch (e) {
    console.error('GET /api/admin/site-common-modules/[id]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/**
 * PATCH /api/admin/site-common-modules/[id]
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = patchSchema.parse(await request.json())
    const existing = await prisma.globalSettings.findFirst()
    if (!existing) {
      return NextResponse.json({ error: 'Global settings missing' }, { status: 500 })
    }

    const doc = parseCommonModulesDocument(existing.commonModulesJson ?? null)
    const mod = getCommonModuleById(doc, params.id)
    if (!mod) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    const st = getSectionType(mod.sectionKey)
    if (!st) {
      return NextResponse.json({ error: 'Unknown section type' }, { status: 400 })
    }

    let nextDoc = doc

    if (body.mode === 'locale' && body.locale != null && body.block != null) {
      const v = st.zodSchema.safeParse(body.block)
      if (!v.success) {
        return NextResponse.json(
          { error: 'Données invalides pour ce type', details: v.error.issues },
          { status: 400 },
        )
      }
      const defaultLoc = body.defaultLocale ?? mod.defaultLocale
      nextDoc = buildCommonModulesDocAfterLocaleEdit({
        existingRaw: existing.commonModulesJson ?? null,
        moduleId: params.id,
        locale: body.locale,
        defaultLocale: defaultLoc,
        block: v.data as Record<string, unknown>,
      })
    } else if (body.mode === 'design' && body.designBlock != null) {
      try {
        nextDoc = buildCommonModulesDocAfterDesignEdit({
          existingRaw: existing.commonModulesJson ?? null,
          moduleId: params.id,
          designBlock: body.designBlock as Record<string, unknown>,
        })
      } catch (e) {
        if (e instanceof z.ZodError) {
          return NextResponse.json(
            { error: 'Données d’apparence invalides pour ce type', details: e.issues },
            { status: 400 },
          )
        }
        throw e
      }
    } else if (body.label) {
      nextDoc = buildCommonModulesDocAfterLabelEdit({
        existingRaw: existing.commonModulesJson ?? null,
        moduleId: params.id,
        label: body.label,
      })
    }

    if (body.defaultLocale != null && body.mode !== 'locale') {
      nextDoc = commonModulesDocumentSchema.parse({
        version: 1,
        modules: nextDoc.modules.map((m) =>
          m.id === params.id ? { ...m, defaultLocale: body.defaultLocale! } : m,
        ),
      })
    }

    const parsed = commonModulesDocumentSchema.parse(nextDoc)
    await prisma.globalSettings.update({
      where: { id: existing.id },
      data: {
        commonModulesJson: parsed as object,
        updatedAt: new Date(),
      },
    })

    const updated = getCommonModuleById(parsed, params.id)
    return NextResponse.json({
      module: updated ? normalizeCommonModuleEntry(updated) : null,
    })
  } catch (e) {
    console.error('PATCH /api/admin/site-common-modules/[id]', e)
    if (e instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid payload', details: e.issues }, { status: 400 })
    }
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Internal server error' },
      { status: 500 },
    )
  }
}

/**
 * DELETE /api/admin/site-common-modules/[id]
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const existing = await prisma.globalSettings.findFirst()
    if (!existing) {
      return NextResponse.json({ error: 'Global settings missing' }, { status: 500 })
    }

    const doc = parseCommonModulesDocument(existing.commonModulesJson ?? null)
    if (!getCommonModuleById(doc, params.id)) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    const nextDoc = buildCommonModulesDocAfterDelete({
      existingRaw: existing.commonModulesJson ?? null,
      moduleId: params.id,
    })
    await prisma.globalSettings.update({
      where: { id: existing.id },
      data: {
        commonModulesJson: nextDoc as object,
        updatedAt: new Date(),
      },
    })

    return NextResponse.json({ ok: true })
  } catch (e) {
    console.error('DELETE /api/admin/site-common-modules/[id]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

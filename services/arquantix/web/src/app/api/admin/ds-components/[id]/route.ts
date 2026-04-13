import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

type JsonRecord = Record<string, unknown>

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as JsonRecord
}

function extractLayoutModuleConfigs(body: JsonRecord): Array<JsonRecord> {
  return Object.entries(body)
    .filter(([k]) => k !== 'modules')
    .map(([, v]) => asRecord(v))
    .filter((v): v is JsonRecord => v !== null)
}

async function validateStrictLayoutModules(
  chapterId: string,
  schemaJson: JsonRecord
): Promise<string | null> {
  const structure = asRecord(schemaJson.structure)
  const body = asRecord(structure?.body)
  if (!body) {
    return 'structure.body must be an object'
  }
  const rawModules = body.modules
  if (!Array.isArray(rawModules)) {
    return 'body.modules must be an array of module slugs'
  }

  const modules = rawModules
    .filter((m): m is string => typeof m === 'string')
    .map((m) => m.trim())
    .filter((m) => m.length > 0)

  if (modules.length !== rawModules.length) {
    return 'body.modules must contain only non-empty string slugs'
  }

  const duplicate = modules.find((m, i) => modules.indexOf(m) !== i)
  if (duplicate) {
    return `Duplicate module slug in body.modules: "${duplicate}"`
  }

  const dsModules = await prisma.dsComponent.findMany({
    where: {
      chapterId,
      slug: { in: modules },
    },
    select: {
      slug: true,
      schemaJson: true,
    },
  })
  const bySlug = new Map(dsModules.map((m) => [m.slug, m]))

  const missing = modules.filter((slug) => !bySlug.has(slug))
  if (missing.length > 0) {
    return `Unknown module slug(s) in body.modules: ${missing.join(', ')}`
  }

  const bodyConfigs = extractLayoutModuleConfigs(body)
  for (const slug of modules) {
    const config = bodyConfigs.find((c) => c.key === slug)
    if (!config) {
      return `Missing body config object with key="${slug}"`
    }

    const layoutType = typeof config.type === 'string' ? config.type.trim() : ''
    if (!layoutType) {
      return `Missing "type" for body config key="${slug}"`
    }

    const dbSchema = asRecord(bySlug.get(slug)?.schemaJson)
    const dbWidgetType =
      typeof dbSchema?.widgetType === 'string' ? dbSchema.widgetType.trim() : ''
    if (dbWidgetType && layoutType !== dbWidgetType) {
      return `Type mismatch for "${slug}": layout="${layoutType}" db="${dbWidgetType}"`
    }
  }

  return null
}

/** GET /api/admin/ds-components/[id] — Détail d'un composant DS (admin). */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const component = await prisma.dsComponent.findUnique({
      where: { id },
      include: {
        chapter: true,
      },
    })

    if (!component) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    return NextResponse.json(component)
  } catch (e) {
    console.error('[api/admin/ds-components/[id]]', e)
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Internal error' },
      { status: 500 }
    )
  }
}

/** PUT /api/admin/ds-components/[id] — Met à jour le schemaJson d'un composant DS (admin). */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const body = (await request.json()) as { schemaJson?: unknown }

    if (!body || typeof body !== 'object' || body.schemaJson == null) {
      return NextResponse.json({ error: 'schemaJson is required' }, { status: 400 })
    }

    if (typeof body.schemaJson !== 'object' || Array.isArray(body.schemaJson)) {
      return NextResponse.json({ error: 'schemaJson must be a JSON object' }, { status: 400 })
    }

    const existing = await prisma.dsComponent.findUnique({
      where: { id },
      select: {
        id: true,
        chapterId: true,
        chapter: {
          select: { slug: true },
        },
      },
    })
    if (!existing) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    if (existing.chapter.slug === 'component_ds_flutter') {
      const root = body.schemaJson as JsonRecord
      const isLayout = root.type === 'layout'
      if (isLayout) {
        const validationError = await validateStrictLayoutModules(existing.chapterId, root)
        if (validationError) {
          return NextResponse.json(
            { error: `Layout validation error: ${validationError}` },
            { status: 400 }
          )
        }
      }
    }

    const updated = await prisma.dsComponent.update({
      where: { id },
      data: {
        schemaJson: body.schemaJson as object,
      },
      include: {
        chapter: true,
      },
    })

    return NextResponse.json(updated)
  } catch (e) {
    console.error('[api/admin/ds-components/[id] PUT]', e)
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Internal error' },
      { status: 500 }
    )
  }
}

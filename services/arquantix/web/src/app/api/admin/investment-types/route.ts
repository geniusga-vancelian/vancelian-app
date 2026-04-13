import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

function slugFromLabel(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

const colorHexSchema = z.string().regex(/^#[0-9A-Fa-f]{6}$/)

const createSchema = z.object({
  label: z.string().min(1).max(200),
  description: z.string().max(2000).optional().nullable(),
  colorHex: colorHexSchema.optional(),
  iconKey: z.string().min(1).max(100).optional(),
  sortOrder: z.number().int().optional(),
})

type InvestmentTypeRow = {
  id: string
  slug: string
  label: string
  description: string | null
  color_hex: string
  icon_key: string
  sort_order: number
  created_at: Date
  updated_at: Date
}

/** GET /api/admin/investment-types — Liste des types d'investissement (admin). */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const rows = await prisma.$queryRawUnsafe<InvestmentTypeRow[]>(
      `SELECT "id", "slug", "label", "description", "color_hex", "icon_key", "sort_order", "created_at", "updated_at"
       FROM "investment_types"
       ORDER BY "sort_order" ASC, "created_at" ASC`
    )

    return NextResponse.json({
      investmentTypes: rows.map((row) => ({
        id: row.id,
        slug: row.slug,
        label: row.label,
        description: row.description ?? null,
        colorHex: row.color_hex,
        iconKey: row.icon_key,
        sortOrder: row.sort_order,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      })),
    })
  } catch (error) {
    console.error('Error fetching investment types:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/** POST /api/admin/investment-types — Créer un type d'investissement. */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const parsed = createSchema.parse(body)
    const label = parsed.label.trim()
    const slug = slugFromLabel(label)

    const existing = await prisma.$queryRawUnsafe<Array<{ id: string }>>(
      `SELECT "id" FROM "investment_types" WHERE "slug" = $1 LIMIT 1`,
      slug
    )
    if (existing.length > 0) {
      return NextResponse.json(
        { error: 'Un type avec ce libellé (slug) existe déjà.' },
        { status: 409 }
      )
    }

    const maxOrderRows = await prisma.$queryRawUnsafe<Array<{ max_order: number | null }>>(
      `SELECT MAX("sort_order")::int AS "max_order" FROM "investment_types"`
    )
    const sortOrder =
      parsed.sortOrder ?? ((maxOrderRows[0]?.max_order ?? null) === null ? 0 : (maxOrderRows[0].max_order as number) + 1)
    const id = crypto.randomUUID()
    const colorHex = parsed.colorHex ?? '#6366F1'
    const iconKey = parsed.iconKey?.trim() || 'tag'
    const description = parsed.description?.trim() || null

    await prisma.$executeRawUnsafe(
      `INSERT INTO "investment_types" ("id", "slug", "label", "description", "color_hex", "icon_key", "sort_order", "created_at", "updated_at")
       VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())`,
      id,
      slug,
      label,
      description,
      colorHex,
      iconKey,
      sortOrder
    )

    const rows = await prisma.$queryRawUnsafe<InvestmentTypeRow[]>(
      `SELECT "id", "slug", "label", "description", "color_hex", "icon_key", "sort_order", "created_at", "updated_at"
       FROM "investment_types"
       WHERE "id" = $1
       LIMIT 1`,
      id
    )

    return NextResponse.json({
      investmentType: rows[0]
        ? {
            id: rows[0].id,
            slug: rows[0].slug,
            label: rows[0].label,
            description: rows[0].description ?? null,
            colorHex: rows[0].color_hex,
            iconKey: rows[0].icon_key,
            sortOrder: rows[0].sort_order,
            createdAt: rows[0].created_at,
            updatedAt: rows[0].updated_at,
          }
        : null,
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: error.message, details: error.flatten() }, { status: 400 })
    }
    console.error('Error creating investment type:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

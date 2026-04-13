import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

const colorHexSchema = z.string().regex(/^#[0-9A-Fa-f]{6}$/)

const updateSchema = z.object({
  label: z.string().min(1).max(200).optional(),
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

function slugFromLabel(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

function mapRow(row: InvestmentTypeRow) {
  return {
    id: row.id,
    slug: row.slug,
    label: row.label,
    description: row.description ?? null,
    colorHex: row.color_hex,
    iconKey: row.icon_key,
    sortOrder: row.sort_order,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

/** GET /api/admin/investment-types/[id] */
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
    const rows = await prisma.$queryRawUnsafe<InvestmentTypeRow[]>(
      `SELECT "id", "slug", "label", "description", "color_hex", "icon_key", "sort_order", "created_at", "updated_at"
       FROM "investment_types"
       WHERE "id" = $1
       LIMIT 1`,
      id
    )
    const row = rows[0]
    if (!row) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }
    return NextResponse.json({ investmentType: mapRow(row) })
  } catch (error) {
    console.error('Error fetching investment type:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/** PATCH /api/admin/investment-types/[id] */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const currentRows = await prisma.$queryRawUnsafe<InvestmentTypeRow[]>(
      `SELECT "id", "slug", "label", "description", "color_hex", "icon_key", "sort_order", "created_at", "updated_at"
       FROM "investment_types"
       WHERE "id" = $1
       LIMIT 1`,
      id
    )
    const current = currentRows[0]
    if (!current) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const body = await request.json()
    const parsed = updateSchema.parse(body)

    const nextLabel = parsed.label !== undefined ? parsed.label.trim() : current.label
    const nextSlug = parsed.label !== undefined ? slugFromLabel(nextLabel) : current.slug
    if (nextSlug !== current.slug) {
      const duplicate = await prisma.$queryRawUnsafe<Array<{ id: string }>>(
        `SELECT "id" FROM "investment_types" WHERE "slug" = $1 AND "id" <> $2 LIMIT 1`,
        nextSlug,
        id
      )
      if (duplicate.length > 0) {
        return NextResponse.json(
          { error: 'Un type avec ce libellé (slug) existe déjà.' },
          { status: 409 }
        )
      }
    }

    const nextDescription =
      parsed.description !== undefined ? parsed.description?.trim() || null : current.description
    const nextColorHex = parsed.colorHex !== undefined ? parsed.colorHex : current.color_hex
    const nextIconKey = parsed.iconKey !== undefined ? parsed.iconKey.trim() : current.icon_key
    const nextSortOrder = parsed.sortOrder !== undefined ? parsed.sortOrder : current.sort_order

    await prisma.$executeRawUnsafe(
      `UPDATE "investment_types"
       SET "slug" = $1,
           "label" = $2,
           "description" = $3,
           "color_hex" = $4,
           "icon_key" = $5,
           "sort_order" = $6,
           "updated_at" = NOW()
       WHERE "id" = $7`,
      nextSlug,
      nextLabel,
      nextDescription,
      nextColorHex,
      nextIconKey,
      nextSortOrder,
      id
    )

    const rows = await prisma.$queryRawUnsafe<InvestmentTypeRow[]>(
      `SELECT "id", "slug", "label", "description", "color_hex", "icon_key", "sort_order", "created_at", "updated_at"
       FROM "investment_types"
       WHERE "id" = $1
       LIMIT 1`,
      id
    )
    return NextResponse.json({ investmentType: rows[0] ? mapRow(rows[0]) : null })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: error.message, details: error.flatten() }, { status: 400 })
    }
    console.error('Error updating investment type:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

/** DELETE /api/admin/investment-types/[id] */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { id } = await params
    const existing = await prisma.$queryRawUnsafe<Array<{ id: string }>>(
      `SELECT "id" FROM "investment_types" WHERE "id" = $1 LIMIT 1`,
      id
    )
    if (existing.length === 0) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    await prisma.$executeRawUnsafe(`DELETE FROM "investment_types" WHERE "id" = $1`, id)
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting investment type:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

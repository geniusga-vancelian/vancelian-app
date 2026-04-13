import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

type InvestmentTypeRow = {
  id: string
  slug: string
  label: string
  description: string | null
  color_hex: string
  icon_key: string
  sort_order: number
}

const FALLBACK_TYPES = [
  { id: 'fallback-it-1', slug: 'crypto-assets', label: 'Crypto Assets', description: null, colorHex: '#F59E0B', iconKey: 'trending-up' },
  { id: 'fallback-it-2', slug: 'crypto-bundles', label: 'Crypto Bundles', description: null, colorHex: '#6366F1', iconKey: 'boxes' },
  { id: 'fallback-it-3', slug: 'saving-vaults', label: 'Saving Vaults', description: null, colorHex: '#10B981', iconKey: 'shield' },
  { id: 'fallback-it-4', slug: 'exclusive-offers', label: 'Exclusive offers', description: null, colorHex: '#EC4899', iconKey: 'tag' },
  { id: 'fallback-it-5', slug: 'mandates', label: 'Mandates', description: null, colorHex: '#0EA5E9', iconKey: 'file-text' },
]

/** GET /api/investment-types — Liste publique des types d'investissement. */
export async function GET() {
  try {
    const rows = await prisma.$queryRawUnsafe<InvestmentTypeRow[]>(
      `SELECT "id", "slug", "label", "description", "color_hex", "icon_key", "sort_order"
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
      })),
    })
  } catch (error) {
    console.warn('Investment types from DB failed, using fallback:', error)
    return NextResponse.json({ investmentTypes: FALLBACK_TYPES })
  }
}

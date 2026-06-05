import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { listAvailablePlatformVaultsForAdmin } from '@/lib/admin/platformVaultEngine'
import { getSessionFromCookie } from '@/lib/auth'

const querySchema = z.object({
  q: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(200).optional().default(50),
  publishedOnly: z
    .enum(['true', 'false', '1', '0'])
    .optional()
    .transform((v) => v === 'true' || v === '1'),
})

/**
 * GET /api/admin/platform-vaults/available
 * Vaults Morpho + Ledgity configurés sur la plateforme (pour liaison offre exclusive).
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const parsed = querySchema.parse({
      q: searchParams.get('q') ?? undefined,
      limit: searchParams.get('limit') ?? undefined,
      publishedOnly: searchParams.get('publishedOnly') ?? undefined,
    })

    const items = await listAvailablePlatformVaultsForAdmin({
      query: parsed.q,
      limit: parsed.limit,
      publishedOnly: parsed.publishedOnly ?? false,
    })

    return NextResponse.json({ items })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Paramètres invalides', issues: error.issues }, { status: 400 })
    }
    console.error('[api/admin/platform-vaults/available GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { fetchMorphoBaseVaultCatalog } from '@/lib/portal/morphoGraphql'

/** Catalogue Morpho Base (lecture seule) pour le picker admin. */
export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const vaults = await fetchMorphoBaseVaultCatalog()
    return NextResponse.json({ vaults })
  } catch (error) {
    console.error('[api/admin/morpho-vaults/catalog GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

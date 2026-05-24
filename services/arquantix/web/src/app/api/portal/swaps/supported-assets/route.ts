import { NextResponse } from 'next/server'

import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'

/** Catalogue swap — public côté API ; pas de session requise pour lister les actifs V1. */
export async function GET() {
  try {
    const res = await portalUpstreamFetch('/api/swaps/supported-assets', {
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/swaps/supported-assets GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

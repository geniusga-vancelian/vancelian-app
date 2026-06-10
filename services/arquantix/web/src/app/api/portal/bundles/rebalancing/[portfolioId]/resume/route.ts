import { NextRequest, NextResponse } from 'next/server'

import { parsePortalUpstreamJson, portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function POST(
  _request: NextRequest,
  { params }: { params: { portfolioId: string } },
) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const portfolioId = (params.portfolioId ?? '').trim()
    const res = await portalUpstreamFetch(
      `/api/app/bundle/${encodeURIComponent(portfolioId)}/rebalancing/resume`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: AbortSignal.timeout(120_000),
      },
    )
    const { data, parseError } = await parsePortalUpstreamJson(res)
    if (parseError) {
      console.error('[api/portal/bundles/rebalancing/resume POST] upstream parse error', parseError)
    }
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/bundles/rebalancing/resume POST]', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

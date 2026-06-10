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
      `/api/app/bundle/${encodeURIComponent(portfolioId)}/rebalancing/preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: AbortSignal.timeout(60_000),
      },
    )
    const { data, parseError } = await parsePortalUpstreamJson(res)
    if (parseError) {
      console.error(
        '[api/portal/bundles/rebalancing/preview POST] upstream parse error',
        parseError,
      )
      return NextResponse.json(
        {
          error: 'upstream_unavailable',
          message: 'Service temporairement indisponible — réessayez dans un instant.',
          upstream_status: res.status,
        },
        { status: res.status >= 400 ? res.status : 502 },
      )
    }
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/bundles/rebalancing/preview POST]', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

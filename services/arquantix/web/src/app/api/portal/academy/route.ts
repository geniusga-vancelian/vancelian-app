import { NextRequest, NextResponse } from 'next/server'

import {
  mapAcademyHubFromBlogFeed,
  mapAnalysisFromBlogFeed,
  mapVancelianNewsFromBlogFeed,
} from '@/lib/portal/mapAcademyHubFeed'
import type { PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
import { listPortalAcademyTypeArticles } from '@/lib/portal/listPortalAcademyArticles'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

async function fetchJson(url: string) {
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

export async function GET(request: NextRequest) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE

    const blogQuery = (segment: string, pageSize: number) =>
      `${bffOrigin}/api/blog?locale=${encodeURIComponent(locale)}&page=1&pageSize=${pageSize}&segment=${segment}`

    const [marketRes, companyRes, analysisRes, academyArticles] = await Promise.all([
      fetchJson(blogQuery('market', 24)),
      fetchJson(blogQuery('company', 24)),
      fetchJson(blogQuery('analysis', 24)),
      listPortalAcademyTypeArticles(locale, { origin: bffOrigin, limit: 48 }),
    ])

    const marketHub = mapAcademyHubFromBlogFeed(marketRes.data, { origin: bffOrigin })
    const vancelianNews = mapVancelianNewsFromBlogFeed(companyRes.data, { origin: bffOrigin })
    const analysis = mapAnalysisFromBlogFeed(analysisRes.data, { origin: bffOrigin })

    const payload: PortalAcademyHubPayload = {
      featured: marketHub.featured,
      highlighted: marketHub.highlighted,
      marketNews: marketHub.marketNews,
      vancelianNews,
      analysis,
      academy: academyArticles,
    }

    return NextResponse.json(payload)
  } catch (err) {
    console.error('[api/portal/academy] GET failed', err)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}

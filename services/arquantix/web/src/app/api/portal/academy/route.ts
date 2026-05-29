import { NextRequest, NextResponse } from 'next/server'
import {
  mapAcademyHubFromBlogFeed,
  mapAcademyResearchFromBlogFeed,
} from '@/lib/portal/mapAcademyHubFeed'
import type { PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
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

    const [newsRes, researchRes] = await Promise.all([
      fetchJson(
        `${bffOrigin}/api/blog?locale=${encodeURIComponent(locale)}&page=1&pageSize=24&segment=market`,
      ),
      fetchJson(
        `${bffOrigin}/api/blog?locale=${encodeURIComponent(locale)}&page=1&pageSize=12&segment=analysis`,
      ),
    ])

    const newsHub = mapAcademyHubFromBlogFeed(newsRes.data)
    const research = mapAcademyResearchFromBlogFeed(researchRes.data, { maxItems: 8 })

    const payload: PortalAcademyHubPayload = {
      ...newsHub,
      research,
      categories: newsHub.categories,
    }

    return NextResponse.json(payload)
  } catch (err) {
    console.error('[api/portal/academy] GET failed', err)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}

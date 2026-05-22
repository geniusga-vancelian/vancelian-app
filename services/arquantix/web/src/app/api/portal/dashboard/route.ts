import { NextRequest, NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { parseTop10NewsWidget } from '@/lib/portal/parseTop10NewsWidget'

async function fetchUpstreamJson(path: string) {
  const res = await portalUpstreamFetch(path, { signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

async function fetchNewsWidget(origin: string, locale: string) {
  try {
    const widgetUrl = new URL('/api/mobile/flutter/widgets/top10news', origin)
    widgetUrl.searchParams.set('locale', locale)
    const res = await fetch(widgetUrl, { next: { revalidate: 60 } })
    if (!res.ok) return null
    const raw = await res.json()
    const parsed = parseTop10NewsWidget(raw)
    if (!parsed || parsed.items.length === 0) {
      return { title: 'Vancelian News', items: [], headerHref: '/blog' }
    }
    return parsed
  } catch {
    return null
  }
}

/** Agrège les données home Flutter pour le dashboard portail (cookie httpOnly). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const locale = request.nextUrl.searchParams.get('locale')?.trim() || 'fr'
  const origin = request.nextUrl.origin

  const [
    bootstrap,
    profile,
    cash,
    globalStatistics,
    globalHistory,
    crypto,
    placements,
    notifications,
    newsWidget,
  ] = await Promise.all([
    fetchUpstreamJson('/api/app/bootstrap'),
    fetchUpstreamJson('/api/app/profile'),
    fetchUpstreamJson('/api/app/cash'),
    fetchUpstreamJson('/api/app/portfolio/global/statistics'),
    fetchUpstreamJson('/api/app/portfolio/global/history?period=ALL'),
    fetchUpstreamJson('/api/app/crypto-positions'),
    fetchUpstreamJson('/api/app/lending/earn/positions'),
    fetchUpstreamJson('/api/app/notifications/unread-count'),
    fetchNewsWidget(origin, locale),
  ])

  const partial =
    !bootstrap.ok ||
    !profile.ok ||
    !cash.ok ||
    !globalStatistics.ok ||
    !globalHistory.ok ||
    !crypto.ok ||
    !placements.ok

  return NextResponse.json({
    bootstrap: bootstrap.ok ? bootstrap.data : null,
    profile: profile.ok ? profile.data : null,
    cash: cash.ok ? cash.data : null,
    globalStatistics: globalStatistics.ok ? globalStatistics.data : null,
    globalHistory: globalHistory.ok ? globalHistory.data : null,
    crypto: crypto.ok ? crypto.data : null,
    placements: placements.ok ? placements.data : null,
    notifications: notifications.ok ? notifications.data : null,
    newsWidget,
    partial,
  })
}

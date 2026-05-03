import { NextRequest, NextResponse } from 'next/server'

import { getLocaleOrDefault } from '@/config/locales'
import { getExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'

export const dynamic = 'force-dynamic'

/**
 * GET /api/site/exclusive-offer/[pageSlug]?locale=fr
 * Données publiques détail offre (Vault Builder + lending), même source que la page `[slug]`.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { pageSlug: string } },
) {
  const slug = (params.pageSlug ?? '').trim()
  if (!slug) {
    return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
  }
  const locale = getLocaleOrDefault(
    request.nextUrl.searchParams.get('locale') || 'fr',
  )
  const payload = await getExclusiveOfferVaultPayload(slug, locale)
  if (!payload) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }
  return NextResponse.json(payload, {
    headers: {
      'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=120',
    },
  })
}

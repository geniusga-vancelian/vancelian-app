import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { resolveMapsShareLinkToEmbed } from '@/lib/maps/resolveMapsShareLink'

const bodySchema = z.object({
  url: z.string().min(8).max(4096),
})

/**
 * POST /api/admin/maps/resolve-share-link
 * Convertit un lien courts Google Maps (ex. maps.app.goo.gl/...) en URL d’iframe
 * (q=lat,lng&output=embed), sans clé API.
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const json: unknown = await request.json()
    const parsed = bodySchema.safeParse(json)
    if (!parsed.success) {
      return NextResponse.json({ error: 'Invalid body' }, { status: 400 })
    }

    const result = await resolveMapsShareLinkToEmbed(parsed.data.url)
    if (!result.ok) {
      return NextResponse.json({ ok: false, error: result.error }, { status: 422 })
    }

    return NextResponse.json({
      ok: true,
      embedUrl: result.embedUrl,
      resolvedUrl: result.resolvedUrl,
    })
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Erreur serveur'
    return NextResponse.json({ ok: false, error: message }, { status: 500 })
  }
}

/**
 * Proxy admin : `GET /api/admin/assistance/cognitive/funnel` vers FastAPI.
 *
 * Read-only, agrège les distributions cognitives (Cognitive Bot v4 — Lot 5/6).
 * Source de vérité : `services/assistance/admin_cognitive_router.py`.
 *
 * Query params supportés :
 *   - `period_days` (1..90, défaut 7) — fenêtre temporelle d'agrégation.
 */
import { NextRequest } from 'next/server'
import { forwardCognitiveRequest } from '@/lib/assistance-cognitive-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams
  return forwardCognitiveRequest('/funnel', {
    period_days: sp.get('period_days'),
  })
}

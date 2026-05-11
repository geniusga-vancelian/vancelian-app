/**
 * Proxy admin : `GET …/data-need-gaps` → FastAPI.
 * Query : `period_days` (1..90).
 */
import { NextRequest } from 'next/server'
import { forwardObservabilityRequest } from '@/lib/assistance-observability-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams
  return forwardObservabilityRequest('/data-need-gaps', {
    period_days: sp.get('period_days'),
  })
}

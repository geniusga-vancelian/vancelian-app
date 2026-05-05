/**
 * Proxy admin : `GET` (list) sur `/api/admin/assistance/conversations`
 * vers FastAPI. Read-only.
 *
 * Query params supportés :
 *   - `client_id`  (UUID pe_clients) ou `person_id` (UUID persons) — l'un OU l'autre requis
 *   - `status`     (`active` | `closed`)
 *   - `limit`, `offset` — pagination
 */
import { NextRequest } from 'next/server'
import { forwardConversationsRequest } from '@/lib/assistance-conversations-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams
  return forwardConversationsRequest('', {
    client_id: sp.get('client_id'),
    person_id: sp.get('person_id'),
    status: sp.get('status'),
    limit: sp.get('limit'),
    offset: sp.get('offset'),
  })
}

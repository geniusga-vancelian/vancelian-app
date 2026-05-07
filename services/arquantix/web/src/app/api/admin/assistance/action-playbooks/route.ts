/**
 * Proxy admin : GET (list) / POST (create) playbooks CAL.
 */
import { NextRequest } from 'next/server'
import { forwardActionPlaybooksRequest } from '@/lib/assistance-action-playbooks-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams
  return forwardActionPlaybooksRequest('/', 'GET', undefined, {
    is_enabled: sp.get('is_enabled'),
    search: sp.get('search'),
    skip: sp.get('skip'),
    limit: sp.get('limit'),
  })
}

export async function POST(request: NextRequest) {
  let body: unknown = null
  try {
    body = await request.json()
  } catch {
    body = null
  }
  return forwardActionPlaybooksRequest('/', 'POST', body)
}

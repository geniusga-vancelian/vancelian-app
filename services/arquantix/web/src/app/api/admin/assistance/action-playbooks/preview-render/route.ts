import { NextRequest } from 'next/server'
import { forwardActionPlaybooksRequest } from '@/lib/assistance-action-playbooks-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const refresh = request.nextUrl.searchParams.get('refresh')
  return forwardActionPlaybooksRequest('/preview-render', 'GET', undefined, {
    refresh: refresh ?? undefined,
  })
}

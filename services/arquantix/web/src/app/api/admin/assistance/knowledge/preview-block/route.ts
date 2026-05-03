/** Proxy admin : aperçu du bloc-catalogue tel que les agents le verront. */
import { NextRequest } from 'next/server'
import { forwardKnowledgeRequest } from '@/lib/assistance-knowledge-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const refresh = request.nextUrl.searchParams.get('refresh')
  return forwardKnowledgeRequest('/preview-block', 'GET', undefined, { refresh })
}

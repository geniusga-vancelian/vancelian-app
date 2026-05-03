/**
 * Proxy admin : `GET` (list) / `POST` (create) sur `/api/admin/assistance/knowledge`
 * vers FastAPI.
 */
import { NextRequest } from 'next/server'
import { forwardKnowledgeRequest } from '@/lib/assistance-knowledge-proxy'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams
  return forwardKnowledgeRequest('/', 'GET', undefined, {
    topic: sp.get('topic'),
    is_active: sp.get('is_active'),
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
  return forwardKnowledgeRequest('/', 'POST', body)
}

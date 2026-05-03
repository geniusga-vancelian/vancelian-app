/** Proxy admin : `GET` / `PUT` / `DELETE` sur une fiche `product_knowledge`. */
import { NextRequest } from 'next/server'
import { forwardKnowledgeRequest } from '@/lib/assistance-knowledge-proxy'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: NextRequest,
  { params }: { params: { slug: string } },
) {
  return forwardKnowledgeRequest(
    `/${encodeURIComponent(params.slug)}`,
    'GET',
  )
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { slug: string } },
) {
  let body: unknown = null
  try {
    body = await request.json()
  } catch {
    body = null
  }
  return forwardKnowledgeRequest(
    `/${encodeURIComponent(params.slug)}`,
    'PUT',
    body,
  )
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: { slug: string } },
) {
  return forwardKnowledgeRequest(
    `/${encodeURIComponent(params.slug)}`,
    'DELETE',
  )
}

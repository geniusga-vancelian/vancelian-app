import { NextRequest } from 'next/server'
import { forwardActionPlaybooksRequest } from '@/lib/assistance-action-playbooks-proxy'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: NextRequest,
  { params }: { params: { actionKey: string } },
) {
  return forwardActionPlaybooksRequest(
    `/${encodeURIComponent(params.actionKey)}`,
    'GET',
  )
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { actionKey: string } },
) {
  let body: unknown = null
  try {
    body = await request.json()
  } catch {
    body = null
  }
  return forwardActionPlaybooksRequest(
    `/${encodeURIComponent(params.actionKey)}`,
    'PUT',
    body,
  )
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: { actionKey: string } },
) {
  return forwardActionPlaybooksRequest(
    `/${encodeURIComponent(params.actionKey)}`,
    'DELETE',
  )
}

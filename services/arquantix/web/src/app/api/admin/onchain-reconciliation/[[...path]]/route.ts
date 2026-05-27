import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

async function proxy(
  request: NextRequest,
  pathSegments: string[],
  method: string,
) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const subpath = pathSegments.length ? pathSegments.join('/') : ''
  const backendPath = `/api/admin/onchain-reconciliation/${subpath}`
  const url = new URL(buildBackendUrl(backendPath))
  const incoming = new URL(request.url)
  incoming.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value)
  })

  const headers: Record<string, string> = {
    'X-Actor-Type': 'admin',
    'X-Actor-Id': session.userEmail,
    'X-Actor-Roles': 'admin',
  }

  const init: RequestInit = { method, headers, cache: 'no-store' }
  if (method !== 'GET' && method !== 'HEAD') {
    const body = await request.text()
    if (body) {
      headers['Content-Type'] = 'application/json'
      init.body = body
    }
  }

  const res = await fetch(url.toString(), init)
  const text = await res.text()
  let payload: unknown = {}
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { detail: text }
    }
  }
  return NextResponse.json(payload, { status: res.status })
}

type RouteContext = { params: Promise<{ path?: string[] }> }

export async function GET(request: NextRequest, context: RouteContext) {
  const { path = [] } = await context.params
  try {
    return proxy(request, path, 'GET')
  } catch (error) {
    console.error('[api/admin/onchain-reconciliation GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

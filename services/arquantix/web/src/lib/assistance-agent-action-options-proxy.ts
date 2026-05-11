/**
 * Proxy admin GET — `/api/admin/assistance/agent-action-options` → FastAPI.
 */
import { NextResponse } from 'next/server'
import { authorizeAndPrepareHeaders } from '@/lib/assistance-action-playbooks-proxy'
import { buildBackendUrl } from '@/lib/backend'

export const dynamic = 'force-dynamic'

const TIMEOUT_MS = 15_000

export async function forwardAgentActionOptionsGet(): Promise<NextResponse> {
  const auth = await authorizeAndPrepareHeaders()
  if (!auth.ok) return auth.response

  const url = buildBackendUrl('/api/admin/assistance/agent-action-options')

  try {
    const upstream = await fetch(url, {
      method: 'GET',
      headers: auth.headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })

    const text = await upstream.text()
    let json: unknown = null
    try {
      json = text ? JSON.parse(text) : null
    } catch {
      return new NextResponse(text, {
        status: upstream.status,
        headers: { 'Content-Type': upstream.headers.get('content-type') || 'text/plain' },
      })
    }

    return NextResponse.json(json, { status: upstream.status })
  } catch (error) {
    console.error('[assistance-agent-action-options-proxy]', error)
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 })
  }
}

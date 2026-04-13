import { NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

async function authHeaders() {
  const session = await getSessionFromCookie()
  if (!session) return null
  const signed = await signAdminBackendJwtFromSession(session)
  if (!signed.ok) return null
  return { Authorization: `Bearer ${signed.token}` }
}

export async function GET(request: Request) {
  try {
    const headers = await authHeaders()
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit')
    const query = limit ? `?limit=${encodeURIComponent(limit)}` : ''
    const res = await fetch(buildBackendUrl(`/api/market-data/cron-refresh-logs${query}`), {
      headers: headers || {},
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      return NextResponse.json(err, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { buildBackendUrl } from '@/lib/backend'

async function proxyGet(request: NextRequest, pathSegments: string[]) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const sub = pathSegments.length ? pathSegments.join('/') : ''
  const path = `/admin/security/risk-dashboard/${sub}`
  const url = new URL(buildBackendUrl(path))
  const sp = request.nextUrl.searchParams
  sp.forEach((v, k) => url.searchParams.set(k, v))

  const signed = await signAdminBackendJwtFromSession(session)
  if (!signed.ok) {
    return NextResponse.json(
      { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
      { status: 403 }
    )
  }
  const token = signed.token

  const response = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })

  const text = await response.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { raw: text }
  }
  return NextResponse.json(data, { status: response.status })
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path } = await context.params
  const segments = path ?? []
  return proxyGet(request, segments)
}

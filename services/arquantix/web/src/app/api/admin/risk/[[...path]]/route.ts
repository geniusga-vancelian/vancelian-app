import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { buildBackendUrl } from '@/lib/backend'

async function proxy(request: NextRequest, method: string, pathSegments: string[]) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const sub = pathSegments.length ? pathSegments.join('/') : ''
  const path = `/admin/risk/${sub}`
  const url = new URL(buildBackendUrl(path))
  request.nextUrl.searchParams.forEach((v, k) => url.searchParams.set(k, v))

  const signed = await signAdminBackendJwtFromSession(session)
  if (!signed.ok) {
    return NextResponse.json(
      { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
      { status: 403 }
    )
  }
  const token = signed.token

  const hasBody = !['GET', 'HEAD'].includes(method)
  const bodyText = hasBody ? await request.text() : undefined

  const response = await fetch(url.toString(), {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(bodyText ? { 'Content-Type': 'application/json' } : {}),
    },
    body: bodyText || undefined,
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
  return proxy(request, 'GET', path ?? [])
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path } = await context.params
  return proxy(request, 'POST', path ?? [])
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path } = await context.params
  return proxy(request, 'PATCH', path ?? [])
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path } = await context.params
  return proxy(request, 'PUT', path ?? [])
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) {
  const { path } = await context.params
  return proxy(request, 'DELETE', path ?? [])
}

import { getSiteOrigin } from '@/lib/metadata/siteOrigin'
import { resolvePortalAppUrl } from '@/lib/wallet/externalWalletConstants'

function isInternalBindHost(host: string): boolean {
  const hostname = host.split(':')[0]?.trim().toLowerCase() ?? ''
  return hostname === '0.0.0.0' || hostname === '127.0.0.1' || hostname === 'localhost'
}

function originFromHost(host: string, proto?: string | null): string | null {
  const trimmed = host.trim()
  if (!trimmed || isInternalBindHost(trimmed)) return null
  const scheme =
    proto?.trim() ||
    (trimmed.startsWith('localhost') || trimmed.startsWith('127.0.0.1') ? 'http' : 'https')
  return `${scheme}://${trimmed}`
}

function originFromUrl(raw: string | null | undefined): string | null {
  const trimmed = raw?.trim()
  if (!trimmed) return null
  try {
    const u = new URL(trimmed)
    if (isInternalBindHost(u.hostname)) return null
    return `${u.protocol}//${u.host}`
  } catch {
    return null
  }
}

type RequestPublicOriginInput = {
  headers: Headers
  nextUrl: { origin: string }
}

/**
 * Origine publique d'une requête API (médias mobile, canonical absolutisé).
 * En prod ECS, `request.nextUrl.origin` vaut souvent `https://0.0.0.0:3000` (bind interne).
 */
export function resolveRequestPublicOrigin(request: RequestPublicOriginInput): string | null {
  const forwardedHost = request.headers.get('x-forwarded-host')
  const forwardedProto = request.headers.get('x-forwarded-proto')
  if (forwardedHost) {
    const fromForwarded = originFromHost(forwardedHost, forwardedProto)
    if (fromForwarded) return fromForwarded
  }

  const host = request.headers.get('host')
  if (host) {
    const fromHost = originFromHost(host, forwardedProto)
    if (fromHost) return fromHost
  }

  const fromRequestOrigin = originFromUrl(request.nextUrl.origin)
  if (fromRequestOrigin) return fromRequestOrigin

  return (
    originFromUrl(resolvePortalAppUrl()) ??
    originFromUrl(getSiteOrigin()) ??
    originFromUrl(process.env.NEXT_PUBLIC_BASE_URL) ??
    null
  )
}

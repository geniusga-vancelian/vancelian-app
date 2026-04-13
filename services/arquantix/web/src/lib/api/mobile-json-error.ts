import { NextResponse } from 'next/server'

/** Clé `error` stable pour les clients mobile (ne pas exposer de détails techniques). */
export const MOBILE_API_ERROR_KEY = 'Internal server error'

const JSON_UTF8 = { 'Content-Type': 'application/json; charset=utf-8' } as const

export function mobileApiJsonError(
  status: number,
  message: string,
  errorKey: string = MOBILE_API_ERROR_KEY
): NextResponse {
  return NextResponse.json({ error: errorKey, message }, { status, headers: JSON_UTF8 })
}

/**
 * Log structuré (route, message, stack) — réservé au serveur, jamais renvoyé tel quel au mobile.
 */
export function logMobileApiFailure(
  route: string,
  err: unknown,
  extra?: Record<string, unknown>
): void {
  const message = err instanceof Error ? err.message : String(err)
  const stack = err instanceof Error ? err.stack : undefined
  console.error(`[Mobile API] ${route}`, {
    status: 500,
    ...extra,
    errMessage: message,
    stack,
  })
}

/**
 * Texte API-safe pour le champ `message` (pas de stack Prisma en prod).
 */
export function safeApiMessageForClient(err: unknown): string {
  if (process.env.NODE_ENV === 'development' && err instanceof Error) {
    return err.message.length > 240 ? `${err.message.slice(0, 240)}…` : err.message
  }
  return 'The request could not be completed.'
}

export function mobileApiFailureResponse(route: string, err: unknown): NextResponse {
  logMobileApiFailure(route, err)
  return mobileApiJsonError(500, safeApiMessageForClient(err))
}

const HTMLISH = /<(!DOCTYPE|html|head|body|pre|script)/i

/**
 * Lit le corps d'une Response fetch (proxy Python) : garantit du JSON ou lève pour catch local.
 */
export async function readProxyJsonBody(
  res: Response,
  routeTag: string
): Promise<unknown> {
  const text = await res.text()
  const trimmed = text.trim()
  if (!trimmed) {
    console.error(`[Mobile API] ${routeTag} upstream empty body`, { status: res.status })
    throw new Error('Upstream returned an empty body')
  }
  if (trimmed.startsWith('<') || HTMLISH.test(trimmed)) {
    console.error(`[Mobile API] ${routeTag} upstream HTML/non-JSON`, {
      status: res.status,
      preview: trimmed.slice(0, 400),
    })
    throw new Error('Upstream returned non-JSON body')
  }
  try {
    return JSON.parse(trimmed) as unknown
  } catch (e) {
    console.error(`[Mobile API] ${routeTag} upstream JSON parse failed`, {
      status: res.status,
      preview: trimmed.slice(0, 400),
    })
    throw e
  }
}

export function mobileApiUpstreamInvalidResponse(routeTag: string): NextResponse {
  console.error(`[Mobile API] ${routeTag} upstream invalid (non-JSON or HTML)`)
  return mobileApiJsonError(
    502,
    'The upstream service returned an invalid response. Please try again later.'
  )
}

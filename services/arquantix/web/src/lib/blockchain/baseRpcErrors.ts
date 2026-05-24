import { logMorphoSupportEvent } from '@/lib/portal/morphoBetaSupportLog'

export const BASE_RPC_USER_MESSAGE =
  'Le réseau Base est temporairement occupé. Veuillez réessayer dans quelques secondes.'

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  if (error && typeof error === 'object') {
    const row = error as Record<string, unknown>
    if (typeof row.message === 'string') return row.message
    if (typeof row.details === 'string') return row.details
    if (typeof row.shortMessage === 'string') return row.shortMessage
  }
  return ''
}

/** Erreurs RPC transitoires (rate limit, timeout, réseau). */
export function isBaseRpcTransientError(error: unknown): boolean {
  const msg = extractErrorMessage(error).toLowerCase()
  const cause = error instanceof Error ? (error as Error & { cause?: unknown }).cause : undefined
  const causeMsg = cause instanceof Error ? cause.message.toLowerCase() : String(cause ?? '').toLowerCase()
  const combined = `${msg} ${causeMsg}`

  return (
    combined.includes('rate limit') ||
    combined.includes('over rate limit') ||
    combined.includes('rpc request failed') ||
    combined.includes('429') ||
    combined.includes('timeout') ||
    combined.includes('timed out') ||
    combined.includes('network') ||
    combined.includes('econnreset') ||
    combined.includes('fetch failed') ||
    combined.includes('socket hang up')
  )
}

/** Message utilisateur — jamais l’erreur viem brute. */
export function formatBaseRpcUserMessage(error?: unknown): string {
  if (error && !isBaseRpcTransientError(error)) {
    const msg = extractErrorMessage(error)
    if (msg && !msg.toLowerCase().includes('rpc request failed')) {
      return msg
    }
  }
  return BASE_RPC_USER_MESSAGE
}

export function logBaseRpcSupportEvent(args: {
  error: unknown
  personId?: string | null
  route?: string
  metadata?: Record<string, unknown>
}): void {
  const message = extractErrorMessage(args.error) || 'Base RPC error'
  logMorphoSupportEvent({
    code: 'morpho.base_rpc_error',
    level: isBaseRpcTransientError(args.error) ? 'warning' : 'critical',
    message,
    personId: args.personId,
    metadata: {
      route: args.route,
      userMessage: BASE_RPC_USER_MESSAGE,
      ...args.metadata,
    },
  })
}

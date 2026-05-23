export type PortalExchangeError = { code?: string; message: string }

const DEFAULT_MESSAGE =
  'Impossible d’ouvrir votre session pour le moment. Réessayez dans quelques secondes.'

const ERROR_CODE_MESSAGES: Record<string, string> = {
  internal_error: DEFAULT_MESSAGE,
  exchange_failed:
    'Connexion au service d’authentification impossible. Réessayez dans quelques secondes.',
  invalid_exchange_response:
    'Réponse serveur inattendue lors de la connexion. Réessayez.',
  'privy.exchange.person_not_found':
    'Aucun compte Vancelian trouvé pour cet e-mail. Vérifiez l’adresse ou créez un compte.',
  'privy.exchange.identity_conflict':
    'Ce compte est déjà associé à un autre profil. Contactez le support.',
  'privy.token_invalid': 'Session expirée. Revenez à la connexion et recommencez.',
  'privy.token_missing': 'Session expirée. Revenez à la connexion et recommencez.',
}

function friendlyMessageForCode(code: string | undefined, explicitMessage?: string): string {
  if (explicitMessage?.trim()) return explicitMessage.trim()
  if (code && ERROR_CODE_MESSAGES[code]) return ERROR_CODE_MESSAGES[code]
  return DEFAULT_MESSAGE
}

/** Normalise les réponses BFF / FastAPI pour l’écran verify OTP. */
export function parsePortalExchangeError(data: unknown): PortalExchangeError {
  if (!data || typeof data !== 'object') {
    return { message: DEFAULT_MESSAGE }
  }

  const row = data as Record<string, unknown>
  const detail = row.detail

  if (typeof detail === 'string' && detail.trim()) {
    return { message: detail.trim() }
  }

  if (detail && typeof detail === 'object') {
    const d = detail as Record<string, unknown>
    const code = typeof d.code === 'string' ? d.code : undefined
    const message = typeof d.message === 'string' ? d.message : undefined
    return {
      code,
      message: friendlyMessageForCode(code, message),
    }
  }

  const rowMessage = typeof row.message === 'string' ? row.message : undefined
  const rowError = typeof row.error === 'string' ? row.error : undefined

  if (rowMessage?.trim()) {
    return {
      code: rowError,
      message: friendlyMessageForCode(rowError, rowMessage),
    }
  }

  if (rowError) {
    return {
      code: rowError,
      message: friendlyMessageForCode(rowError),
    }
  }

  return { message: DEFAULT_MESSAGE }
}

export function isUpstreamExchangeUnavailable(error: unknown): boolean {
  if (!(error instanceof Error)) return false
  const msg = error.message
  const cause = (error as Error & { cause?: { code?: string } }).cause
  return (
    /fetch failed|ECONNREFUSED|ENOTFOUND|ETIMEDOUT/i.test(msg) ||
    cause?.code === 'ECONNREFUSED'
  )
}

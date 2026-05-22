const LOCAL_DEV_ORIGINS = ['http://localhost:3000', 'http://localhost:3100'] as const

export function getCurrentBrowserOrigin(): string | null {
  if (typeof window === 'undefined') return null
  return window.location.origin
}

export function isPrivyOriginNotAllowedError(err: unknown): boolean {
  const message = extractPrivyErrorMessage(err)
  return /origin not allowed/i.test(message)
}

export function isPrivyInvalidNativeAppIdError(err: unknown): boolean {
  const message = extractPrivyErrorMessage(err)
  return /invalid nativeappid|invalid_native_app_id/i.test(message)
}

function extractPrivyErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message.trim()
  if (typeof err === 'object' && err !== null && 'message' in err) {
    const msg = (err as { message?: unknown }).message
    if (typeof msg === 'string') return msg.trim()
  }
  return ''
}

export function isPrivyUnauthorizedError(err: unknown): boolean {
  return /unauthorized/i.test(extractPrivyErrorMessage(err))
}

function extractPrivyErrorCode(err: unknown): string {
  if (!err || typeof err !== 'object') return ''
  const code = (err as { privyErrorCode?: unknown; type?: unknown }).privyErrorCode
  if (typeof code === 'string') return code
  const type = (err as { type?: unknown }).type
  if (typeof type === 'string') return type
  return ''
}

/** Échec captcha Privy (Turnstile) — récupérable via reset + retry. */
export function isPrivyCaptchaError(err: unknown): boolean {
  const code = extractPrivyErrorCode(err)
  if (/captcha/i.test(code)) return true
  return /captcha failed|invalid_captcha|captcha verification/i.test(
    extractPrivyErrorMessage(err),
  )
}

function isPrivyTimeoutError(err: unknown): boolean {
  const message = extractPrivyErrorMessage(err)
  if (isPrivyCaptchaError(err)) return false
  return /timeout|timed out|TimeoutError|aborted due to timeout/i.test(message)
}

function isPrivyRawFetchError(message: string): boolean {
  return /\[POST\]|\[GET\]|auth\.privy\.io|passwordless\/(authenticate|init)|<no response>/i.test(
    message,
  )
}

export type PortalPrivyAuthErrorContext = 'send-code' | 'verify-code'

/** Messages lisibles pour le portail auth (sans dump technique ofetch). */
export function formatPortalPrivyAuthError(
  err: unknown,
  context: PortalPrivyAuthErrorContext,
  fallback: string,
): string {
  if (isPrivyOriginNotAllowedError(err) || isPrivyInvalidNativeAppIdError(err)) {
    return formatPrivyConfigError(err, fallback)
  }

  if (isPrivyCaptchaError(err)) {
    return 'Security check failed. Please try again.'
  }

  if (isPrivyTimeoutError(err)) {
    return context === 'send-code'
      ? 'Unable to send the code right now. Check your connection and try again.'
      : 'Verification timed out. Try again with the code from your email, or resend a new code.'
  }

  const message = extractPrivyErrorMessage(err)
  if (isPrivyRawFetchError(message)) return fallback
  return message || fallback
}

/** Message actionnable pour les erreurs de configuration Privy côté web. */
export function formatPrivyConfigError(err: unknown, fallback: string): string {
  if (isPrivyOriginNotAllowedError(err)) {
    const origin = getCurrentBrowserOrigin() ?? 'http://localhost:3000'
    const hasWebClientId =
      typeof process !== 'undefined' &&
      Boolean(process.env.NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID?.trim())

    if (hasWebClientId) {
      return (
        `Privy refuse l’origine ${origin}. Dans le dashboard Privy, ouvrez votre app client Web ` +
        `(NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID) et ajoutez cette URL dans Allowed origins. ` +
        `Origines locales courantes : ${LOCAL_DEV_ORIGINS.join(', ')}.`
      )
    }

    return (
      `Privy refuse l’origine ${origin}. Dans le dashboard Privy → Settings → Domains, ajoutez ` +
      `${origin} dans Allowed origins (onglet Domains, pas le client mobile Flutter). ` +
      `Attendre ~1 min après sauvegarde, puis hard refresh.`
    )
  }

  if (isPrivyInvalidNativeAppIdError(err)) {
    return (
      'Configuration Privy web incorrecte : le client ID mobile Flutter ne doit pas être utilisé sur le web. ' +
      'Retirez NEXT_PUBLIC_PRIVY_APP_CLIENT_ID du .env.local et utilisez NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID ' +
      `(app client Web, Allowed origins : ${LOCAL_DEV_ORIGINS.join(', ')}).`
    )
  }

  const message = extractPrivyErrorMessage(err)
  return message || fallback
}

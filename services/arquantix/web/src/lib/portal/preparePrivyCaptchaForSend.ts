import type { PrivyCaptchaState } from '@/lib/portal/privyInternals'

type CaptchaForSend = Pick<
  PrivyCaptchaState,
  'enabled' | 'status' | 'error' | 'reset' | 'execute' | 'waitForResult'
>

const READY_POLL_INTERVAL_MS = 100
const READY_POLL_MAX_ATTEMPTS = 30 // ≈ 3s max

function isCaptchaIdle(captcha: Pick<PrivyCaptchaState, 'status'>): boolean {
  return captcha.status === 'ready' || captcha.status === 'loading'
}

async function waitNextAnimationFrames(): Promise<void> {
  return new Promise<void>((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  })
}

/**
 * Remet Turnstile sur `ready` si le token a déjà été consommé (`success`) ou en erreur.
 * Ne touche pas un widget en cours (`loading`) ni déjà prêt (`ready`).
 */
export async function preparePrivyCaptchaForSend(
  captcha: Pick<PrivyCaptchaState, 'enabled' | 'status' | 'reset'>,
): Promise<void> {
  if (!captcha.enabled) return
  if (isCaptchaIdle(captcha)) return

  captcha.reset()
  await waitNextAnimationFrames()
}

/**
 * Obtient un token Turnstile frais pour un envoi OTP.
 * Utilise un getter pour lire le status à jour (le hook Privy recrée l'objet à chaque render).
 */
export async function obtainPrivyCaptchaTokenForSend(
  getCaptcha: () => CaptchaForSend,
): Promise<string | undefined> {
  const captcha = getCaptcha()
  if (!captcha.enabled) return undefined

  await preparePrivyCaptchaForSend(captcha)

  for (let attempt = 0; attempt < READY_POLL_MAX_ATTEMPTS; attempt += 1) {
    if (isCaptchaIdle(getCaptcha())) break
    await new Promise((resolve) => setTimeout(resolve, READY_POLL_INTERVAL_MS))
  }

  const latest = getCaptcha()
  if (latest.status === 'error') {
    throw new Error(latest.error || 'Captcha failed')
  }

  latest.execute()
  return latest.waitForResult()
}

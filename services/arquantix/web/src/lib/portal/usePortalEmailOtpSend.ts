'use client'

import { useCallback, useRef } from 'react'
import { useLoginWithEmail, usePrivy } from '@privy-io/react-auth'
import { recoverPrivyEmailLoginSession } from '@/components/portal/PortalAuthPrivySessionHygiene'
import { useCaptcha, usePrivyInternal } from '@/lib/portal/privyInternals'
import { obtainPrivyCaptchaTokenForSend } from '@/lib/portal/preparePrivyCaptchaForSend'
import {
  isPrivyCaptchaError,
  isPrivyUnauthorizedError,
} from '@/lib/portal/privyConfigErrors'
import { isPortalPrivyOtpDevMockEnabled } from '@/lib/portal/privyOtpDevMockConfig'

type SendEmailOtpArgs = {
  email: string
  disableSignup: boolean
}

const MAX_CAPTCHA_RECOVERY_ATTEMPTS = 2

/**
 * Envoi initial OTP (login).
 * Obtient un token Turnstile explicite puis appelle initLoginWithEmail —
 * évite le bug Privy sendCode() qui skip le token quand status === 'success'.
 */
export function usePortalEmailOtpSend() {
  const captcha = useCaptcha()
  const captchaRef = useRef(captcha)
  captchaRef.current = captcha

  const { logout } = usePrivy()
  const { sendCode } = useLoginWithEmail()
  const { initLoginWithEmail } = usePrivyInternal()

  const getCaptcha = useCallback(() => captchaRef.current, [])

  return useCallback(
    async ({ email, disableSignup }: SendEmailOtpArgs) => {
      if (isPortalPrivyOtpDevMockEnabled()) {
        return
      }

      const dispatch = async () => {
        const current = getCaptcha()
        if (current.enabled) {
          const captchaToken = await obtainPrivyCaptchaTokenForSend(getCaptcha)
          await initLoginWithEmail({
            email,
            captchaToken,
            disableSignup,
            withPrivyUi: false,
          })
          return
        }
        await sendCode({ email, disableSignup })
      }

      let captchaAttempts = 0
      while (true) {
        try {
          await dispatch()
          return
        } catch (err) {
          if (
            isPrivyCaptchaError(err) &&
            captchaAttempts < MAX_CAPTCHA_RECOVERY_ATTEMPTS
          ) {
            captchaAttempts += 1
            getCaptcha().reset()
            await new Promise((resolve) => setTimeout(resolve, 250))
            continue
          }

          if (isPrivyUnauthorizedError(err)) {
            await recoverPrivyEmailLoginSession(logout)
            getCaptcha().reset()
            await dispatch()
            return
          }

          throw err
        }
      }
    },
    [getCaptcha, initLoginWithEmail, logout, sendCode],
  )
}

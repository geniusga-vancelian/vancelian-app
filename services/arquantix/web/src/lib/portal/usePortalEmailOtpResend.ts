'use client'

import { useCallback, useRef } from 'react'
import { useLoginWithEmail } from '@privy-io/react-auth'
import { useCaptcha, usePrivyInternal } from '@/lib/portal/privyInternals'
import {
  obtainPrivyCaptchaTokenForSend,
  preparePrivyCaptchaForSend,
} from '@/lib/portal/preparePrivyCaptchaForSend'
import {
  isPrivyCaptchaError,
  isPrivyUnauthorizedError,
} from '@/lib/portal/privyConfigErrors'

type ResendEmailOtpArgs = {
  email: string
  disableSignup: boolean
}

type EmailAuthFlow = {
  meta?: {
    email?: string
    captchaToken?: string
  }
  sendCodeEmail?: (args: {
    email?: string
    captchaToken?: string
    withPrivyUi?: boolean
  }) => Promise<unknown>
}

const MAX_CAPTCHA_RECOVERY_ATTEMPTS = 2

function getActiveEmailAuthFlow(getAuthFlow: () => unknown): EmailAuthFlow | null {
  const authFlow = getAuthFlow?.()
  if (
    !authFlow ||
    typeof authFlow !== 'object' ||
    typeof (authFlow as EmailAuthFlow).sendCodeEmail !== 'function'
  ) {
    return null
  }

  const flowEmail = (authFlow as EmailAuthFlow).meta?.email
  if (typeof flowEmail !== 'string' || !flowEmail.trim()) return null

  return authFlow as EmailAuthFlow
}

export function usePortalEmailOtpResend() {
  const captcha = useCaptcha()
  const captchaRef = useRef(captcha)
  captchaRef.current = captcha

  const { getAuthFlow } = usePrivyInternal()
  const { sendCode } = useLoginWithEmail()

  const getCaptcha = useCallback(() => captchaRef.current, [])

  return useCallback(
    async ({ email, disableSignup }: ResendEmailOtpArgs) => {
      const dispatchOnActiveFlow = async () => {
        const activeFlow = getActiveEmailAuthFlow(getAuthFlow)
        if (!activeFlow?.sendCodeEmail) return false
        const captchaToken = await obtainPrivyCaptchaTokenForSend(getCaptcha)
        await activeFlow.sendCodeEmail({
          email,
          captchaToken,
          withPrivyUi: false,
        })
        return true
      }

      const dispatchFresh = async () => {
        await preparePrivyCaptchaForSend(getCaptcha())
        await sendCode({ email, disableSignup })
      }

      let captchaAttempts = 0
      let useFreshFlow = false

      while (true) {
        try {
          if (useFreshFlow) {
            await dispatchFresh()
            return
          }
          const handled = await dispatchOnActiveFlow()
          if (handled) return
          await dispatchFresh()
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
            getCaptcha().reset()
            useFreshFlow = true
            continue
          }

          throw err
        }
      }
    },
    [getAuthFlow, getCaptcha, sendCode],
  )
}

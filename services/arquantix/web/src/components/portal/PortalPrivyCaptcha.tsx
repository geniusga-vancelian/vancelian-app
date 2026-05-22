'use client'

import * as React from 'react'
import { Captcha } from '@privy-io/react-auth'
import { useCaptcha } from '@/lib/portal/privyInternals'
import { preparePrivyCaptchaForSend } from '@/lib/portal/preparePrivyCaptchaForSend'

type PortalPrivyCaptchaContextValue = {
  prepareCaptchaForSend: () => Promise<void>
  resetCaptcha: () => void
  captchaStatus: 'disabled' | 'ready' | 'loading' | 'success' | 'error'
}

const PortalPrivyCaptchaContext = React.createContext<PortalPrivyCaptchaContextValue>({
  prepareCaptchaForSend: async () => {},
  resetCaptcha: () => {},
  captchaStatus: 'disabled',
})

export function usePortalPrivyCaptcha(): PortalPrivyCaptchaContextValue {
  return React.useContext(PortalPrivyCaptchaContext)
}

function PortalPrivyCaptchaBridge({ children }: { children: React.ReactNode }) {
  const captcha = useCaptcha()
  const captchaRef = React.useRef(captcha)
  captchaRef.current = captcha

  const getCaptcha = React.useCallback(() => captchaRef.current, [])

  // Callbacks stables — évite les useEffect en boucle sur login (captcha change à chaque render).
  const prepareCaptchaForSend = React.useCallback(async () => {
    await preparePrivyCaptchaForSend(getCaptcha())
  }, [getCaptcha])

  const resetCaptcha = React.useCallback(() => {
    const current = getCaptcha()
    if (!current.enabled) return
    if (current.status === 'ready' || current.status === 'loading') return
    current.reset()
  }, [getCaptcha])

  // Récupération discrète après erreur Turnstile — uniquement si le widget est idle.
  React.useEffect(() => {
    if (captcha.status !== 'error') return
    const timer = window.setTimeout(() => {
      const current = captchaRef.current
      if (current.status === 'error') {
        current.reset()
      }
    }, 800)
    return () => window.clearTimeout(timer)
  }, [captcha.status])

  const value = React.useMemo<PortalPrivyCaptchaContextValue>(
    () => ({
      prepareCaptchaForSend,
      resetCaptcha,
      captchaStatus: captcha.status,
    }),
    [captcha.status, prepareCaptchaForSend, resetCaptcha],
  )

  return (
    <PortalPrivyCaptchaContext.Provider value={value}>
      {children}
    </PortalPrivyCaptchaContext.Provider>
  )
}

export function PortalPrivyCaptchaProvider({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Captcha delayedExecution />
      <PortalPrivyCaptchaBridge>{children}</PortalPrivyCaptchaBridge>
    </>
  )
}

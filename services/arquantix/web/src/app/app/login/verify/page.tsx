'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useLoginWithEmail, usePrivy, useIdentityToken } from '@privy-io/react-auth'
import { PortalAuthShell } from '@/components/portal/PortalAuthShell'
import { PortalOtpInput } from '@/components/portal/PortalOtpInput'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

const RESEND_SECONDS = 45

function readStoredPrivyIdentityToken(): string | null {
  if (typeof window === 'undefined') return null
  try {
    return (
      localStorage.getItem('privy:id-token') ??
      localStorage.getItem('privy-id-token') ??
      null
    )
  } catch {
    return null
  }
}

type ExchangeError = { code?: string; message: string }

function parseExchangeError(data: unknown): ExchangeError {
  const fallback = 'Unable to open your session. Please try again.'
  if (!data || typeof data !== 'object') return { message: fallback }
  const row = data as Record<string, unknown>
  const detail = row.detail
  if (typeof detail === 'string') return { message: detail }
  if (detail && typeof detail === 'object') {
    const d = detail as Record<string, unknown>
    return {
      code: typeof d.code === 'string' ? d.code : undefined,
      message: typeof d.message === 'string' ? d.message : fallback,
    }
  }
  if (typeof row.message === 'string') return { message: row.message }
  if (typeof row.error === 'string') return { message: row.error }
  return { message: fallback }
}

function formatPrivyError(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message.trim()) {
    const msg = err.message.trim()
    if (/invalid nativeappid|invalid_native_app_id/i.test(msg)) {
      return (
        'Configuration Privy web incorrecte : le client ID mobile Flutter ne doit pas être utilisé sur le web.'
      )
    }
    return msg
  }
  if (typeof err === 'object' && err !== null && 'message' in err) {
    const msg = (err as { message?: unknown }).message
    if (typeof msg === 'string' && msg.trim()) return msg
  }
  return fallback
}

function VerifyContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = (searchParams?.get('email') ?? '').trim()
  const signUpMode = searchParams?.get('mode') === 'signup'
  const sentFromLogin = searchParams?.get('sent') === '1'

  const { ready, getAccessToken } = usePrivy()
  const { identityToken } = useIdentityToken()
  const { sendCode, loginWithCode, state } = useLoginWithEmail()

  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [sendSucceeded, setSendSucceeded] = useState(sentFromLogin)
  const [resendCountdown, setResendCountdown] = useState(sentFromLogin ? RESEND_SECONDS : 0)

  const title = signUpMode ? 'Email sign-up code' : 'Email sign-in code'

  useEffect(() => {
    if (!email) {
      router.replace(PORTAL_ROUTES.login)
    }
  }, [email, router])

  useEffect(() => {
    if (resendCountdown <= 0) return
    const timer = window.setTimeout(() => setResendCountdown((v) => v - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [resendCountdown])

  useEffect(() => {
    if (state?.status === 'error' && state.error) {
      setError(formatPrivyError(state.error, 'Unable to send the code. Please try again.'))
    }
  }, [state])

  const sendOtp = useCallback(async () => {
    if (!email || !ready) return
    setError('')
    setSending(true)
    try {
      await sendCode({ email, disableSignup: !signUpMode })
      setSendSucceeded(true)
      setResendCountdown(RESEND_SECONDS)
    } catch (err) {
      console.error('[portal/login/verify] sendCode', err)
      setError(formatPrivyError(err, 'Unable to send the code. Please try again.'))
      setSendSucceeded(false)
    } finally {
      setSending(false)
    }
  }, [email, ready, sendCode, signUpMode])

  const exchangeSession = useCallback(async () => {
    const privyToken = await getAccessToken()
    if (!privyToken) {
      throw new Error('missing_privy_token')
    }
    const privyIdentityToken = identityToken ?? readStoredPrivyIdentityToken()

    const callExchange = async (useSignUpMode: boolean) => {
      const res = await fetch('/api/portal/privy/exchange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          privy_access_token: privyToken,
          privy_identity_token: privyIdentityToken ?? undefined,
          signUpMode: useSignUpMode,
          email,
        }),
      })
      const data = await res.json().catch(() => ({}))
      return { res, data }
    }

    let { res, data } = await callExchange(signUpMode)
    if (!res.ok) {
      const err = parseExchangeError(data)
      if (!signUpMode && err.code === 'privy.exchange.person_not_found') {
        ;({ res, data } = await callExchange(true))
        if (res.ok) return
        throw new Error(parseExchangeError(data).message)
      }
      throw new Error(err.message)
    }
  }, [email, getAccessToken, identityToken, signUpMode])

  const verifyOtp = useCallback(
    async (otp: string) => {
      if (otp.length !== 6 || verifying || !ready) return
      setError('')
      setVerifying(true)
      try {
        await loginWithCode({ code: otp })
        await exchangeSession()
        router.replace(PORTAL_ROUTES.dashboard)
        router.refresh()
      } catch (err) {
        console.error('[portal/login/verify] loginWithCode', err)
        setCode('')
        setError(
          formatPrivyError(
            err,
            'The code does not match. Check the email you received.',
          ),
        )
      } finally {
        setVerifying(false)
      }
    },
    [exchangeSession, loginWithCode, ready, router, verifying],
  )

  useEffect(() => {
    if (code.length === 6) {
      void verifyOtp(code)
    }
  }, [code, verifyOtp])

  const isOtpLoading =
    !ready ||
    verifying ||
    state?.status === 'submitting-code' ||
    sending ||
    state?.status === 'sending-code'

  if (!email) return null

  return (
    <PortalAuthShell showBack backHref={PORTAL_ROUTES.login}>
      <div className="flex flex-col gap-8">
        <div className="flex flex-col gap-3 text-left">
          <h1 className="m-0 font-editorial text-[32px] font-normal leading-[1.12] text-v-fg sm:text-[36px]">
            {title}
          </h1>
          {sendSucceeded ? (
            <p className="m-0 font-ui text-[16px] leading-[1.55] text-v-fg-body">
              Code sent to <strong className="font-semibold text-v-fg">{email}</strong>
            </p>
          ) : (
            <p className="m-0 font-ui text-[16px] leading-[1.55] text-v-fg-body">
              Enter the six-digit code we sent to your inbox, or resend a new code below.
            </p>
          )}
        </div>

        {error ? (
          <p className="m-0 rounded-v-card border border-red-200 bg-red-50 px-4 py-3 font-ui text-[14px] text-red-800">
            {error}
          </p>
        ) : null}

        <PortalOtpInput
          value={code}
          onChange={setCode}
          disabled={isOtpLoading}
          loading={isOtpLoading}
          autoFocus
        />

        <div className="text-center">
          {resendCountdown > 0 ? (
            <p className="m-0 font-ui text-[14px] text-v-fg-muted">
              Resend code in {resendCountdown}s
            </p>
          ) : (
            <button
              type="button"
              disabled={isOtpLoading}
              onClick={() => void sendOtp()}
              className="border-0 bg-transparent p-0 font-ui text-[14px] font-medium text-v-terracotta underline-offset-[3px] hover:underline disabled:opacity-50"
            >
              Resend code
            </button>
          )}
        </div>
      </div>
    </PortalAuthShell>
  )
}

export default function PortalLoginVerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyContent />
    </Suspense>
  )
}

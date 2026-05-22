'use client'

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useLoginWithEmail, usePrivy, useIdentityToken } from '@privy-io/react-auth'
import { usePortalAuthContent } from '@/components/portal/PortalAuthContentProvider'
import { PortalAuthFormDeferShell } from '@/components/portal/PortalAuthFormDeferShell'
import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalVerifyFormPlaceholder } from '@/components/portal/PortalVerifyFormPlaceholder'
import { PortalOtpInput } from '@/components/portal/PortalOtpInput'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { interpolatePortalAuthTemplate } from '@/lib/cms/portal-auth'
import {
  clearPortalOtpFlow,
  markPortalOtpFlowActive,
} from '@/components/portal/PortalAuthPrivySessionHygiene'
import { formatPrivyConfigError, isPrivyUnauthorizedError } from '@/lib/portal/privyConfigErrors'

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
  if (typeof row.error === 'string') {
    return {
      message:
        row.error === 'exchange_failed'
          ? 'Connexion au serveur impossible. Réessayez dans quelques secondes.'
          : row.error,
    }
  }
  return { message: fallback }
}

function formatPrivyError(err: unknown, fallback: string): string {
  return formatPrivyConfigError(err, fallback)
}

function VerifyContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const authContent = usePortalAuthContent()
  const resendSeconds = authContent.resendSeconds
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
  const [resendCountdown, setResendCountdown] = useState(sentFromLogin ? resendSeconds : 0)

  const verifyInFlightRef = useRef(false)
  const verifySucceededRef = useRef(false)
  const otpAcceptedRef = useRef(false)
  const lastSubmittedOtpRef = useRef('')

  const title = signUpMode ? authContent.verify.signupTitle : authContent.verify.loginTitle

  const backToLoginHref = useMemo(() => {
    const params = new URLSearchParams()
    if (email) params.set('email', email)
    if (signUpMode) params.set('mode', 'signup')
    const qs = params.toString()
    return qs ? `${PORTAL_ROUTES.login}?${qs}` : PORTAL_ROUTES.login
  }, [email, signUpMode])

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

  const sendOtp = useCallback(async () => {
    if (!email || !ready) return
    setError('')
    setSending(true)
    markPortalOtpFlowActive()
    try {
      await sendCode({ email, disableSignup: !signUpMode })
      setSendSucceeded(true)
      setResendCountdown(resendSeconds)
    } catch (err) {
      console.error('[portal/login/verify] sendCode', err)
      if (isPrivyUnauthorizedError(err)) {
        clearPortalOtpFlow()
        const params = new URLSearchParams({ email })
        if (signUpMode) params.set('mode', 'signup')
        router.replace(`${PORTAL_ROUTES.login}?${params.toString()}`)
        return
      }
      setError(formatPrivyError(err, 'Unable to send the code. Please try again.'))
      setSendSucceeded(false)
      clearPortalOtpFlow()
    } finally {
      setSending(false)
    }
  }, [email, ready, resendSeconds, router, sendCode, signUpMode])

  const exchangeSession = useCallback(async () => {
    const privyToken = await getAccessToken()
    if (!privyToken) {
      throw new Error('missing_privy_token')
    }
    const callExchange = async (useSignUpMode: boolean, withIdentityToken: boolean) => {
      const res = await fetch('/api/portal/privy/exchange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          privy_access_token: privyToken,
          privy_identity_token:
            withIdentityToken && identityToken ? identityToken : undefined,
          signUpMode: useSignUpMode,
          email,
        }),
      })
      const data = await res.json().catch(() => ({}))
      return { res, data }
    }

    const runExchange = async (useSignUpMode: boolean) => {
      let attempt = await callExchange(useSignUpMode, true)
      if (!attempt.res.ok && identityToken) {
        attempt = await callExchange(useSignUpMode, false)
      }
      return attempt
    }

    let { res, data } = await runExchange(signUpMode)
    if (!res.ok) {
      const err = parseExchangeError(data)
      if (!signUpMode && err.code === 'privy.exchange.person_not_found') {
        ;({ res, data } = await runExchange(true))
        if (res.ok) return
        throw new Error(parseExchangeError(data).message)
      }
      throw new Error(err.message)
    }
  }, [email, getAccessToken, identityToken, signUpMode])

  const verifyOtp = useCallback(
    async (otp: string) => {
      if (
        otp.length !== 6 ||
        verifyInFlightRef.current ||
        verifySucceededRef.current ||
        !ready
      ) {
        return
      }

      verifyInFlightRef.current = true
      otpAcceptedRef.current = false
      setError('')
      setVerifying(true)
      try {
        await loginWithCode({ code: otp })
        otpAcceptedRef.current = true
        await exchangeSession()
        verifySucceededRef.current = true
        clearPortalOtpFlow()
        router.replace(PORTAL_ROUTES.dashboard)
        router.refresh()
      } catch (err) {
        if (verifySucceededRef.current) return

        // OTP accepté par Privy mais échange JWT échoué — retry exchange uniquement.
        if (otpAcceptedRef.current) {
          try {
            await exchangeSession()
            verifySucceededRef.current = true
            clearPortalOtpFlow()
            router.replace(PORTAL_ROUTES.dashboard)
            router.refresh()
            return
          } catch (exchangeErr) {
            console.error('[portal/login/verify] exchange after otp', exchangeErr)
            setCode('')
            lastSubmittedOtpRef.current = ''
            setError(
              exchangeErr instanceof Error
                ? exchangeErr.message
                : 'Unable to open your session. Please try again.',
            )
            return
          }
        }

        console.error('[portal/login/verify] loginWithCode', err)
        setCode('')
        lastSubmittedOtpRef.current = ''
        setError(
          formatPrivyError(
            err,
            'The code does not match. Check the email you received.',
          ),
        )
      } finally {
        verifyInFlightRef.current = false
        if (!verifySucceededRef.current) {
          setVerifying(false)
        }
      }
    },
    [exchangeSession, getAccessToken, loginWithCode, ready, router],
  )

  useEffect(() => {
    if (code.length !== 6 || code === lastSubmittedOtpRef.current) return
    lastSubmittedOtpRef.current = code
    void verifyOtp(code)
  }, [code, verifyOtp])

  const isOtpLoading =
    !ready ||
    verifying ||
    state?.status === 'submitting-code' ||
    sending ||
    state?.status === 'sending-code'

  if (!email) return null

  return (
    <>
      <div className="portal-auth__form">
        <header className="portal-auth__intro">
          <h2 className="portal-auth__form-title" id="portal-auth-form-title">
            {title}
          </h2>
          {sendSucceeded ? (
            <p className="portal-auth__form-body">
              {authContent.verify.bodySent.includes('{email}') ? (
                <>
                  {authContent.verify.bodySent.split('{email}')[0]}
                  <strong className="font-semibold text-v-fg">{email}</strong>
                  {authContent.verify.bodySent.split('{email}').slice(1).join('{email}')}
                </>
              ) : (
                interpolatePortalAuthTemplate(authContent.verify.bodySent, { email })
              )}
            </p>
          ) : (
            <p className="portal-auth__form-body">{authContent.verify.bodyPending}</p>
          )}
        </header>

        <PortalOtpInput
          value={code}
          onChange={setCode}
          disabled={isOtpLoading}
          loading={isOtpLoading}
          autoFocus
        />

        <div className="text-center">
          {resendCountdown > 0 ? (
            <p className="portal-auth__helper">
              {interpolatePortalAuthTemplate(authContent.verify.resendCountdown, {
                seconds: resendCountdown,
              })}
            </p>
          ) : (
            <button
              type="button"
              disabled={isOtpLoading}
              onClick={() => void sendOtp()}
              className="portal-auth__link disabled:opacity-50"
            >
              {authContent.verify.resendLabel}
            </button>
          )}
        </div>

        <p className="portal-auth__helper">
          {authContent.verify.wrongEmailHelper}{' '}
          <Link href={backToLoginHref} className="portal-auth__link">
            {signUpMode
              ? authContent.verify.backToSignupLabel
              : authContent.verify.backToLoginLabel}
          </Link>
        </p>

        {error ? <p className="portal-auth__error">{error}</p> : null}
      </div>
    </>
  )
}

export default function PortalLoginVerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyGate />
    </Suspense>
  )
}

function VerifyGate() {
  const { privyReady } = usePortalAuthPrivy()

  return (
    <PortalAuthFormDeferShell loading={!privyReady}>
      {privyReady ? <VerifyContent /> : <PortalVerifyFormPlaceholder />}
    </PortalAuthFormDeferShell>
  )
}

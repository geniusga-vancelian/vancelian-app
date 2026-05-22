'use client'

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useLoginWithEmail, usePrivy } from '@privy-io/react-auth'
import { Loader2 } from 'lucide-react'
import { PortalAuthSsoSection } from '@/components/portal/PortalAuthSsoSection'
import { usePortalAuthContent } from '@/components/portal/PortalAuthContentProvider'
import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalLoginFormPlaceholder } from '@/components/portal/PortalLoginFormPlaceholder'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { isPrivyConfigured } from '@/lib/portal/privyConfig'
import {
  clearPortalOtpFlow,
  markPortalOtpFlowActive,
} from '@/components/portal/PortalAuthPrivySessionHygiene'
import { formatPrivyConfigError } from '@/lib/portal/privyConfigErrors'

function formatPrivyError(err: unknown): string {
  return formatPrivyConfigError(
    err,
    'Unable to send the code. Please try again.',
  )
}

function PortalLoginForm({ initialEmail = '' }: { initialEmail?: string }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const authContent = usePortalAuthContent()
  const { ready } = usePrivy()
  const { sendCode, state } = useLoginWithEmail()

  const [email, setEmail] = useState(initialEmail || searchParams?.get('email') || '')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const signUpMode = searchParams?.get('mode') === 'signup'

  useEffect(() => {
    router.prefetch(PORTAL_ROUTES.loginVerify)
  }, [router])

  const setAuthMode = useCallback(
    (signup: boolean) => {
      const params = new URLSearchParams(searchParams?.toString() ?? '')
      if (signup) params.set('mode', 'signup')
      else params.delete('mode')
      const storedEmail = params.get('email')
      if (storedEmail) params.set('email', storedEmail)
      const qs = params.toString()
      router.replace(qs ? `${PORTAL_ROUTES.login}?${qs}` : PORTAL_ROUTES.login, { scroll: false })
    },
    [router, searchParams],
  )

  const copy = useMemo(
    () =>
      signUpMode
        ? {
            title: authContent.signup.title,
            body: authContent.signup.body,
            submit: authContent.signup.submitLabel,
            helper: authContent.signup.helperText,
            switchLabel: authContent.signup.switchLabel,
            switchToSignup: false,
          }
        : {
            title: authContent.login.title,
            body: authContent.login.body,
            submit: authContent.login.submitLabel,
            helper: authContent.login.helperText,
            switchLabel: authContent.login.switchLabel,
            switchToSignup: true,
          },
    [authContent, signUpMode],
  )

  const emailOk = useMemo(() => {
    const e = email.trim()
    if (!e.includes('@')) return false
    const parts = e.split('@')
    return parts.length === 2 && parts[1].length > 0
  }, [email])

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    if (!emailOk) {
      setError('Please enter a valid email address.')
      return
    }
    if (!isPrivyConfigured()) {
      setError('Email sign-in is unavailable (Privy is not configured for this build).')
      return
    }
    if (!ready) {
      setError('Authentication is still loading. Please wait a moment and try again.')
      return
    }

    setSubmitting(true)
    markPortalOtpFlowActive()
    try {
      await sendCode({ email: email.trim(), disableSignup: !signUpMode })
      const params = new URLSearchParams({
        email: email.trim(),
        sent: '1',
        ...(signUpMode ? { mode: 'signup' } : {}),
      })
      router.push(`${PORTAL_ROUTES.loginVerify}?${params.toString()}`)
      // Garder le bouton en chargement jusqu’au démontage (navigation vers verify).
    } catch (err) {
      console.error('[portal/login] sendCode', err)
      clearPortalOtpFlow()
      setError(formatPrivyError(err))
      setSubmitting(false)
    }
  }

  const isSendingCode = state?.status === 'sending-code'
  const isBusy = submitting || isSendingCode || !ready

  return (
    <>
      <form className="portal-auth__form" onSubmit={(e) => void onSubmit(e)} noValidate>
        <header className="portal-auth__intro">
          <h2 className="portal-auth__form-title" id="portal-auth-form-title">
            {copy.title}
          </h2>
          <p className="portal-auth__form-body">{copy.body}</p>
        </header>

        {error ? <p className="portal-auth__error">{error}</p> : null}

        <div className="portal-auth__field">
          <input
            className="portal-auth__input"
            id="portal-email"
            name="email"
            type="email"
            required
            autoComplete="email"
            inputMode="email"
            spellCheck={false}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder=" "
          />
          <label className="portal-auth__label" htmlFor="portal-email">
            {authContent.login.emailLabel}
          </label>
        </div>

        <button
          className="portal-auth__btn portal-auth__btn--primary portal-auth__btn--lg portal-auth__btn--block"
          type="submit"
          disabled={!emailOk || isBusy}
          aria-busy={isBusy || undefined}
        >
          <span>{copy.submit}</span>
          {isBusy ? (
            <Loader2 className="portal-auth__btn-loader h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <span className="portal-auth__btn-arrow" aria-hidden="true">
              →
            </span>
          )}
          {isBusy ? <span className="sr-only">Sending code</span> : null}
        </button>

        <PortalAuthSsoSection ssoEnabled={authContent.ssoEnabled} login={authContent.login} />

        <p className="portal-auth__helper">
          {copy.helper}{' '}
          <button
            type="button"
            className="portal-auth__link"
            onClick={() => setAuthMode(copy.switchToSignup)}
          >
            {copy.switchLabel}
          </button>
        </p>
      </form>
    </>
  )
}

function PortalLoginPageGate() {
  const { privyReady } = usePortalAuthPrivy()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState(searchParams?.get('email') ?? '')

  if (!privyReady) {
    return (
      <PortalLoginFormPlaceholder
        email={email}
        setEmail={setEmail}
        submitDisabled
      />
    )
  }

  return <PortalLoginForm initialEmail={email} />
}

export default function PortalLoginPage() {
  return (
    <Suspense fallback={null}>
      <PortalLoginPageGate />
    </Suspense>
  )
}

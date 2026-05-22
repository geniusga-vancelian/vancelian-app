'use client'

import { useCallback, useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { PortalAuthSsoSection } from '@/components/portal/PortalAuthSsoSection'
import { usePortalAuthContent } from '@/components/portal/PortalAuthContentProvider'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  email: string
  setEmail: (value: string) => void
  onActivate?: () => void
  submitDisabled?: boolean
}

/** Formulaire login sans Privy — first paint instantané, active Privy au focus/submit. */
export function PortalLoginFormPlaceholder({
  email,
  setEmail,
  onActivate,
  submitDisabled = false,
}: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const authContent = usePortalAuthContent()
  const signUpMode = searchParams?.get('mode') === 'signup'

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

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!emailOk) return
    onActivate?.()
  }

  return (
    <>
      <form className="portal-auth__form" onSubmit={onSubmit} noValidate>
        <header className="portal-auth__intro">
          <h2 className="portal-auth__form-title" id="portal-auth-form-title">
            {copy.title}
          </h2>
          <p className="portal-auth__form-body">{copy.body}</p>
        </header>

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
            onFocus={() => onActivate?.()}
            placeholder=" "
          />
          <label className="portal-auth__label" htmlFor="portal-email">
            {authContent.login.emailLabel}
          </label>
        </div>

        <button
          className="portal-auth__btn portal-auth__btn--primary portal-auth__btn--lg portal-auth__btn--block"
          type="submit"
          disabled={!emailOk || submitDisabled}
        >
          <span>{copy.submit}</span>
          <span className="portal-auth__btn-arrow" aria-hidden="true">
            →
          </span>
        </button>

        <PortalAuthSsoSection
          ssoEnabled={authContent.ssoEnabled}
          login={authContent.login}
          onSsoClick={onActivate}
        />

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

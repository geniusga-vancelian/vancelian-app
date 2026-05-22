'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { usePortalAuthContent } from '@/components/portal/PortalAuthContentProvider'
import { interpolatePortalAuthTemplate } from '@/lib/cms/portal-auth'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Écran verify statique — visible pendant le boot Privy en arrière-plan. */
export function PortalVerifyFormPlaceholder() {
  const searchParams = useSearchParams()
  const authContent = usePortalAuthContent()
  const email = (searchParams?.get('email') ?? '').trim()
  const signUpMode = searchParams?.get('mode') === 'signup'
  const sentFromLogin = searchParams?.get('sent') === '1'
  const title = signUpMode ? authContent.verify.signupTitle : authContent.verify.loginTitle

  const backToLoginHref = useMemo(() => {
    const params = new URLSearchParams()
    if (email) params.set('email', email)
    if (signUpMode) params.set('mode', 'signup')
    const qs = params.toString()
    return qs ? `${PORTAL_ROUTES.login}?${qs}` : PORTAL_ROUTES.login
  }, [email, signUpMode])

  if (!email) return null

  return (
    <>
      <div className="portal-auth__form">
        <header className="portal-auth__intro">
          <h2 className="portal-auth__form-title" id="portal-auth-form-title">
            {title}
          </h2>
          {sentFromLogin ? (
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

        <div className="portal-auth__otp-placeholder" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <span key={index} className="portal-auth__otp-placeholder-cell" />
          ))}
        </div>

        <p className="portal-auth__helper">
          {authContent.verify.wrongEmailHelper}{' '}
          <Link href={backToLoginHref} className="portal-auth__link">
            {signUpMode
              ? authContent.verify.backToSignupLabel
              : authContent.verify.backToLoginLabel}
          </Link>
        </p>
      </div>
    </>
  )
}

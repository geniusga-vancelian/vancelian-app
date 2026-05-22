'use client'

import type { PortalAuthContent } from '@/lib/cms/portal-auth'

type Props = {
  ssoEnabled: boolean
  login: PortalAuthContent['login']
  onSsoClick?: () => void
}

/** Bloc OR + boutons SSO (Google + Apple) — rendu uniquement si activé dans le CMS. */
export function PortalAuthSsoSection({ ssoEnabled, login, onSsoClick }: Props) {
  if (!ssoEnabled) return null

  return (
    <>
      <div className="portal-auth__or" role="separator" aria-label={login.orSeparator}>
        {login.orSeparator}
      </div>

      <div className="portal-auth__sso">
        <button
          className="portal-auth__btn portal-auth__btn--sso portal-auth__btn--lg portal-auth__btn--block"
          type="button"
          onClick={onSsoClick}
        >
          <span className="portal-auth__sso-mark" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={login.ssoGoogleIconSrc} alt="" />
          </span>
          <span>{login.ssoGoogleLabel}</span>
        </button>
        <button
          className="portal-auth__btn portal-auth__btn--sso portal-auth__btn--lg portal-auth__btn--block"
          type="button"
          onClick={onSsoClick}
        >
          <span className="portal-auth__sso-mark" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={login.ssoAppleIconSrc} alt="" />
          </span>
          <span>{login.ssoAppleLabel}</span>
        </button>
      </div>
    </>
  )
}

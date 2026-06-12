'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, ShieldCheck, Zap } from 'lucide-react'
import { useLoginWithEmail, usePrivy } from '@privy-io/react-auth'

import { PortalOtpInput } from '@/components/portal/PortalOtpInput'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { formatPortalPrivyAuthError } from '@/lib/portal/privyConfigErrors'
import {
  isPortalPrivyOtpDevMockCode,
  portalPrivyOtpDevMockCode,
} from '@/lib/portal/privyOtpDevMock'
import { isPortalPrivyOtpDevMockEnabled } from '@/lib/portal/privyOtpDevMockConfig'
import { usePortalEmailOtpSend } from '@/lib/portal/usePortalEmailOtpSend'
import { usePortalWalletDelegation } from '@/lib/portal/usePortalWalletDelegation'
import { cn } from '@/lib/utils'

type ProfileEmail = { email?: string }

/**
 * Activation/désactivation de l'exécution automatique (Privy Session Signers).
 *
 * Vit sous `PortalWeb3Boundary` (Privy monté) — contrairement au profil. Si la
 * session SDK Privy n'est pas active, on l'établit d'abord par code e-mail
 * (même flux que la création de wallet), puis on délègue/révoque le wallet
 * embedded au signer serveur Vancelian.
 */
export function PortalAutoTradingScreen() {
  const { ready, authenticated } = usePrivy()
  const { loginWithCode, state } = useLoginWithEmail()
  const sendEmailOtp = usePortalEmailOtpSend()
  const {
    isConfigured,
    isDelegated,
    canDelegate,
    canRevoke,
    isPending,
    error: delegationError,
    delegate,
    revoke,
  } = usePortalWalletDelegation()

  const [profileEmail, setProfileEmail] = useState('')
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [error, setError] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [sendingOtp, setSendingOtp] = useState(false)
  const [verifyingOtp, setVerifyingOtp] = useState(false)
  const [privyMockAuthed, setPrivyMockAuthed] = useState(false)

  const privyOtpDevMock = isPortalPrivyOtpDevMockEnabled()
  const needsPrivyAuth = ready && !authenticated && !privyMockAuthed

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/portal/profile', { cache: 'no-store' })
        if (!res.ok) return
        const payload = (await res.json()) as { profile?: ProfileEmail }
        const email =
          typeof payload.profile?.email === 'string' ? payload.profile.email.trim() : ''
        if (!cancelled) setProfileEmail(email)
      } finally {
        if (!cancelled) setLoadingProfile(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const sendPrivyOtp = useCallback(async () => {
    if (!profileEmail || sendingOtp || !ready) return
    setError('')
    setSendingOtp(true)
    try {
      await sendEmailOtp({ email: profileEmail, disableSignup: true })
      setOtpSent(true)
      setOtpCode('')
    } catch (err) {
      setError(formatPortalPrivyAuthError(err, 'send-code', 'Envoi du code impossible.'))
    } finally {
      setSendingOtp(false)
    }
  }, [profileEmail, ready, sendEmailOtp, sendingOtp])

  useEffect(() => {
    if (!needsPrivyAuth || !profileEmail || otpSent || sendingOtp) return
    void sendPrivyOtp()
  }, [needsPrivyAuth, otpSent, profileEmail, sendPrivyOtp, sendingOtp])

  useEffect(() => {
    if (!needsPrivyAuth || otpCode.length !== 6 || verifyingOtp) return
    setVerifyingOtp(true)
    setError('')
    void (async () => {
      try {
        if (privyOtpDevMock && isPortalPrivyOtpDevMockCode(otpCode)) {
          setPrivyMockAuthed(true)
          setOtpCode('')
          return
        }
        await loginWithCode({ code: otpCode })
      } catch (err) {
        setOtpCode('')
        setError(formatPortalPrivyAuthError(err, 'verify-code', 'Code incorrect. Réessayez.'))
      } finally {
        setVerifyingOtp(false)
      }
    })()
  }, [loginWithCode, needsPrivyAuth, otpCode, privyOtpDevMock, verifyingOtp])

  const otpBusy =
    verifyingOtp ||
    sendingOtp ||
    state?.status === 'submitting-code' ||
    state?.status === 'sending-code'

  const subtitle = isDelegated
    ? 'Vancelian peut exécuter vos ordres automatiquement, sans signature à chaque fois.'
    : 'Autorisez Vancelian à exécuter vos ordres sans signer à chaque fois. Vos fonds restent en auto-conservation.'

  const title = useMemo(() => {
    if (needsPrivyAuth) return 'Confirmez votre e-mail'
    return 'Exécution automatique'
  }, [needsPrivyAuth])

  if (!isConfigured) {
    return (
      <PortalPageContainer className="py-8 sm:py-10">
        <div className="mx-auto w-full max-w-lg">
          <div className="rounded-v-card border border-v-fg-10 bg-v-card p-6 shadow-v-subtle sm:p-8">
            <h1 className="m-0 font-ui text-[24px] font-semibold tracking-v-tight text-v-fg">
              Exécution automatique
            </h1>
            <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              Fonctionnalité non disponible pour le moment.
            </p>
          </div>
        </div>
      </PortalPageContainer>
    )
  }

  if (loadingProfile || !ready) {
    return (
      <PortalPageContainer className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" aria-hidden />
        <span className="sr-only">Chargement</span>
      </PortalPageContainer>
    )
  }

  return (
    <PortalPageContainer className="py-8 sm:py-10">
      <div className="mx-auto w-full max-w-lg">
        <div className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card p-6 shadow-v-subtle sm:p-8">
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-v-fg-05">
            {needsPrivyAuth ? (
              <ShieldCheck className="h-6 w-6 text-v-fg" aria-hidden />
            ) : (
              <Zap className="h-6 w-6 text-v-fg" aria-hidden />
            )}
          </div>

          <h1 className="m-0 font-ui text-[24px] font-semibold tracking-v-tight text-v-fg">
            {title}
          </h1>

          {needsPrivyAuth ? (
            <>
              <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
                {privyOtpDevMock ? (
                  <>
                    Mode test local : saisissez le code{' '}
                    <strong className="font-semibold text-v-fg">
                      {portalPrivyOtpDevMockCode() ?? '111111'}
                    </strong>{' '}
                    pour activer la session.
                  </>
                ) : (
                  <>
                    Pour autoriser l&apos;exécution automatique en toute sécurité, confirmez le code
                    envoyé à{' '}
                    <strong className="font-semibold text-v-fg">
                      {profileEmail || 'votre e-mail'}
                    </strong>
                    .
                  </>
                )}
              </p>
              <div className="mt-8 space-y-4">
                <PortalOtpInput
                  value={otpCode}
                  onChange={setOtpCode}
                  disabled={otpBusy || !otpSent}
                  loading={otpBusy}
                  autoFocus
                />
                <button
                  type="button"
                  className="portal-auth__link disabled:opacity-50"
                  disabled={otpBusy || !profileEmail}
                  onClick={() => void sendPrivyOtp()}
                >
                  Renvoyer le code
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
                {subtitle}
              </p>

              <div className="mt-8 flex items-center justify-between gap-4 rounded-v-card border border-v-fg-10 bg-v-bg px-4 py-4">
                <div className="flex items-center gap-3">
                  <Zap className="h-6 w-6 text-v-fg" strokeWidth={1.75} aria-hidden />
                  <span className="font-ui text-[16px] font-medium text-v-fg">
                    Trading automatique
                  </span>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={isDelegated}
                  aria-label={
                    isDelegated
                      ? "Désactiver l'exécution automatique"
                      : "Activer l'exécution automatique"
                  }
                  disabled={isPending || (!canDelegate && !canRevoke)}
                  onClick={() => {
                    if (isDelegated) {
                      if (canRevoke) void revoke()
                    } else if (canDelegate) {
                      void delegate()
                    }
                  }}
                  className={cn(
                    'relative h-7 w-12 shrink-0 rounded-v-pill border-0 transition-colors duration-v-fast disabled:cursor-default',
                    isDelegated ? 'bg-v-fg' : 'bg-v-fg-20',
                    isPending && 'opacity-60',
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-v-subtle transition-transform duration-v-fast',
                      isDelegated ? 'translate-x-[22px]' : 'translate-x-0.5',
                    )}
                  />
                </button>
              </div>

              {isPending ? (
                <p className="mt-4 mb-0 flex items-center gap-2 font-ui text-[13px] text-v-fg-muted">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Confirmation Privy en cours…
                </p>
              ) : null}

              {!canDelegate && !canRevoke ? (
                <p className="mt-4 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
                  {privyOtpDevMock
                    ? 'Mode test local : la délégation réelle nécessite une session Privy réelle (pas de mock). Le flux d’activation est néanmoins exerçable ici.'
                    : 'Activez d’abord votre wallet Vancelian depuis « Mon wallet » (code e-mail), puis revenez ici.'}
                </p>
              ) : (
                <p className="mt-4 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
                  Vous pouvez révoquer cette autorisation à tout moment depuis cet écran.
                </p>
              )}
            </>
          )}

          {error || delegationError ? (
            <p className="portal-auth__error mt-6">{error || delegationError}</p>
          ) : null}
        </div>
      </div>
    </PortalPageContainer>
  )
}

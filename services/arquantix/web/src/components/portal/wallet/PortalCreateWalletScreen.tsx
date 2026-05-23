'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, ShieldCheck, Wallet } from 'lucide-react'
import { useRouter } from 'next/navigation'
import {
  useCreateWallet,
  useIdentityToken,
  useLoginWithEmail,
  usePrivy,
  useWallets,
} from '@privy-io/react-auth'
import { PortalOtpInput } from '@/components/portal/PortalOtpInput'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Button } from '@/components/ui/button'
import { PORTAL_ROUTES, resolvePortalDepositHref } from '@/lib/portal/portalRouting'
import { fetchPortalPersonCryptoWallets } from '@/lib/portal/privyWalletClient'
import { runPortalPrivyWalletCompletion } from '@/lib/portal/runPortalPrivyWalletCompletion'
import { usePortalEmailOtpSend } from '@/lib/portal/usePortalEmailOtpSend'
import { formatPortalPrivyAuthError } from '@/lib/portal/privyConfigErrors'

type ProfileEmail = {
  email?: string
}

export function PortalCreateWalletScreen() {
  const router = useRouter()
  const { ready, authenticated, user, getAccessToken } = usePrivy()
  const { identityToken } = useIdentityToken()
  const { wallets } = useWallets()
  const { createWallet } = useCreateWallet()
  const sendEmailOtp = usePortalEmailOtpSend()
  const { loginWithCode, state } = useLoginWithEmail()

  const [profileEmail, setProfileEmail] = useState('')
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [checkingWallet, setCheckingWallet] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [otpCode, setOtpCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [sendingOtp, setSendingOtp] = useState(false)
  const [verifyingOtp, setVerifyingOtp] = useState(false)

  const needsPrivyAuth = ready && !authenticated

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

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const rows = await fetchPortalPersonCryptoWallets()
        if (cancelled) return
        if (rows.length > 0) {
          router.replace(resolvePortalDepositHref(true))
        }
      } catch {
        /* ignore — page still usable */
      } finally {
        if (!cancelled) setCheckingWallet(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [router])

  const sendPrivyOtp = useCallback(async () => {
    if (!profileEmail || sendingOtp || !ready) return
    setError('')
    setSendingOtp(true)
    try {
      await sendEmailOtp({ email: profileEmail, disableSignup: true })
      setOtpSent(true)
      setOtpCode('')
    } catch (err) {
      setError(
        formatPortalPrivyAuthError(err, 'send-code', 'Unable to send the verification code.'),
      )
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
        await loginWithCode({ code: otpCode })
      } catch (err) {
        setOtpCode('')
        setError(
          formatPortalPrivyAuthError(err, 'verify-code', 'The code does not match. Try again.'),
        )
      } finally {
        setVerifyingOtp(false)
      }
    })()
  }, [loginWithCode, needsPrivyAuth, otpCode, verifyingOtp])

  const findEmbeddedWallet = useCallback(() => {
    const embedded = wallets.find((w) => w.type === 'ethereum' && w.address)
    if (!embedded?.address) return null
    return {
      address: embedded.address,
      chainId: embedded.chainId,
      walletType: 'embedded',
    }
  }, [wallets])

  const privyEmbeddedWallet = authenticated ? findEmbeddedWallet() : null
  const isSyncMode = Boolean(privyEmbeddedWallet)

  const onCreateWallet = useCallback(async () => {
    if (creating || !ready || !authenticated) return
    setError('')
    setCreating(true)
    try {
      const result = await runPortalPrivyWalletCompletion({
        getPrivyUserId: () => user?.id ?? null,
        getAccessToken,
        getIdentityToken: () => identityToken ?? null,
        findExistingEmbeddedWallet: findEmbeddedWallet,
        createEmbeddedWallet: async () => {
          const existing = findEmbeddedWallet()
          if (existing?.address) return existing
          try {
            const wallet = await createWallet()
            return {
              address: wallet.address,
              walletType: 'embedded',
            }
          } catch (err) {
            // Wallet déjà créé côté Privy (ex. clic précédent avant sync backend).
            const recovered = findEmbeddedWallet()
            if (recovered?.address) return recovered
            throw err
          }
        },
      })

      if (result === 'already_exists') {
        router.replace(resolvePortalDepositHref(true))
        return
      }

      router.replace(`${PORTAL_ROUTES.cryptoWallet}?wallet_created=1`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create your wallet. Try again.')
    } finally {
      setCreating(false)
    }
  }, [
    authenticated,
    createWallet,
    creating,
    findEmbeddedWallet,
    getAccessToken,
    identityToken,
    ready,
    router,
    user?.id,
  ])

  const busy = loadingProfile || checkingWallet || !ready
  const otpBusy =
    verifyingOtp || sendingOtp || state?.status === 'submitting-code' || state?.status === 'sending-code'

  const title = useMemo(() => {
    if (needsPrivyAuth) return 'Confirm your email'
    if (isSyncMode) return 'Link your crypto wallet'
    return 'Create your crypto wallet'
  }, [isSyncMode, needsPrivyAuth])

  if (busy) {
    return (
      <PortalPageContainer className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" aria-hidden />
        <span className="sr-only">Loading</span>
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
              <Wallet className="h-6 w-6 text-v-fg" aria-hidden />
            )}
          </div>

          <h1 className="m-0 font-ui text-[24px] font-semibold tracking-v-tight text-v-fg">{title}</h1>

          {needsPrivyAuth ? (
            <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              To create your embedded EVM wallet securely, confirm the code sent to{' '}
              <strong className="font-semibold text-v-fg">{profileEmail || 'your email'}</strong>.
            </p>
          ) : isSyncMode ? (
            <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              Your embedded wallet already exists on Privy
              {privyEmbeddedWallet?.address
                ? ` (${privyEmbeddedWallet.address.slice(0, 6)}…${privyEmbeddedWallet.address.slice(-4)})`
                : ''}
              . Link it to your Vancelian account to see balances and deposit addresses in the
              app.
            </p>
          ) : (
            <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              Your Vancelian account is ready. Create a Privy embedded wallet to receive crypto
              deposits and view balances in your dashboard.
            </p>
          )}

          {needsPrivyAuth ? (
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
                Resend code
              </button>
            </div>
          ) : (
            <div className="mt-8">
              <Button
                type="button"
                className="w-full gap-2"
                disabled={creating}
                onClick={() => void onCreateWallet()}
              >
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    {isSyncMode ? 'Linking wallet…' : 'Creating wallet…'}
                  </>
                ) : (
                  <>
                    <Wallet className="h-4 w-4" aria-hidden />
                    {isSyncMode ? 'Link wallet to Vancelian' : 'Create wallet'}
                  </>
                )}
              </Button>
              <p className="mt-4 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
                {isSyncMode
                  ? 'Links your existing Privy wallet to Vancelian so deposits and balances appear in the dashboard.'
                  : 'This creates an embedded Ethereum (EVM) wallet via Privy, linked to your Vancelian account — same flow as the mobile app.'}
              </p>
            </div>
          )}

          {error ? <p className="portal-auth__error mt-6">{error}</p> : null}
        </div>
      </div>
    </PortalPageContainer>
  )
}

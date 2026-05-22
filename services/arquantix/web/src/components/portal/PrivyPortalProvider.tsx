'use client'

import * as React from 'react'
import { PrivyProvider, Captcha } from '@privy-io/react-auth'
import { isPrivyConfigured, privyProviderProps } from '@/lib/portal/privyConfig'
import {
  formatPrivyConfigError,
  getCurrentBrowserOrigin,
  isPrivyOriginNotAllowedError,
} from '@/lib/portal/privyConfigErrors'
import { PortalAuthPrivySessionHygiene } from '@/components/portal/PortalAuthPrivySessionHygiene'

type Props = {
  children: React.ReactNode
  /** Injecté par le layout serveur depuis `PRIVY_APP_ID` (ECS / Secrets Manager). */
  appId?: string
}

function PrivySetupRequired({ message }: { message: string }) {
  const origin = getCurrentBrowserOrigin() ?? 'http://localhost:3000'

  return (
    <div className="flex min-h-screen items-center justify-center bg-v-bg px-6 py-12">
      <div className="max-w-xl rounded-v-card border border-v-fg-10 bg-white p-8 shadow-v-subtle">
        <h1 className="m-0 font-ui text-[20px] font-semibold text-v-fg">
          Configuration Privy requise
        </h1>
        <p className="mt-4 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">{message}</p>
        <ol className="mt-4 mb-0 list-decimal space-y-2 pl-5 font-ui text-[14px] leading-relaxed text-v-fg-body">
          <li>
            Dashboard Privy → <strong>Settings → Domains</strong> : vérifier{' '}
            <code className="rounded bg-v-fg-05 px-1">{origin}</code> dans Allowed origins
            (onglet Domains, pas Clients).
          </li>
          <li>
            Ne pas utiliser le client mobile Flutter (
            <code className="rounded bg-v-fg-05 px-1">com.vancelian.app*</code>) sur le web —
            il provoque <code className="rounded bg-v-fg-05 px-1">Invalid nativeAppID</code>.
          </li>
          <li>
            Option avancée : créer un <strong>client Web</strong> séparé et renseigner{' '}
            <code className="rounded bg-v-fg-05 px-1">NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID</code>{' '}
            dans <code className="rounded bg-v-fg-05 px-1">.env.local</code>.
          </li>
          <li>Vider le cache navigateur ou hard refresh, puis redémarrer Next si besoin.</li>
        </ol>
        <p className="mt-4 mb-0 font-ui text-[13px] text-v-fg-muted">
          Avec les domains app-level configurés, seul{' '}
          <code className="rounded bg-v-fg-05 px-1">NEXT_PUBLIC_PRIVY_APP_ID</code> suffit — pas
          besoin du client ID mobile.
        </p>
      </div>
    </div>
  )
}

export function PrivyPortalProvider({ children, appId: appIdFromServer }: Props) {
  const [configError, setConfigError] = React.useState<string | null>(null)

  React.useEffect(() => {
    const onRejection = (event: PromiseRejectionEvent) => {
      if (!isPrivyOriginNotAllowedError(event.reason)) return
      event.preventDefault()
      setConfigError(
        formatPrivyConfigError(event.reason, 'Privy a refusé l’origine locale.'),
      )
    }
    window.addEventListener('unhandledrejection', onRejection)
    return () => window.removeEventListener('unhandledrejection', onRejection)
  }, [])

  if (!isPrivyConfigured(appIdFromServer)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-v-bg px-6">
        <div className="max-w-md rounded-v-card border border-v-fg-10 bg-white p-8 text-center shadow-v-subtle">
          <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
            Privy n&apos;est pas configuré pour ce build web. Définissez{' '}
            <code className="rounded bg-v-fg-05 px-1">NEXT_PUBLIC_PRIVY_APP_ID</code>.
          </p>
        </div>
      </div>
    )
  }

  if (configError) {
    return <PrivySetupRequired message={configError} />
  }

  const providerProps = privyProviderProps(appIdFromServer)

  return (
    <PrivyProvider
      {...providerProps}
      config={{
        loginMethods: ['email'],
        appearance: {
          theme: 'light',
          accentColor: '#1A1815',
        },
        embeddedWallets: {
          createOnLogin: 'off',
        },
      }}
    >
      {/*
        Requis pour useLoginWithEmail (whitelabel) : Privy injecte le token Turnstile
        au moment de sendCode. Sans ce composant, l'envoi OTP échoue silencieusement.
      */}
      <Captcha delayedExecution />
      <PortalAuthPrivySessionHygiene />
      {children}
    </PrivyProvider>
  )
}

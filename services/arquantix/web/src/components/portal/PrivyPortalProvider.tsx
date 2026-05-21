'use client'

import { PrivyProvider, Captcha } from '@privy-io/react-auth'
import { isPrivyConfigured, privyProviderProps } from '@/lib/portal/privyConfig'

type Props = {
  children: React.ReactNode
  /** Injecté par le layout serveur depuis `PRIVY_APP_ID` (ECS / Secrets Manager). */
  appId?: string
}

export function PrivyPortalProvider({ children, appId: appIdFromServer }: Props) {
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
      {children}
    </PrivyProvider>
  )
}

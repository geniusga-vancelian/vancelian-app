import { Suspense } from 'react'
import type { Metadata } from 'next'
import { headers } from 'next/headers'
import { PortalAuthBootstrapShell } from '@/components/portal/PortalAuthBootstrapShell'
import { PortalAuthLoginSkeleton } from '@/components/portal/PortalAuthLoginSkeleton'
import { PortalAuthVerifySkeleton } from '@/components/portal/PortalAuthVerifySkeleton'
import { PortalAuthPrivyWrapper } from '@/components/portal/PortalAuthPrivyWrapper'
import { PortalLoginCmsShell } from '@/components/portal/PortalLoginCmsShell'
import { PortalPrivyErrorBoundary } from '@/components/portal/PortalPrivyErrorBoundary'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import '@/styles/portal-auth.css'

export const metadata: Metadata = {
  title: 'Vancelian — Connexion',
  robots: { index: false, follow: false },
}

/** Toujours dynamique — évite un rendu statique sans en-têtes middleware portail. */
export const dynamic = 'force-dynamic'

function isPortalFastAuthBootstrap(): boolean {
  return headers().get('x-portal-fast-auth') === '1'
}

function isVerifyRoute(): boolean {
  const pathname = headers().get('x-arq-pathname') ?? ''
  return pathname.startsWith(`${PORTAL_ROUTES.login}/verify`)
}

function portalAuthSuspenseFallback(instant = false) {
  if (isVerifyRoute()) {
    return (
      <PortalAuthBootstrapShell instant={instant}>
        <PortalAuthVerifySkeleton />
      </PortalAuthBootstrapShell>
    )
  }

  return (
    <PortalAuthBootstrapShell instant={instant}>
      <PortalAuthLoginSkeleton />
    </PortalAuthBootstrapShell>
  )
}

function portalAuthDeferPlaceholder() {
  if (isVerifyRoute()) {
    return <PortalAuthVerifySkeleton />
  }

  return <PortalAuthLoginSkeleton />
}

/** Shell CMS streamé — voie sign-out : Privy différé dans la colonne formulaire uniquement. */
export default async function PortalLoginLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()
  const fastBootstrap = isPortalFastAuthBootstrap()
  const suspenseFallback = portalAuthSuspenseFallback(fastBootstrap)

  return (
    <PortalPrivyErrorBoundary>
      <Suspense fallback={suspenseFallback}>
        <PortalLoginCmsShell>
          <PortalAuthPrivyWrapper
            appId={appId}
            deferPrivy={fastBootstrap}
            deferPlaceholder={portalAuthDeferPlaceholder()}
          >
            {children}
          </PortalAuthPrivyWrapper>
        </PortalLoginCmsShell>
      </Suspense>
    </PortalPrivyErrorBoundary>
  )
}

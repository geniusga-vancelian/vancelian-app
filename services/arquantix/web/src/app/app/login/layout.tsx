import { Suspense } from 'react'
import type { Metadata } from 'next'
import { PortalAuthPrivyGate } from '@/components/portal/PortalAuthPrivyGate'
import { PortalAuthBootstrapShell } from '@/components/portal/PortalAuthBootstrapShell'
import { PortalAuthLoginSkeleton } from '@/components/portal/PortalAuthLoginSkeleton'
import { PortalLoginCmsShell } from '@/components/portal/PortalLoginCmsShell'
import { PortalPrivyErrorBoundary } from '@/components/portal/PortalPrivyErrorBoundary'
import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'
import '@/styles/portal-auth.css'

export const metadata: Metadata = {
  title: 'Vancelian — Connexion',
  robots: { index: false, follow: false },
}

/** Toujours dynamique — évite un rendu statique sans en-têtes middleware portail. */
export const dynamic = 'force-dynamic'

/** Shell CMS streamé — Suspense bootstrap + skeleton pendant le chargement CMS. */
export default async function PortalLoginLayout({ children }: { children: React.ReactNode }) {
  const appId = getPrivyAppIdServer()

  return (
    <PortalPrivyErrorBoundary>
      <PortalAuthPrivyGate appId={appId}>
        <Suspense
          fallback={
            <PortalAuthBootstrapShell>
              <PortalAuthLoginSkeleton />
            </PortalAuthBootstrapShell>
          }
        >
          <PortalLoginCmsShell>{children}</PortalLoginCmsShell>
        </Suspense>
      </PortalAuthPrivyGate>
    </PortalPrivyErrorBoundary>
  )
}

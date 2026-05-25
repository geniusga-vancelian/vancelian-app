import { notFound } from 'next/navigation'

import { PortalWeb3Providers } from '@/components/portal/PortalWeb3Providers'
import { isExternalWalletMockDevRouteAvailable } from '@/lib/wallet/externalWalletMockConfig'

import { WalletSandboxDevPanel } from './WalletSandboxDevPanel'

export default function WalletSandboxDevPage() {
  if (!isExternalWalletMockDevRouteAvailable()) {
    notFound()
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <PortalWeb3Providers>
        <WalletSandboxDevPanel />
      </PortalWeb3Providers>
    </main>
  )
}

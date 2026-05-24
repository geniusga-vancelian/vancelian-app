'use client'

import { Suspense } from 'react'
import { Loader2 } from 'lucide-react'
import { useSearchParams } from 'next/navigation'

import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalCreateSolanaWalletScreen } from '@/components/portal/wallet/PortalCreateSolanaWalletScreen'
import { PortalCreateWalletScreen } from '@/components/portal/wallet/PortalCreateWalletScreen'

function PortalWalletCreatePageContent() {
  const searchParams = useSearchParams()
  const chain = searchParams?.get('chain')
  if (chain === 'solana') return <PortalCreateSolanaWalletScreen />
  return <PortalCreateWalletScreen />
}

export default function PortalWalletCreatePage() {
  return (
    <Suspense
      fallback={
        <PortalPageContainer className="flex min-h-[50vh] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" aria-hidden />
          <span className="sr-only">Loading</span>
        </PortalPageContainer>
      }
    >
      <PortalWalletCreatePageContent />
    </Suspense>
  )
}

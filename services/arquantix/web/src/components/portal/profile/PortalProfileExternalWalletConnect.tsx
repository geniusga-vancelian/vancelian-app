'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { ConnectExternalWalletButton } from '@/components/wallet/ConnectExternalWalletButton'
import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

/** Connexion wallet externe — Web3 chargé au clic uniquement. */
export function PortalProfileExternalWalletConnect() {
  const [active, setActive] = useState(false)

  if (!active) {
    return (
      <Button type="button" variant="outline" size="sm" onClick={() => setActive(true)}>
        Connecter MetaMask / WalletConnect
      </Button>
    )
  }

  return (
    <PortalWeb3BoundaryLazy>
      <ConnectExternalWalletButton compact />
    </PortalWeb3BoundaryLazy>
  )
}

'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalEvmChainDepositModule } from '@/components/portal/wallet/PortalEvmChainDepositModule'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  fetchPortalPersonCryptoWallets,
  readCachedPortalPersonCryptoWallets,
  resolvePrimaryPersonCryptoWallet,
  type PortalPersonCryptoWallet,
} from '@/lib/portal/privyWalletClient'

export function PortalCryptoDepositScreen() {
  const router = useRouter()
  const cachedWallets = useMemo(() => readCachedPortalPersonCryptoWallets(), [])
  const [wallets, setWallets] = useState<PortalPersonCryptoWallet[]>(cachedWallets)
  const [activeWalletId, setActiveWalletId] = useState<string | null>(null)
  const [addressLoading, setAddressLoading] = useState(cachedWallets.length === 0)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    setError('')
    try {
      const rows = await fetchPortalPersonCryptoWallets()
      setWallets(rows)
      if (rows.length === 0) {
        router.replace(PORTAL_ROUTES.walletCreate)
        return
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load your deposit address.')
    } finally {
      setAddressLoading(false)
      setRefreshing(false)
    }
  }, [router])

  useEffect(() => {
    void load()
  }, [load])

  const primaryWallet = useMemo(() => resolvePrimaryPersonCryptoWallet(wallets), [wallets])

  useEffect(() => {
    if (wallets.length === 0) return
    setActiveWalletId((current) => {
      if (current && wallets.some((wallet) => wallet.id === current)) return current
      return primaryWallet?.id ?? wallets[0]?.id ?? null
    })
  }, [primaryWallet?.id, wallets])

  const activeWallet = useMemo(() => {
    if (!activeWalletId) return primaryWallet
    return wallets.find((wallet) => wallet.id === activeWalletId) ?? primaryWallet
  }, [activeWalletId, primaryWallet, wallets])

  return (
    <PortalPageContainer>
      <PortalDetailBackLink href={PORTAL_ROUTES.cryptoWallet} label="Back to crypto wallet" />

      <div className="v-card overflow-hidden !p-0">
        <PortalEvmChainDepositModule
          wallets={wallets}
          activeWallet={activeWallet}
          onSelectWallet={(wallet) => setActiveWalletId(wallet.id)}
          loading={addressLoading}
          error={error}
          onRefresh={() => void load(true)}
          refreshing={refreshing}
        />
      </div>
    </PortalPageContainer>
  )
}

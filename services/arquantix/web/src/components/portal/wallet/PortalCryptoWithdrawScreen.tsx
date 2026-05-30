'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalEvmChainWithdrawModule } from '@/components/portal/wallet/PortalEvmChainWithdrawModule'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  fetchPortalPersonCryptoWallets,
  readCachedPortalPersonCryptoWallets,
  resolvePrimaryPersonCryptoWallet,
  type PortalPersonCryptoWallet,
} from '@/lib/portal/privyWalletClient'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

function buildWithdrawBalances(
  positions: PortalCryptoWalletHubPayload['positions']['positions'],
): Record<string, number> {
  const balances: Record<string, number> = {}
  for (const position of positions) {
    const key = position.asset.trim().toUpperCase()
    if (!key) continue
    balances[key] = position.availableBalance ?? position.balance ?? 0
  }
  return balances
}

export function PortalCryptoWithdrawScreen() {
  const router = useRouter()
  const cachedWallets = useMemo(() => readCachedPortalPersonCryptoWallets(), [])
  const [wallets, setWallets] = useState<PortalPersonCryptoWallet[]>(cachedWallets)
  const [activeWalletId, setActiveWalletId] = useState<string | null>(null)
  const [walletsLoading, setWalletsLoading] = useState(cachedWallets.length === 0)
  const [walletError, setWalletError] = useState('')

  const {
    data: walletData,
    loading: balancesLoading,
    refreshing,
    error: balancesError,
    refresh,
  } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:crypto-wallet',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: 'Unable to load your crypto balances.',
    scopeAware: true,
  })

  const loadWallets = useCallback(async (isRefresh = false) => {
    if (!isRefresh) setWalletsLoading(true)
    setWalletError('')
    try {
      const rows = await fetchPortalPersonCryptoWallets()
      setWallets(rows)
      if (rows.length === 0) {
        router.replace(PORTAL_ROUTES.walletCreate)
        return
      }
    } catch (err) {
      setWalletError(err instanceof Error ? err.message : 'Unable to load your wallets.')
    } finally {
      setWalletsLoading(false)
    }
  }, [router])

  useEffect(() => {
    void loadWallets()
  }, [loadWallets])

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

  const balances = useMemo(
    () => buildWithdrawBalances(walletData?.positions.positions ?? []),
    [walletData?.positions.positions],
  )

  const loading = walletsLoading || (balancesLoading && !walletData)
  const error = walletError || balancesError

  const onRefresh = useCallback(() => {
    void loadWallets(true)
    void refresh()
  }, [loadWallets, refresh])

  if (loading) {
    return <PortalDashboardSkeleton />
  }

  return (
    <PortalPageContainer>
      <PortalDetailBackLink href={PORTAL_ROUTES.cryptoWallet} label="Back to crypto wallet" />

      <div className="v-card overflow-hidden !p-0">
        <PortalEvmChainWithdrawModule
          wallets={wallets}
          activeWallet={activeWallet}
          onSelectWallet={(wallet) => setActiveWalletId(wallet.id)}
          balances={balances}
          loading={loading}
          error={error}
          onCancel={() => router.push(PORTAL_ROUTES.cryptoWallet)}
          onRefresh={onRefresh}
          refreshing={refreshing}
        />
      </div>
    </PortalPageContainer>
  )
}

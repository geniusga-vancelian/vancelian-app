'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { PortalDefiVaultInvestFlow } from '@/components/portal/invest/PortalDefiVaultInvestFlow'
import { PortalDefiVaultInvestLayout } from '@/components/portal/invest/PortalDefiVaultInvestLayout'
import { fetchPortalLedgityVaults } from '@/lib/portal/ledgity/ledgityVaultClient'
import type {
  PortalLedgityBetaPortalFlags,
  PortalLedgityVaultDetails,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import { parsePortalVaultFlowMode, PORTAL_ROUTES, portalSavingsVaultRoute } from '@/lib/portal/portalRouting'

type Props = {
  vaultId: string
}

export function PortalLedgityVaultInvestScreen({ vaultId }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = parsePortalVaultFlowMode(searchParams?.get('mode') ?? null)
  const [vault, setVault] = useState<PortalLedgityVaultDetails | null>(null)
  const [beta, setBeta] = useState<PortalLedgityBetaPortalFlags | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchPortalLedgityVaults()
      setBeta(payload.beta ?? null)
      const needle = vaultId.trim()
      const needleLower = needle.toLowerCase()
      const match =
        payload.vaults.find((row) => row.id === needle) ??
        payload.vaults.find((row) => row.portalConfigId === needle) ??
        payload.vaults.find((row) => row.vaultAddress.trim().toLowerCase() === needleLower) ??
        payload.vaults.find((row) => row.id === needleLower)
      if (!match) {
        setError(
          payload.partial
            ? 'Vault temporarily unavailable. Please try again.'
            : 'This vault is not available.',
        )
        setVault(null)
        return
      }
      setVault(match)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load vault.')
      setVault(null)
    } finally {
      setLoading(false)
    }
  }, [vaultId])

  useEffect(() => {
    void load()
  }, [load])

  const back = () => {
    if (searchParams?.get('from') === 'savings' && vault?.vaultAddress) {
      router.push(portalSavingsVaultRoute(vault.vaultAddress))
      return
    }
    router.push(PORTAL_ROUTES.invest)
  }

  return (
    <PortalDefiVaultInvestLayout loading={loading} error={error} onRetry={() => void load()}>
      {vault ? (
        <PortalDefiVaultInvestFlow vault={vault} beta={beta} mode={mode} onClose={back} />
      ) : null}
    </PortalDefiVaultInvestLayout>
  )
}

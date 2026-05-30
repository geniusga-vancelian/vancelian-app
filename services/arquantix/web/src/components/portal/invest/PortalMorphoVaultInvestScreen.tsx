'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { PortalDefiVaultInvestFlow } from '@/components/portal/invest/PortalDefiVaultInvestFlow'
import { PortalDefiVaultInvestLayout } from '@/components/portal/invest/PortalDefiVaultInvestLayout'
import { fetchPortalMorphoVaults } from '@/lib/portal/morphoVaultClient'
import type {
  PortalMorphoBetaPortalFlags,
  PortalMorphoVaultDetails,
} from '@/lib/portal/morphoVaultTypes'
import { parsePortalVaultFlowMode, PORTAL_ROUTES, portalSavingsVaultRoute } from '@/lib/portal/portalRouting'

type Props = {
  vaultAddress: string
}

export function PortalMorphoVaultInvestScreen({ vaultAddress }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = parsePortalVaultFlowMode(searchParams?.get('mode') ?? null)
  const normalized = vaultAddress.trim().toLowerCase()
  const [vault, setVault] = useState<PortalMorphoVaultDetails | null>(null)
  const [beta, setBeta] = useState<PortalMorphoBetaPortalFlags | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await fetchPortalMorphoVaults()
      setBeta(payload.beta ?? null)
      const match = payload.vaults.find(
        (row) => row.vaultAddress.trim().toLowerCase() === normalized,
      )
      if (!match) {
        setError('This vault is not available.')
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
  }, [normalized])

  useEffect(() => {
    void load()
  }, [load])

  const back = () => {
    if (searchParams?.get('from') === 'savings') {
      router.push(portalSavingsVaultRoute(normalized))
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

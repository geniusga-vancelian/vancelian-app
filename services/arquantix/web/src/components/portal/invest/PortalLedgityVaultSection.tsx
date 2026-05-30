'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalDefiVaultOfferCard } from '@/components/portal/invest/PortalDefiVaultOfferCard'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { fetchPortalLedgityVaults } from '@/lib/portal/ledgity/ledgityVaultClient'
import type {
  PortalLedgityBetaPortalFlags,
  PortalLedgityVaultDetails,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import { portalLedgityVaultInvestRoute } from '@/lib/portal/portalRouting'

type Props = {
  embedded?: boolean
}

export function PortalLedgityVaultSection({ embedded = false }: Props) {
  const [vaults, setVaults] = useState<PortalLedgityVaultDetails[]>([])
  const [beta, setBeta] = useState<PortalLedgityBetaPortalFlags | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadVaults = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPortalLedgityVaults()
      setVaults(data.vaults)
      setBeta(data.beta ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load Ledgity vaults.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadVaults()
  }, [loadVaults])

  return (
    <section id={embedded ? undefined : 'ledgity-vaults'} className="flex flex-col gap-4">
      {embedded ? (
        <h3 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Ledgity (RWA)</h3>
      ) : (
        <PortalSectionHeading title="Ledgity vaults (RWA)" />
      )}
      <p className="m-0 -mt-2 font-ui text-[14px] text-v-fg-muted">
        Deposit stablecoins into Ledgity ERC4626 vaults on Base. Variable yield linked to tokenized real-world assets (RWA).
      </p>

      {beta?.message ? (
        <p className="m-0 rounded-v-card border border-sky-200 bg-sky-50 px-4 py-3 font-ui text-[13px] text-sky-950">
          {beta.message}
        </p>
      ) : null}

      {beta?.depositsDisabled ? (
        <p className="m-0 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-900">
          Ledgity deposits are temporarily paused. You can still withdraw existing funds.
        </p>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 font-ui text-[14px] text-v-fg-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading Ledgity vaults…
        </div>
      ) : null}

      {error ? (
        <div className="flex flex-col gap-2">
          <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
          <button
            type="button"
            onClick={() => void loadVaults()}
            className="v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px]"
          >
            Retry
          </button>
        </div>
      ) : null}

      {!loading && !error && vaults.length === 0 && !beta?.enabled ? (
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">No Ledgity vaults published yet.</p>
      ) : null}

      {!loading && !error && vaults.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {vaults.map((vault) => (
            <PortalDefiVaultOfferCard
              key={vault.id}
              vault={vault}
              href={portalLedgityVaultInvestRoute(vault.id)}
            />
          ))}
        </div>
      ) : null}
    </section>
  )
}

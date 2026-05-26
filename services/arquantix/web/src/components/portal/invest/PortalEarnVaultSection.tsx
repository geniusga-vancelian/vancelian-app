'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalEarnVaultModal } from '@/components/portal/invest/PortalEarnVaultModal'
import { PortalDefiVaultOfferCard } from '@/components/portal/invest/PortalDefiVaultOfferCard'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { fetchPortalMorphoVaults } from '@/lib/portal/morphoVaultClient'
import type { PortalMorphoVaultDetails, PortalMorphoBetaPortalFlags } from '@/lib/portal/morphoVaultTypes'

type Props = {
  /** Sous-section d’une liste DeFi unifiée (sans titre h2 principal). */
  embedded?: boolean
}

export function PortalEarnVaultSection({ embedded = false }: Props) {
  const [vaults, setVaults] = useState<PortalMorphoVaultDetails[]>([])
  const [beta, setBeta] = useState<PortalMorphoBetaPortalFlags | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedVault, setSelectedVault] = useState<PortalMorphoVaultDetails | null>(null)

  const loadVaults = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPortalMorphoVaults()
      setVaults(data.vaults)
      setBeta(data.beta ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load vaults.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadVaults()
  }, [loadVaults])

  return (
    <section id={embedded ? undefined : 'earn-vaults'} className="flex flex-col gap-4">
      {embedded ? (
        <h3 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Morpho</h3>
      ) : (
        <PortalSectionHeading title="DeFi vaults" />
      )}
      <p className="m-0 -mt-2 font-ui text-[14px] text-v-fg-muted">
        Deposit stablecoins into Morpho on-chain vaults (Base). Sign with your Vancelian or MetaMask wallet.
      </p>

      {beta?.message ? (
        <p className="m-0 rounded-v-card border border-sky-200 bg-sky-50 px-4 py-3 font-ui text-[13px] text-sky-950">
          {beta.message}
        </p>
      ) : null}

      {beta?.enabled && beta.allowed && beta.depositsDisabled ? (
        <p className="m-0 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-900">
          Morpho USDC deposits are temporarily paused. You can still withdraw existing funds.
        </p>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 font-ui text-[14px] text-v-fg-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading vaults…
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
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">No published vaults yet.</p>
      ) : null}

      {!loading && !error && vaults.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {vaults.map((vault) => (
            <PortalDefiVaultOfferCard
              key={vault.id}
              vault={vault}
              onOpen={() => setSelectedVault(vault)}
            />
          ))}
        </div>
      ) : null}

      {selectedVault ? (
        <PortalEarnVaultModal
          vault={selectedVault}
          beta={beta ?? undefined}
          onClose={() => {
            setSelectedVault(null)
            void loadVaults()
          }}
        />
      ) : null}
    </section>
  )
}

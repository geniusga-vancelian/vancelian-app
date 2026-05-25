'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, TrendingUp } from 'lucide-react'

import { PortalLedgityVaultModal } from '@/components/portal/invest/PortalLedgityVaultModal'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { Button } from '@/components/ui/button'
import { fetchPortalLedgityVaults } from '@/lib/portal/ledgity/ledgityVaultClient'
import {
  formatEarnApyFromBps,
  formatPricePerShare,
} from '@/lib/portal/ledgity/ledgityVaultFormat'
import type {
  PortalLedgityBetaPortalFlags,
  PortalLedgityVaultDetails,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import { getPortalDefiIntegrationLabel } from '@/lib/portal/morphoConstants'
import { formatEarnUsd } from '@/lib/portal/morphoVaultFormat'
import { cn } from '@/lib/utils'

export function PortalLedgityVaultSection() {
  const [vaults, setVaults] = useState<PortalLedgityVaultDetails[]>([])
  const [beta, setBeta] = useState<PortalLedgityBetaPortalFlags | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedVault, setSelectedVault] = useState<PortalLedgityVaultDetails | null>(null)

  const loadVaults = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPortalLedgityVaults()
      setVaults(data.vaults)
      setBeta(data.beta ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les vaults Ledgity.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadVaults()
  }, [loadVaults])

  return (
    <section id="ledgity-vaults" className="flex flex-col gap-4">
      <PortalSectionHeading title="Vaults Ledgity (RWA)" />
      <p className="m-0 -mt-2 font-ui text-[14px] text-v-fg-muted">
        Déposez vos stablecoins dans des vaults Ledgity ERC4626 sur Base. Rendement variable lié à des actifs réels
        tokenisés (RWA).
      </p>

      {beta?.message ? (
        <p className="m-0 rounded-v-card border border-sky-200 bg-sky-50 px-4 py-3 font-ui text-[13px] text-sky-950">
          {beta.message}
        </p>
      ) : null}

      {beta?.depositsDisabled ? (
        <p className="m-0 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-900">
          Les dépôts Ledgity sont temporairement suspendus. Vous pouvez retirer vos fonds existants.
        </p>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 font-ui text-[14px] text-v-fg-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Chargement des vaults Ledgity…
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
            Réessayer
          </button>
        </div>
      ) : null}

      {!loading && !error && vaults.length === 0 && !beta?.enabled ? (
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">Aucun vault Ledgity publié pour le moment.</p>
      ) : null}

      {!loading && !error && vaults.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {vaults.map((vault) => (
            <article
              key={vault.id}
              className="flex flex-col gap-4 rounded-v-card border border-v-fg-10 bg-v-card p-5 shadow-v-subtle"
            >
              <div className="flex items-start gap-3">
                <PortalCryptoAvatar ticker={vault.asset.symbol} symbol={vault.asset.symbol} size="md" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="m-0 font-ui text-[17px] font-semibold text-v-fg">{vault.name}</h3>
                    <span className="rounded-v-tag bg-violet-100 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-violet-800">
                      {vault.provider}
                    </span>
                    <span className="rounded-v-tag bg-v-fg-05 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-v-fg-muted">
                      {getPortalDefiIntegrationLabel(vault.integrationMode)}
                    </span>
                  </div>
                  {vault.description ? (
                    <p className="mt-1 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
                      {vault.description}
                    </p>
                  ) : null}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 font-ui text-[13px]">
                <div>
                  <p className="m-0 text-v-fg-muted">APY estimé</p>
                  <p className="m-0 mt-0.5 flex items-center gap-1 font-semibold text-v-green">
                    <TrendingUp className="h-3.5 w-3.5" />
                    {formatEarnApyFromBps(vault.userApyBps)}
                  </p>
                </div>
                <div>
                  <p className="m-0 text-v-fg-muted">Prix par part (PPS)</p>
                  <p className="m-0 mt-0.5 font-semibold text-v-fg">{formatPricePerShare(vault.pricePerShare)}</p>
                </div>
                <div>
                  <p className="m-0 text-v-fg-muted">Actif</p>
                  <p className="m-0 mt-0.5 font-semibold text-v-fg">{vault.asset.symbol}</p>
                </div>
                <div>
                  <p className="m-0 text-v-fg-muted">TVL</p>
                  <p className="m-0 mt-0.5 font-semibold text-v-fg">{formatEarnUsd(vault.tvlUsd)}</p>
                </div>
                <div className="col-span-2">
                  <p className="m-0 text-v-fg-muted">Liquidité disponible</p>
                  <p className="m-0 mt-0.5 font-semibold text-v-fg">
                    {formatEarnUsd(vault.availableLiquidityUsd)}
                  </p>
                </div>
              </div>

              <Button
                type="button"
                className={cn('w-full rounded-full font-ui text-[15px] font-semibold')}
                onClick={() => setSelectedVault(vault)}
              >
                Déposer / Retirer
              </Button>
            </article>
          ))}
        </div>
      ) : null}

      {selectedVault ? (
        <PortalLedgityVaultModal
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

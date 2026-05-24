'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, TrendingUp } from 'lucide-react'

import { PortalEarnVaultModal } from '@/components/portal/invest/PortalEarnVaultModal'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { Button } from '@/components/ui/button'
import { getPortalMorphoIntegrationLabel } from '@/lib/portal/morphoConstants'
import { fetchPortalMorphoVaults } from '@/lib/portal/morphoVaultClient'
import { formatEarnApyFromBps, formatEarnUsd } from '@/lib/portal/morphoVaultFormat'
import type { PortalMorphoVaultDetails, PortalMorphoBetaPortalFlags } from '@/lib/portal/morphoVaultTypes'
import { cn } from '@/lib/utils'

export function PortalEarnVaultSection() {
  const [vaults, setVaults] = useState<PortalMorphoVaultDetails[]>([])
  const [configured, setConfigured] = useState(true)
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
      setConfigured(data.configured)
      setBeta(data.beta ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Impossible de charger les vaults.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadVaults()
  }, [loadVaults])

  return (
    <section id="earn-vaults" className="flex flex-col gap-4">
      <PortalSectionHeading title="Vaults DeFi" />
      <p className="m-0 -mt-2 font-ui text-[14px] text-v-fg-muted">
        Déposez vos stablecoins dans des vaults Morpho on-chain (Base).
      </p>

      {!configured ? (
        <p className="m-0 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-900">
          Un vault en mode Privy Earn nécessite{' '}
          <code className="rounded bg-white/80 px-1">PRIVY_APP_SECRET</code> côté serveur.
        </p>
      ) : null}

      {beta?.message ? (
        <p className="m-0 rounded-v-card border border-sky-200 bg-sky-50 px-4 py-3 font-ui text-[13px] text-sky-950">
          {beta.message}
        </p>
      ) : null}

      {beta?.enabled && beta.allowed && beta.depositsDisabled ? (
        <p className="m-0 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-900">
          Les dépôts Morpho USDC sont temporairement suspendus. Vous pouvez retirer vos fonds existants.
        </p>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 font-ui text-[14px] text-v-fg-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Chargement des vaults…
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
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">Aucun vault publié pour le moment.</p>
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
                    <span className="rounded-v-tag bg-v-fg-05 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-v-fg-muted">
                      {vault.provider}
                    </span>
                    <span className="rounded-v-tag bg-v-fg-05 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-v-fg-muted">
                      {getPortalMorphoIntegrationLabel(vault.integrationMode)}
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
                  <p className="m-0 text-v-fg-muted">APY utilisateur</p>
                  <p className="m-0 mt-0.5 flex items-center gap-1 font-semibold text-v-green">
                    <TrendingUp className="h-3.5 w-3.5" />
                    {formatEarnApyFromBps(vault.userApyBps)}
                  </p>
                </div>
                <div>
                  <p className="m-0 text-v-fg-muted">Actif</p>
                  <p className="m-0 mt-0.5 font-semibold text-v-fg">{vault.asset.symbol}</p>
                </div>
                <div>
                  <p className="m-0 text-v-fg-muted">TVL</p>
                  <p className="m-0 mt-0.5 font-semibold text-v-fg">{formatEarnUsd(vault.tvlUsd)}</p>
                </div>
                <div>
                  <p className="m-0 text-v-fg-muted">Liquidité</p>
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

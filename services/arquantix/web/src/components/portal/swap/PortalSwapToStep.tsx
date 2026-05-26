'use client'

import { useMemo, useState } from 'react'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import type { SwapCatalogAsset } from '@/lib/portal/swapFlowTypes'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

type Props = {
  assets: SwapCatalogAsset[]
  onSelect: (asset: string) => void
  onBack?: () => void
}

export function PortalSwapToStep({ assets, onSelect, onBack }: Props) {
  const { chainLabel } = usePortalExecutionScope()
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return assets
    return assets.filter(
      (a) =>
        a.symbol.toLowerCase().includes(q) ||
        a.display_name.toLowerCase().includes(q),
    )
  }, [assets, query])

  return (
    <PortalSwapFlowShell title="Swap" onBack={onBack}>
      <div className="flex flex-col gap-5">
        <div>
          <p className="m-0 font-ui text-[13px] uppercase tracking-wide text-v-fg-muted">Étape 1</p>
          <h2 className="mt-2 mb-0 font-ui text-[24px] font-bold leading-tight text-v-fg">
            Vers quelle crypto ?
          </h2>
          <p className="mt-2 mb-0 font-ui text-[15px] text-v-fg-muted">
            USDC, USDT ou ETH — swap same-chain sur {chainLabel} (réseau navbar).
          </p>
        </div>

        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher"
          className="w-full rounded-full border border-v-border bg-white px-4 py-3 font-ui text-[15px] shadow-v-subtle outline-none focus:border-v-accent"
        />

        <article className="overflow-hidden card-simple overflow-hidden !w-full">
          <ul className="m-0 list-none p-0">
            {filtered.map((asset) => (
              <AssetRow key={asset.symbol} asset={asset} onSelect={onSelect} />
            ))}
          </ul>
        </article>
      </div>
    </PortalSwapFlowShell>
  )
}

function AssetRow({
  asset,
  onSelect,
}: {
  asset: SwapCatalogAsset
  onSelect: (asset: string) => void
}) {
  return (
    <li className="border-b border-v-border last:border-b-0">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-v-card-hover"
        onClick={() => onSelect(asset.symbol)}
      >
        <PortalCryptoAvatar
          ticker={asset.symbol}
          symbol={tickerToProviderSymbol(asset.symbol)}
          size="md"
        />
        <span className="min-w-0 flex-1">
          <span className="block font-ui text-[15px] font-semibold text-v-fg">{asset.display_name}</span>
          <span className="mt-0.5 block font-ui text-[13px] text-v-fg-muted">{asset.symbol}</span>
        </span>
      </button>
    </li>
  )
}

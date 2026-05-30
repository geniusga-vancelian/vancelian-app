'use client'

import { useMemo } from 'react'

import { AppAccountSummaryList } from '@/components/design-system/app/AppAccountSummaryList'
import { AppAccountSummaryRow } from '@/components/design-system/app/AppAccountSummaryRow'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { formatSwapCryptoAmount, buildSwapFromOptions, type SwapFromOption } from '@/lib/portal/swapFlowFormat'
import type { SwapCatalogAsset } from '@/lib/portal/swapFlowTypes'
import { SWAP_V1_SAME_CHAIN_ONLY, SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'

export type { SwapFromOption } from '@/lib/portal/swapFlowFormat'

type Props = {
  toAsset: string
  toChain: string
  catalog: SwapCatalogAsset[]
  positions: PortalCryptoPosition[]
  onSelect: (option: SwapFromOption) => void
  onBack: () => void
  /** Ex. buy via `?to=` — seule étape de sélection. */
  stepEyebrow?: string
  description?: string
}

export function PortalSwapFromStep({
  toAsset,
  toChain,
  catalog,
  positions,
  onSelect,
  onBack,
  stepEyebrow = 'Step 2',
  description,
}: Props) {
  const options = useMemo(
    () => buildSwapFromOptions(catalog, positions, toAsset, toChain),
    [catalog, positions, toAsset, toChain],
  )

  const chainHint = SWAP_CHAIN_LABELS[toChain] ?? toChain

  return (
    <PortalSwapFlowShell title="Swap" onBack={onBack}>
      <div className="flex flex-col gap-5">
        <PortalPageIntro
          eyebrow={stepEyebrow}
          title="From which asset?"
          description={
            description ??
            (SWAP_V1_SAME_CHAIN_ONLY
              ? `Wallet and network are set in the navbar — swaps on ${chainHint} only.`
              : 'Wallet and network are set in the navbar — Base assets eligible (USDC, EURC, ETH, etc.).')
          }
        />

        {options.length === 0 ? (
          <div className="acct-summary p-8 text-center">
            <p className="m-0 font-ui text-[15px] text-v-fg-muted">
              No eligible wallet with balance. Make a crypto deposit first.
            </p>
          </div>
        ) : (
          <AppAccountSummaryList>
            {options.map((opt) => (
              <AppAccountSummaryRow
                key={`${opt.asset}-${opt.chain}`}
                showChevron={false}
                onClick={() => onSelect(opt)}
                leading={
                  <PortalCryptoAvatar
                    ticker={opt.asset}
                    symbol={tickerToProviderSymbol(opt.asset)}
                    apiLogoUrl={opt.logoUrl}
                    size="lg"
                    className="!h-[46px] !w-[46px]"
                  />
                }
                title={opt.name}
                subtitle={`${SWAP_CHAIN_LABELS[opt.chain] ?? opt.chain} · Swap`}
                amount={`${formatSwapCryptoAmount(opt.balance)} ${opt.asset}`}
              />
            ))}
          </AppAccountSummaryList>
        )}
      </div>
    </PortalSwapFlowShell>
  )
}

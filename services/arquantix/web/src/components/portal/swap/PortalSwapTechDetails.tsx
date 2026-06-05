'use client'

import { useState } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import { formatSwapSigningWalletShort } from '@/lib/portal/swapSigningWallet'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'

type Props = {
  quote: SwapQuotePayload
}

export function PortalSwapTechDetails({ quote }: Props) {
  const [open, setOpen] = useState(false)

  const routeLabel =
    quote.route_steps.length > 0
      ? quote.route_steps.map((step) => step.label).join(' → ')
      : `${SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain} → ${SWAP_CHAIN_LABELS[quote.to_chain] ?? quote.to_chain}`

  const chainLabel = SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain
  const walletLabel =
    quote.signing_wallet_mode === 'external_evm' ? 'External wallet' : 'Vancelian wallet'

  return (
    <>
      <button
        type="button"
        className={`inv-tech-toggle${open ? ' is-open' : ''}`}
        onClick={() => setOpen((value) => !value)}
      >
        Technical details
        <span className="inv-tech-toggle__arrow" aria-hidden="true">
          <KalaiIcon name="chevron-down" size={16} />
        </span>
      </button>
      {open ? (
        <div className="inv-tech">
          <div className="inv-tech__row">
            <span className="inv-tech__k">Route</span>
            <span className="inv-tech__v">{routeLabel}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Network</span>
            <span className="inv-tech__v">{chainLabel}</span>
          </div>
          {quote.exchange_rate ? (
            <div className="inv-tech__row">
              <span className="inv-tech__k">Rate</span>
              <span className="inv-tech__v">
                1 {quote.from_asset} ≈ {formatSwapCryptoAmount(quote.exchange_rate, quote.to_asset)} {quote.to_asset}
              </span>
            </div>
          ) : null}
          {quote.signing_wallet_address ? (
            <div className="inv-tech__row">
              <span className="inv-tech__k">Signer</span>
              <span className="inv-tech__v">
                {walletLabel} · {formatSwapSigningWalletShort(quote.signing_wallet_address)}
              </span>
            </div>
          ) : null}
        </div>
      ) : null}
    </>
  )
}

'use client'

import { useMemo, useState } from 'react'

import { PortalCryptoExchangeDirection } from '@/components/portal/swap/PortalCryptoExchangeDirection'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import {
  PortalSwapTransactionSteps,
  type SwapStepState,
} from '@/components/portal/swap/PortalSwapTransactionSteps'
import { Button } from '@/components/ui/button'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import { formatSwapSigningWalletShort } from '@/lib/portal/swapSigningWallet'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import { buildConfirmSteps, formatSwapFeeLine, processingPhaseLabel } from '@/lib/portal/swapFlowSteps'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

type Props = {
  fromAsset: string
  toAsset: string
  amount: string
  quote: SwapQuotePayload
  executionPhase: SwapExecutionPhase
  executing: boolean
  error: string | null
  onConfirm: () => void
  onBack: () => void
}

export function PortalSwapConfirmStep({
  fromAsset,
  toAsset,
  amount,
  quote,
  executionPhase,
  executing,
  error,
  onConfirm,
  onBack,
}: Props) {
  const [acknowledged, setAcknowledged] = useState(false)
  const { isExternalWallet } = usePortalExecutionScope()

  const steps = useMemo(
    () => buildConfirmSteps(quote, executing ? executionPhase : 'idle'),
    [quote, executing, executionPhase],
  )

  const displaySteps = executing
    ? steps
    : steps.map((s) => ({ ...s, state: 'pending' as SwapStepState }))

  const stepsTitle = executing ? 'Étapes en cours' : 'Détail de votre conversion'
  const showProcessingHint =
    executing && executionPhase !== 'idle' && executionPhase !== 'failed' && executionPhase !== 'completed'

  const parsed = Number(amount.replace(',', '.'))
  const heroAmount = `${formatSwapCryptoAmount(parsed > 0 ? parsed : quote.amount_in)} ${fromAsset}`

  return (
    <PortalSwapFlowShell
      title="Swap"
      onBack={executing ? undefined : onBack}
      centered
      footer={
        <Button
          type="button"
          className="h-[52px] w-full rounded-full font-ui text-[16px] font-semibold"
          disabled={executing || !acknowledged}
          onClick={onConfirm}
        >
          {executing ? 'Traitement...' : 'Confirmer la conversion'}
        </Button>
      }
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-col items-center gap-4 text-center">
          <PortalCryptoExchangeDirection fromAsset={fromAsset} toAsset={toAsset} />
          <h2 className="m-0 max-w-sm font-ui text-[22px] font-bold leading-snug text-v-fg">
            Vous êtes sur le point de convertir
          </h2>
          <p className="m-0 font-ui text-[34px] font-bold tracking-tight text-v-fg">{heroAmount}</p>
          <p className="m-0 font-ui text-[15px] font-semibold text-v-fg-muted">
            ≈ {formatSwapCryptoAmount(quote.estimated_receive)} {toAsset}
          </p>
        </div>

        <PortalSwapTransactionSteps title={stepsTitle} steps={displaySteps} />

        {showProcessingHint ? (
          <p className="m-0 text-center font-ui text-[14px] text-v-fg-muted">
            {processingPhaseLabel(executionPhase, quote)}
          </p>
        ) : null}

        <article className="overflow-hidden card-simple overflow-hidden !w-full">
          <div className="flex items-center justify-between px-4 py-3.5 font-ui text-[15px]">
            <span className="text-v-fg-muted">Frais</span>
            <span className="font-medium text-v-fg">{formatSwapFeeLine(quote)}</span>
          </div>
        </article>

        {quote.signing_wallet_address ? (
          <article className="rounded-v-card border border-v-border bg-v-card px-4 py-3.5 font-ui text-[13px] shadow-v-subtle">
            <p className="m-0 font-medium text-v-fg">Wallet signataire LI.FI</p>
            <p className="m-0 mt-2 text-v-fg-muted">
              {quote.signing_wallet_mode === 'external_evm' ? 'MetaMask / externe' : 'Wallet Vancelian'} ·{' '}
              {formatSwapSigningWalletShort(quote.signing_wallet_address)} ·{' '}
              {SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain}
            </p>
            {isExternalWallet || quote.signing_wallet_mode === 'external_evm' ? (
              <p className="m-0 mt-2 text-amber-900">
                MetaMask peut demander plusieurs confirmations sur{' '}
                {SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain} : approbation{' '}
                {quote.from_asset}, puis swap.
              </p>
            ) : (
              <p className="m-0 mt-2 text-v-fg-muted">
                Gas réseau sponsorisé via Privy sur {SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain}{' '}
                (si activé dans le dashboard Privy).
              </p>
            )}
          </article>
        ) : null}

        <label className="flex cursor-pointer items-start gap-3 rounded-v-card border border-v-border bg-v-card px-4 py-3.5 shadow-v-subtle">
          <input
            type="checkbox"
            checked={acknowledged}
            disabled={executing}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-v-accent"
          />
          <span className="font-ui text-[13px] leading-snug text-v-fg-muted">
            En confirmant, j&apos;accepte que cette conversion soit exécutée au prix estimé. Le montant
            final peut varier légèrement selon les conditions du marché et du réseau.
          </span>
        </label>

        {error ? (
          <p className="m-0 rounded-v-control bg-red-50 px-3 py-2 font-ui text-[13px] text-v-error">
            {error}
          </p>
        ) : null}
      </div>
    </PortalSwapFlowShell>
  )
}

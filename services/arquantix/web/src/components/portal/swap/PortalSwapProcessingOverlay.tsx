'use client'

import { Check, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'

type Props = {
  open: boolean
  fromAsset: string
  toAsset: string
  quote: SwapQuotePayload
  phase: SwapExecutionPhase
  error: string | null
  onClose: () => void
  onDone?: () => void
}

/** Modale de résultat terminal uniquement (succès ou échec). */
export function PortalSwapProcessingOverlay({
  open,
  fromAsset,
  toAsset,
  quote,
  phase,
  error,
  onClose,
  onDone,
}: Props) {
  if (!open) return null

  const isSuccess = phase === 'completed'
  const isFailed = phase === 'failed' || Boolean(error)

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="swap-processing-title"
        className="flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-[20px] border border-v-border bg-v-bg shadow-v-medium sm:rounded-v-card"
      >
        <div className="flex justify-center pt-3 sm:hidden">
          <span className="h-1 w-10 rounded-full bg-v-border" />
        </div>

        <div className="flex flex-col gap-5 overflow-y-auto px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-5">
          <div className="flex flex-col items-center gap-3 text-center">
            <StatusIcon isSuccess={isSuccess} isFailed={isFailed} />
            <h2 id="swap-processing-title" className="m-0 font-ui text-[20px] font-bold text-v-fg">
              {isSuccess ? 'Conversion effectuée' : 'Conversion échouée'}
            </h2>
            <p className="m-0 font-ui text-[14px] text-v-fg-muted">
              {isSuccess
                ? `+${formatSwapCryptoAmount(quote.estimated_receive)} ${toAsset}`
                : error ?? 'Une erreur est survenue'}
            </p>
            {isSuccess ? (
              <p className="m-0 font-ui text-[14px] text-v-fg-muted">
                pour {formatSwapCryptoAmount(quote.amount_in)} {fromAsset}
              </p>
            ) : null}
          </div>

          {isFailed ? (
            <Button
              type="button"
              variant="outline"
              className="h-[48px] w-full rounded-full font-ui text-[15px] font-semibold"
              onClick={onClose}
            >
              Fermer
            </Button>
          ) : null}

          {isSuccess ? (
            <Button
              type="button"
              className="h-[48px] w-full rounded-full font-ui text-[15px] font-semibold"
              onClick={onDone ?? onClose}
            >
              Voir mon wallet {toAsset}
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function StatusIcon({ isSuccess, isFailed }: { isSuccess: boolean; isFailed: boolean }) {
  if (isSuccess) {
    return (
      <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-v-fg text-v-bg">
        <Check className="h-8 w-8" strokeWidth={2.5} aria-hidden />
      </span>
    )
  }
  if (isFailed) {
    return (
      <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-v-fg text-v-bg">
        <X className="h-8 w-8" strokeWidth={2.5} aria-hidden />
      </span>
    )
  }
  return null
}

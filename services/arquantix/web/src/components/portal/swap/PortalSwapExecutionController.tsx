'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalSwapLayout } from '@/components/portal/swap/PortalSwapLayout'
import { PortalSwapReviewStep } from '@/components/portal/swap/PortalSwapReviewStep'
import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import {
  buildSwapProcessingSteps,
  buildSwapSuccessSteps,
  buildSwapSuccessSummary,
  resolveSwapFailureCopy,
  SWAP_PROCESSING_COMPLETED_INDEX,
  swapProcessingStepperIndex,
  type SwapProcessingContext,
} from '@/components/portal/transaction/mappers/swapSteps'
import { SWAP_FLOW_UI, SWAP_RESULT_IMPOSSIBLE_ACTIONS } from '@/components/portal/transaction/mappers/swapUiCopy'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_ROUTES, portalCryptoWalletAssetRoute } from '@/lib/portal/portalRouting'
import { buildPortalScopeCacheSuffix } from '@/lib/portal/portalScopeQuery'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { executeSwap, type SwapQuotePayload } from '@/lib/portal/swapClient'
import type { PortalSwapFlowStep, SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

export type PortalSwapExecutionStep = Extract<PortalSwapFlowStep, 'review' | 'processing' | 'result'>

type Props = {
  step: PortalSwapExecutionStep
  quote: SwapQuotePayload
  amount: string
  fromAsset: string
  toAsset: string
  swapMockMode: boolean
  swapProcessingContext: SwapProcessingContext
  onStepChange: (step: PortalSwapFlowStep) => void
  onResetExecutionState: () => void
}

/** Swap review / processing / result — monte useLifiSwapExecution (R4.5-F3). */
export function PortalSwapExecutionController({
  step,
  quote,
  amount,
  fromAsset,
  toAsset,
  swapMockMode,
  swapProcessingContext,
  onStepChange,
  onResetExecutionState,
}: Props) {
  const router = useRouter()
  const { chain, walletScopeId } = usePortalExecutionScope()
  const { privyReady } = usePortalAuthPrivy()

  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [failureCopy, setFailureCopy] = useState(() => resolveSwapFailureCopy(null))
  const [signingPrep, setSigningPrep] = useState(false)
  const executionStartedRef = useRef(false)

  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    setExecutionPhase,
    fromAsset,
  )

  const resetExecution = useCallback(() => {
    setExecutionPhase('idle')
    setFailureCopy(resolveSwapFailureCopy(null))
    executionStartedRef.current = false
    onResetExecutionState()
  }, [onResetExecutionState])

  const runExecution = useCallback(async () => {
    if (!quote) return
    setExecutionPhase('preparing')

    try {
      const exec = await executeSwap(quote.swap_id)
      if (!exec.transaction) {
        throw new Error('Payload transaction manquant')
      }

      await signAndSubmit(exec)

      setExecutionPhase('bridging')
      const status = await pollUntilTerminal(quote.swap_id)

      if (status.status !== 'CONFIRMED') {
        throw new Error('Swap non confirmé')
      }

      setExecutionPhase('completed')
      onStepChange('result')
    } catch (e) {
      setExecutionPhase('failed')
      setFailureCopy(resolveSwapFailureCopy(e))
      onStepChange('result')
    }
  }, [onStepChange, pollUntilTerminal, quote, signAndSubmit])

  useEffect(() => {
    if (step !== 'processing' || executionStartedRef.current) return
    executionStartedRef.current = true
    void runExecution()
  }, [runExecution, step])

  useEffect(() => {
    if (step !== 'review' || swapMockMode) {
      setSigningPrep(false)
      return
    }

    let cancelled = false
    setSigningPrep(true)
    void (async () => {
      try {
        await waitForPrivyClientReady(
          () => privyReady,
          { timeoutMs: 30_000 },
        )
      } catch {
        /* Review still renders; execution will surface errors */
      } finally {
        if (!cancelled) setSigningPrep(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [privyReady, step, swapMockMode])

  const onReviewConfirm = useCallback(() => {
    resetExecution()
    executionStartedRef.current = false
    onStepChange('processing')
  }, [onStepChange, resetExecution])

  const onProcessingClose = useCallback(() => {
    resetExecution()
    router.push(PORTAL_ROUTES.cryptoWallet)
  }, [resetExecution, router])

  const onResultSuccess = useCallback(() => {
    resetExecution()
    const ticker = toAsset.trim().toUpperCase()
    const scopeSuffix = buildPortalScopeCacheSuffix(chain, walletScopeId)
    invalidatePortalCache(`portal:crypto-wallet:${scopeSuffix}`)
    if (ticker) invalidatePortalCache(`portal:crypto-wallet:${ticker}:${scopeSuffix}`)
    router.push(ticker ? portalCryptoWalletAssetRoute(ticker) : PORTAL_ROUTES.cryptoWallet)
  }, [chain, resetExecution, router, toAsset, walletScopeId])

  const onResultRetry = useCallback(() => {
    resetExecution()
    onStepChange('review')
  }, [onStepChange, resetExecution])

  const onResultClose = useCallback(() => {
    resetExecution()
    router.push(PORTAL_ROUTES.cryptoWallet)
  }, [resetExecution, router])

  if (step === 'review') {
    return (
      <PortalSwapLayout backLabel="Back to amount" onBackClick={() => onStepChange('amount')}>
        {signingPrep ? (
          <div
            className="mb-4 flex items-center gap-2 rounded-lg border border-v-fg-10 bg-v-fg-02 px-3 py-2 font-ui text-[13px] text-v-fg-muted"
            aria-live="polite"
          >
            <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
            {SWAP_FLOW_UI.preparingSecureConfirmation}
          </div>
        ) : null}
        <PortalSwapReviewStep
          fromAsset={fromAsset}
          toAsset={toAsset}
          amount={amount}
          quote={quote}
          swapProcessingContext={swapProcessingContext}
          onConfirm={onReviewConfirm}
          onBack={() => onStepChange('amount')}
        />
      </PortalSwapLayout>
    )
  }

  if (step === 'processing') {
    return (
      <PortalSwapLayout backLabel={SWAP_FLOW_UI.backToWallet} onBackClick={onProcessingClose}>
        <TransactionProcessingPage
          title={SWAP_FLOW_UI.processingTitle}
          lead={
            <>
              {SWAP_FLOW_UI.processingLead(
                swapProcessingContext.payLabel,
                fromAsset,
                toAsset,
              )}
            </>
          }
          steps={buildSwapProcessingSteps(swapProcessingContext)}
          progressIndex={swapProcessingStepperIndex(executionPhase)}
          completedProgressIndex={SWAP_PROCESSING_COMPLETED_INDEX}
          onClose={onProcessingClose}
        />
      </PortalSwapLayout>
    )
  }

  return (
    <PortalSwapLayout backLabel={SWAP_FLOW_UI.backToWallet} onBackClick={onResultClose}>
      {executionPhase === 'completed' ? (
        <TransactionResultPage
          variant="success"
          layout="full"
          title={SWAP_FLOW_UI.successTitle}
          lead={
            <>
              <b className="v-tnum">
                {SWAP_FLOW_UI.successLeadReceive(
                  swapProcessingContext.receiveLabel,
                  toAsset,
                )}
              </b>{' '}
              ont été crédités sur votre wallet.
            </>
          }
          stepsTitle={SWAP_FLOW_UI.successStepsTitle}
          summaryTitle={SWAP_FLOW_UI.successSummaryTitle}
          steps={buildSwapSuccessSteps(swapProcessingContext).map((step) => ({
            name: step.name,
            body:
              typeof step.body === 'string' ? (
                <p className="txn-step__amount">{step.body}</p>
              ) : (
                step.body
              ),
          }))}
          summary={buildSwapSuccessSummary(quote, swapProcessingContext)}
          note={SWAP_FLOW_UI.successNote}
          primaryAction={{
            label: SWAP_FLOW_UI.viewWalletCta(toAsset),
            onClick: onResultSuccess,
            icon: <KalaiIcon name="wallet" size={16} />,
          }}
          onClose={onResultClose}
        />
      ) : (
        <TransactionResultPage
          variant="impossible"
          copy={failureCopy}
          onRetry={onResultRetry}
          onClose={onResultClose}
          closeLabel={SWAP_RESULT_IMPOSSIBLE_ACTIONS.close}
          retryLabel={SWAP_RESULT_IMPOSSIBLE_ACTIONS.retry}
        />
      )}
    </PortalSwapLayout>
  )
}

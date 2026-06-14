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
  buildSwapAuthoritativeProcessingSteps,
  buildSwapProcessingSteps,
  buildSwapSuccessSteps,
  buildSwapSuccessSummary,
  resolveSwapFailureCopy,
  SWAP_AUTHORITATIVE_COMPLETED_INDEX,
  SWAP_PROCESSING_COMPLETED_INDEX,
  swapAuthoritativeStepperIndex,
  swapProcessingStepperIndex,
  type SwapProcessingContext,
} from '@/components/portal/transaction/mappers/swapSteps'
import { SWAP_FLOW_UI, SWAP_RESULT_IMPOSSIBLE_ACTIONS } from '@/components/portal/transaction/mappers/swapUiCopy'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { navigateAfterTransactionSuccess } from '@/lib/portal/postTransactionWalletNav'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import {
  classifySwapError,
  executionPhaseToFailurePhase,
  SwapExecutionError,
} from '@/lib/portal/swapFailure'
import {
  abandonSwap,
  recordSwapFailure,
  serverExecuteSwap,
  SwapServerAuthoritativeError,
  type SwapQuotePayload,
} from '@/lib/portal/swapClient'
import {
  SwapPriceChangedError,
  buildSwapReviewSnapshot,
  confirmSwapWithRetry,
} from '@/lib/portal/swapQuoteConfirm'
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
  onQuoteUpdate: (quote: SwapQuotePayload) => void
  priceChangeNotice: string | null
  onClearPriceChangeNotice: () => void
  onPriceChanged: () => void
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
  onQuoteUpdate,
  priceChangeNotice,
  onClearPriceChangeNotice,
  onPriceChanged,
}: Props) {
  const router = useRouter()
  const { chain, walletScope, walletScopeId, isExternalWallet } = usePortalExecutionScope()
  const { privyReady } = usePortalAuthPrivy()

  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [failureCopy, setFailureCopy] = useState(() => resolveSwapFailureCopy(null))
  const [signingPrep, setSigningPrep] = useState(false)
  const [authoritative, setAuthoritative] = useState(false)
  const executionStartedRef = useRef(false)
  const reviewSnapshotRef = useRef(buildSwapReviewSnapshot(quote))

  const { signAndSubmit, pollUntilTerminal, pollAuthoritativeUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    setExecutionPhase,
    fromAsset,
  )

  const resetExecution = useCallback(() => {
    setExecutionPhase('idle')
    setFailureCopy(resolveSwapFailureCopy(null))
    setAuthoritative(false)
    executionStartedRef.current = false
    onResetExecutionState()
  }, [onResetExecutionState])

  // PR4 — suivi du swap exécuté côté serveur (file enqueue-and-wait) : aucune signature
  // navigateur, on poll le statut et on mappe l'état de file vers le stepper autoritaire.
  const runAuthoritative = useCallback(
    async (swapId: string) => {
      setAuthoritative(true)
      setExecutionPhase('queued')
      const status = await pollAuthoritativeUntilTerminal(swapId)
      if (status.status !== 'CONFIRMED') {
        throw new Error('Swap non confirmé')
      }
      setExecutionPhase('completed')
      onStepChange('result')
    },
    [onStepChange, pollAuthoritativeUntilTerminal],
  )

  const failWith = useCallback(
    async (error: unknown) => {
      const classified =
        error instanceof SwapExecutionError
          ? error
          : classifySwapError(error, executionPhaseToFailurePhase(executionPhase))

      setExecutionPhase('failed')
      setFailureCopy(resolveSwapFailureCopy(classified))
      if (quote?.swap_id) {
        try {
          await recordSwapFailure(quote.swap_id, {
            failure_phase: classified.failurePhase,
            error_code: classified.code,
            technical_message: classified.technicalMessage,
          })
        } catch {
          /* failure record best-effort — audit DB peut déjà exister */
        }
      }
      onStepChange('result')
    },
    [executionPhase, onStepChange, quote?.swap_id],
  )

  const runExecution = useCallback(async () => {
    if (!quote) return
    const snapshot = reviewSnapshotRef.current
    setExecutionPhase('verifying_price')

    try {
      const confirmed = await confirmSwapWithRetry({
        swap_id: quote.swap_id,
        review_estimated_receive: snapshot.estimated_receive,
        review_amount_in: snapshot.amount_in,
      })
      onQuoteUpdate(confirmed.quote)

      // PR4 — mode autoritaire : le serveur exécute, le navigateur ne signe rien.
      if (confirmed.server_authoritative) {
        await runAuthoritative(quote.swap_id)
        return
      }

      setExecutionPhase('preparing')

      const exec = confirmed.execute
      if (!exec.transaction) {
        throw new Error('Payload transaction manquant')
      }

      // Wallet réel (Privy embedded) : on tente TOUJOURS l'exécution serveur. La source de
      // vérité de la délégation est l'API Privy interrogée côté backend (jamais un flag
      // client potentiellement périmé). Si non délégué / non configuré, le backend renvoie
      // signed_server_side=false et on retombe sur la signature navigateur (zéro régression).
      const canServerSign = !swapMockMode && !isExternalWallet
      let serverSigned = false
      if (canServerSign) {
        setExecutionPhase('signing')
        try {
          const serverResult = await serverExecuteSwap(quote.swap_id)
          serverSigned = serverResult.signed_server_side
        } catch {
          // Erreur réseau / endpoint indisponible : on retombe sur le flux client.
          serverSigned = false
        }
      }
      if (!serverSigned) {
        await signAndSubmit(exec)
      }

      setExecutionPhase('bridging')
      const status = await pollUntilTerminal(quote.swap_id)

      if (status.status !== 'CONFIRMED') {
        throw new Error('Swap non confirmé')
      }

      setExecutionPhase('completed')
      onStepChange('result')
    } catch (e) {
      if (e instanceof SwapPriceChangedError) {
        onQuoteUpdate(e.freshQuote)
        reviewSnapshotRef.current = buildSwapReviewSnapshot(e.freshQuote)
        onPriceChanged()
        setExecutionPhase('idle')
        executionStartedRef.current = false
        onStepChange('review')
        return
      }

      // PR4 — une route client a été refusée (serveur autoritaire) : bascule en suivi serveur.
      if (e instanceof SwapServerAuthoritativeError) {
        try {
          await runAuthoritative(quote.swap_id)
          return
        } catch (pollError) {
          await failWith(pollError)
          return
        }
      }

      await failWith(e)
    }
  }, [failWith, isExternalWallet, onPriceChanged, onQuoteUpdate, onStepChange, pollUntilTerminal, quote, runAuthoritative, signAndSubmit, swapMockMode])

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
    onClearPriceChangeNotice()
    reviewSnapshotRef.current = buildSwapReviewSnapshot(quote)
    resetExecution()
    executionStartedRef.current = false
    onStepChange('processing')
  }, [onClearPriceChangeNotice, onStepChange, quote, resetExecution])

  const onProcessingClose = useCallback(() => {
    if (quote?.swap_id && executionPhase !== 'completed' && executionPhase !== 'failed') {
      void abandonSwap(quote.swap_id, {
        failure_phase: executionPhaseToFailurePhase(executionPhase),
        reason: 'user_closed_processing',
      }).catch(() => {
        /* explicit abandon best-effort */
      })
    }
    resetExecution()
    router.push(PORTAL_ROUTES.cryptoWallet)
  }, [executionPhase, quote?.swap_id, resetExecution, router])

  const onResultSuccess = useCallback(() => {
    resetExecution()
    void navigateAfterTransactionSuccess(
      router,
      { kind: 'crypto_asset', asset: toAsset },
      { chain, walletScope, walletScopeId },
    )
  }, [chain, resetExecution, router, toAsset, walletScope, walletScopeId])

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
        {priceChangeNotice ? (
          <div
            className="mb-4 rounded-lg border border-amber-200/80 bg-amber-50 px-3 py-2 font-ui text-[13px] text-amber-950"
            role="status"
          >
            {priceChangeNotice}
          </div>
        ) : null}
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
    const authoritativeLead =
      executionPhase === 'queued'
        ? SWAP_FLOW_UI.queueWaitingLead
        : SWAP_FLOW_UI.queueAcceptedLead(swapProcessingContext.payLabel, fromAsset, toAsset)
    return (
      <PortalSwapLayout backLabel={SWAP_FLOW_UI.backToWallet} onBackClick={onProcessingClose}>
        <TransactionProcessingPage
          title={authoritative ? SWAP_FLOW_UI.queueProcessingTitle : SWAP_FLOW_UI.processingTitle}
          lead={
            <>
              {authoritative
                ? authoritativeLead
                : SWAP_FLOW_UI.processingLead(
                    swapProcessingContext.payLabel,
                    fromAsset,
                    toAsset,
                  )}
            </>
          }
          steps={
            authoritative
              ? buildSwapAuthoritativeProcessingSteps(swapProcessingContext)
              : buildSwapProcessingSteps(swapProcessingContext)
          }
          progressIndex={
            authoritative
              ? swapAuthoritativeStepperIndex(executionPhase)
              : swapProcessingStepperIndex(executionPhase)
          }
          completedProgressIndex={
            authoritative ? SWAP_AUTHORITATIVE_COMPLETED_INDEX : SWAP_PROCESSING_COMPLETED_INDEX
          }
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
              <b className="v-tnum">{swapProcessingContext.receiveLabel}</b> ont été crédités sur
              votre wallet.
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

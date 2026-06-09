'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import {
  PortalBundleReviewStep,
  type PortalBundleReviewContext,
} from '@/components/portal/bundles/PortalBundleReviewStep'
import { useBundleLifiInvest } from '@/components/portal/bundles/useBundleLifiInvest'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import {
  buildBundleInvestProcessingStepsDynamic,
  buildBundleReviewPreviewSteps,
  bundleInvestDynamicProcessingProgressIndex,
  type BundleInvestProcessingProgress,
  resolveBundleFailureCopy,
  resolveBundleInvestResultVariant,
} from '@/components/portal/transaction/mappers/bundleSteps'
import {
  BUNDLE_BACKEND_LOCK_PENDING_LABEL,
  BUNDLE_FLOW_UI,
  BUNDLE_RESULT_ACTIONS,
  BUNDLE_REVIEW_UI,
  BUNDLE_TERMINAL_IMPOSSIBLE,
  BUNDLE_TERMINAL_PARTIAL_ALLOCATION,
  BUNDLE_TERMINAL_RECONCILIATION,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import type { BundleInvestRunResult } from '@/components/portal/bundles/useBundleLifiInvest'
import {
  clearBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import {
  BundleInvestTerminalError,
  buildBundleInvestTechnicalDetails,
  detectPartialBundleSuccess,
} from '@/lib/portal/bundleInvestTerminalization'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'
import type { PortalBundleFlowScene, PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { navigateAfterTransactionSuccess } from '@/lib/portal/postTransactionWalletNav'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

export type PortalBundleExecutionScene = Extract<
  PortalBundleFlowScene,
  'review' | 'processing' | 'result'
>

type Props = {
  flowScene: PortalBundleExecutionScene
  onFlowSceneChange: (scene: PortalBundleFlowScene) => void
  onBlocked: (message: string) => void
  bundle: PortalCryptoBundle
  fundingAsset: string
  amount: string
  parsedAmount: number
  reviewContext: PortalBundleReviewContext
  swapMockMode: boolean
  resumeSession: BundleInvestSession | null
  portfolioReady: boolean
  onProcessingClose: () => void
  onResultClose: () => void
}

/** Review sans hooks wagmi — évite WagmiProviderNotFoundError (R4.5-F5-A). */
function PortalBundleReviewScene({
  reviewContext,
  onFlowSceneChange,
  portfolioReady,
}: Pick<Props, 'reviewContext' | 'onFlowSceneChange' | 'portfolioReady'>) {
  const { privyReady } = usePortalAuthPrivy()
  const [signingPrep, setSigningPrep] = useState(false)
  const submitGuardRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    setSigningPrep(true)
    void (async () => {
      try {
        await waitForPrivyClientReady(() => privyReady, { timeoutMs: 30_000 })
      } catch {
        /* Review still renders */
      } finally {
        if (!cancelled) setSigningPrep(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [privyReady])

  const onReviewConfirm = useCallback(() => {
    onFlowSceneChange('processing')
  }, [onFlowSceneChange])

  const onBackToSetup = useCallback(() => {
    onFlowSceneChange('setup')
  }, [onFlowSceneChange])

  const reviewDisabled = !portfolioReady || submitGuardRef.current

  return (
    <>
      {signingPrep ? (
        <div
          className="mb-4 flex items-center gap-2 rounded-lg border border-v-fg-10 bg-v-fg-02 px-3 py-2 font-ui text-[13px] text-v-fg-muted"
          aria-live="polite"
        >
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          {BUNDLE_FLOW_UI.preparingSecureConfirmation}
        </div>
      ) : null}
      <PortalBundleReviewStep
        context={reviewContext}
        onConfirm={onReviewConfirm}
        onBack={onBackToSetup}
        confirmDisabled={reviewDisabled}
      />
    </>
  )
}

/** Processing / result — useBundleLifiInvest sous WagmiProvider (`invest/bundle/(tx)/layout`). */
function PortalBundleWeb3ExecutionRunner({
  flowScene,
  onFlowSceneChange,
  onBlocked,
  bundle,
  fundingAsset,
  amount,
  parsedAmount,
  reviewContext,
  swapMockMode,
  resumeSession,
  portfolioReady,
  onProcessingClose,
  onResultClose,
}: Props) {
  const router = useRouter()
  const { chain, walletScope, walletScopeId } = usePortalExecutionScope()
  const { privyReady } = usePortalAuthPrivy()
  const privyReadyRef = useRef(privyReady)

  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [processingProgress, setProcessingProgress] = useState<BundleInvestProcessingProgress>({
    stage: 'preparing',
  })
  const [displayProgressIndex, setDisplayProgressIndex] = useState(0)
  const maxProgressIndexRef = useRef(0)
  const [failureCopy, setFailureCopy] = useState(() => resolveBundleFailureCopy(null))
  const [resultVariant, setResultVariant] = useState<PortalBundleInvestResultVariant>('success')
  const [resultAmount, setResultAmount] = useState(0)
  const [resultTechnicalDetails, setResultTechnicalDetails] = useState<
    TransactionTechnicalDetailsRow[]
  >([])
  const submitGuardRef = useRef(false)
  const executionStartedRef = useRef(false)
  const executionModeRef = useRef<'none' | 'invest'>('none')

  const { runInvest, inFlightRef } = useBundleLifiInvest(
    swapMockMode,
    fundingAsset,
    setExecutionPhase,
    undefined,
    setProcessingProgress,
  )

  useEffect(() => {
    privyReadyRef.current = privyReady
  }, [privyReady])

  const processingContext = {
    amountLabel: `${formatBundleUsdcAmount(parsedAmount > 0 ? parsedAmount : amount)} ${fundingAsset}`,
    bundleLabel: bundle.title,
  }

  const onViewBasket = useCallback(() => {
    const portfolioId = bundle.portfolioId?.trim()
    if (!portfolioId) {
      onResultClose()
      return
    }
    void navigateAfterTransactionSuccess(
      router,
      { kind: 'crypto_bundle', portfolioId },
      { chain, walletScope, walletScopeId },
    )
  }, [bundle.portfolioId, chain, onResultClose, router, walletScope, walletScopeId])

  const allocationAssetsForSteps = useMemo(() => {
    if (processingProgress.allocationAssets?.length) {
      return processingProgress.allocationAssets
    }
    return reviewContext.targetAllocationRows.map((row) => row.asset)
  }, [processingProgress.allocationAssets, reviewContext.targetAllocationRows])

  const processingSteps = useMemo(
    () =>
      buildBundleInvestProcessingStepsDynamic({
        bundleLabel: bundle.title,
        entryAsset: processingProgress.entryAsset ?? fundingAsset,
        allocationAssets: allocationAssetsForSteps,
      }),
    [
      allocationAssetsForSteps,
      bundle.title,
      fundingAsset,
      processingProgress.entryAsset,
    ],
  )

  const rawProgressIndex = bundleInvestDynamicProcessingProgressIndex(
    processingProgress,
    processingSteps.length,
  )

  useEffect(() => {
    maxProgressIndexRef.current = Math.max(maxProgressIndexRef.current, rawProgressIndex)
    setDisplayProgressIndex(maxProgressIndexRef.current)
  }, [rawProgressIndex])

  useEffect(() => {
    if (flowScene === 'processing') {
      maxProgressIndexRef.current = 0
      setDisplayProgressIndex(0)
      setProcessingProgress({ stage: 'preparing', entryAsset: fundingAsset })
    }
  }, [flowScene, fundingAsset])

  const runExecution = useCallback(
    async (runner: () => Promise<unknown>) => {
      setExecutionPhase('preparing')
      submitGuardRef.current = true
      try {
        await waitForPrivyClientReady(() => privyReadyRef.current, { timeoutMs: 30_000 })
        const outcome = await runner()

        if (
          outcome &&
          typeof outcome === 'object' &&
          'kind' in outcome &&
          (outcome as { kind: string }).kind === 'already_pending'
        ) {
          const pending = outcome as {
            kind: 'already_pending'
            payload: { message: string }
          }
          onBlocked(pending.payload.message)
          return
        }

        const runResult = outcome as BundleInvestRunResult | undefined
        invalidatePortalCache('portal:markets')
        invalidatePortalCache('portal:crypto-wallet')
        invalidatePortalCache('portal:dashboard')

        setResultAmount(
          resumeSession?.fundingAmount ?? (parsedAmount > 0 ? parsedAmount : Number(amount)),
        )
        const variant = resolveBundleInvestResultVariant(
          runResult?.invest,
          runResult?.finalize,
          runResult?.terminalStatus,
        )
        setResultVariant(variant)
        if (
          runResult?.terminalStatus &&
          [
            'completed_full_allocation',
            'completed_partial_allocation',
            'failed_no_allocation',
            'v3_deposit_queued',
          ].includes(runResult.terminalStatus)
        ) {
          clearBundleInvestSession(bundle.portfolioId!)
        }
        if (variant === 'completed_partial_allocation') {
          setFailureCopy(BUNDLE_TERMINAL_PARTIAL_ALLOCATION)
          setResultTechnicalDetails(
            runResult?.backendLockPending
              ? [{ label: 'État technique', value: BUNDLE_BACKEND_LOCK_PENDING_LABEL }]
              : [],
          )
        } else if (variant === 'reconciliation_required') {
          setFailureCopy(BUNDLE_TERMINAL_RECONCILIATION)
          const failedLeg = runResult?.invest.allocation_details?.find(
            (leg) => leg.status !== 'completed' && leg.status !== 'confirmed',
          )
          setResultTechnicalDetails(
            buildBundleInvestTechnicalDetails({
              batchId: runResult?.invest.batch_id,
              failedAsset: failedLeg?.asset,
              legStatus: failedLeg?.status,
            }),
          )
        } else {
          setResultTechnicalDetails([])
        }
        onFlowSceneChange('result')
      } catch (err) {
        setExecutionPhase('failed')
        if (err instanceof BundleInvestTerminalError) {
          setResultVariant(err.variant)
          setFailureCopy(
            err.variant === 'reconciliation_required'
              ? BUNDLE_TERMINAL_RECONCILIATION
              : resolveBundleFailureCopy(err),
          )
          setResultTechnicalDetails(err.technicalDetails ?? [])
        } else {
          const partial = detectPartialBundleSuccess(resumeSession?.invest)
          setResultVariant(partial ? 'reconciliation_required' : 'impossible')
          setFailureCopy(
            partial ? BUNDLE_TERMINAL_RECONCILIATION : resolveBundleFailureCopy(err),
          )
          setResultTechnicalDetails(
            partial
              ? buildBundleInvestTechnicalDetails({
                  batchId: resumeSession?.batchId,
                })
              : [],
          )
        }
        onFlowSceneChange('result')
      } finally {
        submitGuardRef.current = false
      }
    },
    [
      amount,
      bundle.portfolioId,
      onBlocked,
      onFlowSceneChange,
      parsedAmount,
      resumeSession?.batchId,
      resumeSession?.fundingAmount,
      resumeSession?.invest,
    ],
  )

  const executeProcessing = useCallback(async () => {
    if (executionStartedRef.current || submitGuardRef.current) return
    if (executionModeRef.current !== 'invest') return

    executionStartedRef.current = true

    if (!portfolioReady || inFlightRef.current) return
    const parsed = parsedAmount
    if (!Number.isFinite(parsed) || parsed <= 0) return
    await runExecution(() =>
      runInvest({
        portfolio_id: bundle.portfolioId!,
        funding_asset: fundingAsset,
        funding_amount: parsed,
      }),
    )
  }, [
    bundle.portfolioId,
    fundingAsset,
    inFlightRef,
    parsedAmount,
    portfolioReady,
    runExecution,
    runInvest,
  ])

  useEffect(() => {
    if (flowScene === 'processing') {
      executionModeRef.current = 'invest'
      executionStartedRef.current = false
    }
  }, [flowScene])

  useEffect(() => {
    if (flowScene !== 'processing') return
    void executeProcessing()
  }, [executeProcessing, flowScene])

  const successSteps = buildBundleReviewPreviewSteps(processingContext).map((step) => ({
    name: step.label,
    body: step.subtext,
  }))

  if (flowScene === 'processing') {
    return (
      <TransactionProcessingPage
        title={BUNDLE_FLOW_UI.processingTitle}
        lead={BUNDLE_FLOW_UI.processingLead(
          processingContext.amountLabel,
          processingContext.bundleLabel,
        )}
        steps={processingSteps}
        progressIndex={displayProgressIndex}
        completedProgressIndex={processingSteps.length}
        onClose={onProcessingClose}
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {resultVariant === 'success' ? (
        <TransactionResultPage
          variant="success"
          layout="full"
          title={BUNDLE_FLOW_UI.successTitle}
          lead={
            <>
              <b className="v-tnum">
                {formatBundleUsdcAmount(resultAmount)} {fundingAsset}
              </b>{' '}
              ont été investis sur {bundle.title}.
            </>
          }
          subtitle={BUNDLE_FLOW_UI.successSubtitle}
          stepsTitle="Étapes réalisées"
          steps={successSteps}
          summary={[
            { k: BUNDLE_REVIEW_UI.bundle, v: bundle.title },
            { k: BUNDLE_REVIEW_UI.youInvest, v: `${formatBundleUsdcAmount(resultAmount)} ${fundingAsset}` },
          ]}
          primaryAction={{
            label: BUNDLE_FLOW_UI.viewBasketCta,
            onClick: onViewBasket,
          }}
          onClose={onResultClose}
        />
      ) : null}
      {resultVariant === 'v3_deposit_queued' ? (
        <TransactionResultPage
          variant="success"
          layout="full"
          title={BUNDLE_FLOW_UI.v3QueuedTitle}
          lead={
            <>
              <b className="v-tnum">
                {formatBundleUsdcAmount(resultAmount)} {fundingAsset}
              </b>{' '}
              ont été transférés vers {bundle.title}.
            </>
          }
          subtitle={BUNDLE_FLOW_UI.v3QueuedSubtitle}
          stepsTitle="Étapes réalisées"
          steps={[
            { name: 'Transfert des fonds', body: 'Vos fonds ont été crédités sur le panier.' },
            {
              name: 'Rééquilibrage automatique',
              body: 'Le rééquilibrage V3 se poursuit en arrière-plan (quelques minutes).',
            },
          ]}
          summary={[
            { k: BUNDLE_REVIEW_UI.bundle, v: bundle.title },
            { k: BUNDLE_REVIEW_UI.youInvest, v: `${formatBundleUsdcAmount(resultAmount)} ${fundingAsset}` },
          ]}
          primaryAction={{
            label: BUNDLE_FLOW_UI.viewBasketCta,
            onClick: onViewBasket,
          }}
          onClose={onResultClose}
        />
      ) : null}
      {resultVariant === 'completed_partial_allocation' ? (
        <TransactionResultPage
          variant="success"
          layout="full"
          title={BUNDLE_TERMINAL_PARTIAL_ALLOCATION.title}
          lead={BUNDLE_TERMINAL_PARTIAL_ALLOCATION.lines[0]}
          subtitle=""
          steps={[]}
          summary={[]}
          note={
            resultTechnicalDetails.length > 0 ? resultTechnicalDetails[0]?.value : undefined
          }
          primaryAction={{
            label: BUNDLE_FLOW_UI.viewBasketCta,
            onClick: onViewBasket,
          }}
          onClose={onResultClose}
        />
      ) : null}
      {resultVariant === 'reconciliation_required' ? (
        <TransactionResultPage
          variant="reconciliation_required"
          copy={BUNDLE_TERMINAL_RECONCILIATION}
          onClose={onResultClose}
          closeLabel={BUNDLE_RESULT_ACTIONS.close}
          primaryAction={{
            label: BUNDLE_FLOW_UI.viewBasketCta,
            onClick: onViewBasket,
          }}
          technicalDetails={
            resultTechnicalDetails.length > 0 ? resultTechnicalDetails : undefined
          }
          technicalDetailsTitle={BUNDLE_REVIEW_UI.technicalDetailsTitle}
        />
      ) : null}
      {resultVariant === 'impossible' ? (
        <TransactionResultPage
          variant="impossible"
          copy={
            failureCopy.title === BUNDLE_TERMINAL_IMPOSSIBLE.title
              ? failureCopy
              : BUNDLE_TERMINAL_IMPOSSIBLE
          }
          onClose={onResultClose}
          closeLabel={BUNDLE_RESULT_ACTIONS.close}
        />
      ) : null}
    </div>
  )
}

/**
 * Bundle invest review / processing / result (R4.5-F5-A).
 * WagmiProvider fourni par `invest/bundle/(tx)/layout.tsx`.
 */
export function PortalBundleExecutionController(props: Props) {
  if (props.flowScene === 'review') {
    return <PortalBundleReviewScene {...props} />
  }
  return <PortalBundleWeb3ExecutionRunner {...props} />
}

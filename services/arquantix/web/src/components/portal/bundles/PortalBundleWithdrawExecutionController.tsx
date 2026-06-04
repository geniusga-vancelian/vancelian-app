'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import {
  PortalBundleWithdrawReviewStep,
  type PortalBundleWithdrawReviewContext,
} from '@/components/portal/bundles/PortalBundleWithdrawReviewStep'
import { useBundleLifiWithdraw } from '@/components/portal/bundles/useBundleLifiWithdraw'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import {
  buildBundleWithdrawProcessingStepsDynamic,
  buildBundleWithdrawReviewPreviewSteps,
  bundleWithdrawDynamicProcessingProgressIndex,
  type BundleWithdrawProcessingProgress,
} from '@/components/portal/transaction/mappers/bundleSteps'
import {
  BUNDLE_RESULT_ACTIONS,
  BUNDLE_WITHDRAW_FLOW_UI,
  BUNDLE_WITHDRAW_TERMINAL_IMPOSSIBLE,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import {
  clearBundleWithdrawSession,
  type BundleWithdrawSession,
} from '@/lib/portal/bundleWithdrawSession'
import { mapWithdrawStatusToDisplayPhase } from '@/lib/portal/bundleWithdrawFormat'
import { bundleWithdrawPhaseLabel } from '@/lib/portal/bundleWithdrawLabels'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'
import type { PortalBundleFlowScene, PortalBundleWithdrawResultVariant } from '@/lib/portal/bundleFlowTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

export type PortalBundleWithdrawExecutionScene = Extract<
  PortalBundleFlowScene,
  'review' | 'processing' | 'result'
>

type Props = {
  flowScene: PortalBundleWithdrawExecutionScene
  onFlowSceneChange: (scene: PortalBundleFlowScene) => void
  onBlocked: (message: string) => void
  portfolioId: string
  portfolioName: string
  entryAsset: string
  parsedAmount: number
  fullWithdraw: boolean
  reviewContext: PortalBundleWithdrawReviewContext
  swapMockMode: boolean
  resumeSession: BundleWithdrawSession | null
  onProcessingClose: () => void
  onResultClose: () => void
  onCompleted?: () => void
}

function PortalBundleWithdrawReviewScene({
  reviewContext,
  onFlowSceneChange,
}: Pick<Props, 'reviewContext' | 'onFlowSceneChange'>) {
  const { privyReady } = usePortalAuthPrivy()
  const [signingPrep, setSigningPrep] = useState(false)

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

  return (
    <>
      {signingPrep ? (
        <div
          className="mb-4 flex items-center gap-2 rounded-lg border border-v-fg-10 bg-v-fg-02 px-3 py-2 font-ui text-[13px] text-v-fg-muted"
          aria-live="polite"
        >
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          {BUNDLE_WITHDRAW_FLOW_UI.preparingSecureConfirmation}
        </div>
      ) : null}
      <PortalBundleWithdrawReviewStep
        context={reviewContext}
        onConfirm={() => onFlowSceneChange('processing')}
        onBack={() => onFlowSceneChange('setup')}
      />
    </>
  )
}

function PortalBundleWithdrawWeb3ExecutionRunner({
  flowScene,
  onFlowSceneChange,
  onBlocked,
  portfolioId,
  portfolioName,
  entryAsset,
  parsedAmount,
  fullWithdraw,
  reviewContext,
  swapMockMode,
  resumeSession,
  onProcessingClose,
  onResultClose,
  onCompleted,
}: Props) {
  const { privyReady } = usePortalAuthPrivy()
  const privyReadyRef = useRef(privyReady)

  const [processingProgress, setProcessingProgress] = useState<BundleWithdrawProcessingProgress>({
    stage: 'preparing',
  })
  const [displayProgressIndex, setDisplayProgressIndex] = useState(0)
  const maxProgressIndexRef = useRef(0)
  const [resultVariant, setResultVariant] = useState<PortalBundleWithdrawResultVariant>('success')
  const [resultPhaseLabel, setResultPhaseLabel] = useState<string | null>(null)
  const [failureMessage, setFailureMessage] = useState<string | null>(null)
  const submitGuardRef = useRef(false)
  const executionStartedRef = useRef(false)

  const { runWithdraw, resumeSession: resumeWithdraw, inFlightRef } = useBundleLifiWithdraw(
    swapMockMode,
    entryAsset,
    undefined,
    undefined,
    setProcessingProgress,
  )

  useEffect(() => {
    privyReadyRef.current = privyReady
  }, [privyReady])

  const processingContext = useMemo(
    () => ({
      amountLabel: reviewContext.amountLabel,
      bundleLabel: portfolioName,
    }),
    [portfolioName, reviewContext.amountLabel],
  )

  const unwindAssetsForSteps = useMemo(() => {
    if (processingProgress.unwindAssets?.length) {
      return processingProgress.unwindAssets
    }
    return []
  }, [processingProgress.unwindAssets])

  const processingSteps = useMemo(
    () =>
      buildBundleWithdrawProcessingStepsDynamic({
        entryAsset: processingProgress.entryAsset ?? entryAsset,
        unwindAssets: unwindAssetsForSteps,
      }),
    [entryAsset, processingProgress.entryAsset, unwindAssetsForSteps],
  )

  const rawProgressIndex = bundleWithdrawDynamicProcessingProgressIndex(
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
      setProcessingProgress({ stage: 'preparing', entryAsset })
    }
  }, [entryAsset, flowScene])

  const runExecution = useCallback(
    async (runner: () => Promise<unknown>) => {
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

        const runResult = outcome as {
          withdraw?: { status?: string; release?: { released?: boolean } }
        }
        const phase = mapWithdrawStatusToDisplayPhase(
          runResult.withdraw?.status,
          undefined,
          runResult.withdraw?.release ?? null,
        )
        setResultPhaseLabel(bundleWithdrawPhaseLabel(phase))
        setResultVariant('success')
        invalidatePortalCache('portal:crypto-wallet')
        invalidatePortalCache(`portal:crypto-wallet:bundle:${portfolioId}`)
        invalidatePortalCache('portal:dashboard')
        invalidatePortalCache('portal:markets')
        clearBundleWithdrawSession(portfolioId)
        onCompleted?.()
        onFlowSceneChange('result')
      } catch (err) {
        setFailureMessage(err instanceof Error ? err.message : 'Retrait impossible')
        setResultVariant('impossible')
        onFlowSceneChange('result')
      } finally {
        submitGuardRef.current = false
      }
    },
    [onBlocked, onCompleted, onFlowSceneChange, portfolioId],
  )

  const executeProcessing = useCallback(async () => {
    if (executionStartedRef.current || submitGuardRef.current) return
    executionStartedRef.current = true

    if (inFlightRef.current) return

    if (resumeSession) {
      await runExecution(() => resumeWithdraw(resumeSession))
      return
    }

    await runExecution(() =>
      runWithdraw({
        portfolio_id: portfolioId,
        full_withdraw: fullWithdraw,
        withdraw_amount: fullWithdraw ? undefined : parsedAmount,
      }),
    )
  }, [
    fullWithdraw,
    inFlightRef,
    parsedAmount,
    portfolioId,
    resumeSession,
    resumeWithdraw,
    runExecution,
    runWithdraw,
  ])

  useEffect(() => {
    if (flowScene !== 'processing') return
    void executeProcessing()
  }, [executeProcessing, flowScene])

  const successSteps = buildBundleWithdrawReviewPreviewSteps(processingContext).map((step) => ({
    name: step.label,
    body: step.subtext,
  }))

  if (flowScene === 'processing') {
    return (
      <TransactionProcessingPage
        title={BUNDLE_WITHDRAW_FLOW_UI.processingTitle}
        lead={BUNDLE_WITHDRAW_FLOW_UI.processingLead(
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

  if (resultVariant === 'success') {
    return (
      <TransactionResultPage
        variant="success"
        layout="full"
        title={BUNDLE_WITHDRAW_FLOW_UI.successTitle}
        lead={
          <>
            <b className="v-tnum">
              {formatBundleUsdcAmount(parsedAmount)} {entryAsset}
            </b>{' '}
            ont été retirés depuis {portfolioName}.
          </>
        }
        subtitle={resultPhaseLabel ?? BUNDLE_WITHDRAW_FLOW_UI.successSubtitle}
        steps={successSteps}
        stepsTitle="Étapes réalisées"
        primaryAction={{
          label: BUNDLE_WITHDRAW_FLOW_UI.viewTradingCta,
          onClick: onResultClose,
        }}
        onClose={onResultClose}
      />
    )
  }

  return (
    <TransactionResultPage
      variant="impossible"
      copy={{
        title: BUNDLE_WITHDRAW_TERMINAL_IMPOSSIBLE.title,
        lines: [failureMessage ?? BUNDLE_WITHDRAW_TERMINAL_IMPOSSIBLE.lines[0]!],
      }}
      onClose={onResultClose}
      closeLabel={BUNDLE_RESULT_ACTIONS.close}
      primaryAction={{
        label: BUNDLE_RESULT_ACTIONS.close,
        onClick: onResultClose,
      }}
    />
  )
}

/** Retrait bundle review / processing / result — Wagmi via `invest/bundle/(tx)/layout`. */
export function PortalBundleWithdrawExecutionController(props: Props) {
  if (props.flowScene === 'review') {
    return <PortalBundleWithdrawReviewScene {...props} />
  }
  return <PortalBundleWithdrawWeb3ExecutionRunner {...props} />
}

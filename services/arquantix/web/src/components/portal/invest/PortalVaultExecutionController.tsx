'use client'

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import {
  PortalVaultReviewStep,
  type PortalVaultReviewContext,
} from '@/components/portal/invest/PortalVaultReviewStep'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import { TransactionTechnicalDetails } from '@/components/portal/transaction/TransactionTechnicalDetails'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  buildVaultProcessingSteps,
  buildVaultSuccessSteps,
  buildVaultSuccessSummary,
  buildVaultTechnicalDetailRows,
  resolveVaultFailureCopy,
  vaultProcessingStepperIndex,
  vaultSuccessCopy,
  VAULT_PROCESSING_COMPLETED_INDEX,
} from '@/components/portal/transaction/mappers/vaultSteps'
import { VAULT_FLOW_UI, VAULT_RESULT_IMPOSSIBLE_ACTIONS } from '@/components/portal/transaction/mappers/vaultUiCopy'
import { getPortalDefiIntegrationLabel } from '@/lib/portal/morphoConstants'
import { invFmtAmount, type PortalInvestSource, type PortalInvestTarget } from '@/lib/portal/portalInvestFlowFormat'
import {
  usePortalLedgityVaultExecution,
} from '@/lib/portal/usePortalLedgityVaultExecution'
import {
  usePortalMorphoVaultExecution,
} from '@/lib/portal/usePortalMorphoVaultExecution'
import type {
  PortalVaultExecutionPhase,
  PortalVaultFlowScene,
  PortalVaultOperation,
} from '@/lib/portal/vaultFlowTypes'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

export type PortalVaultExecutionScene = Extract<PortalVaultFlowScene, 'review' | 'processing' | 'result'>

export type PortalVaultProcessingContext = {
  amountLabel: string
  vaultLabel: string
  assetSymbol: string
}

type Props = {
  flowScene: PortalVaultExecutionScene
  onFlowSceneChange: (scene: PortalVaultFlowScene) => void
  presentation: 'invest' | 'savings'
  isLedgity: boolean
  integrationMode: 'direct_morpho' | 'ledgity_vault'
  vaultAddress: string
  provider: string
  operation: PortalVaultOperation
  normalizedAmount: string
  numeric: number
  walletAddress: string
  reviewContext: PortalVaultReviewContext
  processingContext: PortalVaultProcessingContext
  disclaimer: string
  source: PortalInvestSource
  target: PortalInvestTarget
  onClose: () => void
  onExecutionSuccess?: () => void | Promise<void>
}

function createIdempotencyKey(prefix: 'morpho' | 'ledgity'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function wrapSavings(children: ReactNode, className?: string) {
  return (
    <article className={`card-simple overflow-hidden !w-full${className ? ` ${className}` : ''}`}>
      {children}
    </article>
  )
}

/** Review sans hooks wagmi — évite WagmiProviderNotFoundError (R4.5-F4). */
function PortalVaultReviewScene({
  reviewContext,
  onFlowSceneChange,
  presentation,
}: Pick<Props, 'reviewContext' | 'onFlowSceneChange' | 'presentation'>) {
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

  const onReviewConfirm = useCallback(() => {
    onFlowSceneChange('processing')
  }, [onFlowSceneChange])

  const onBackToSetup = useCallback(() => {
    onFlowSceneChange('setup')
  }, [onFlowSceneChange])

  const inner = (
    <>
      {signingPrep ? (
        <div
          className="mb-4 flex items-center gap-2 rounded-lg border border-v-fg-10 bg-v-fg-02 px-3 py-2 font-ui text-[13px] text-v-fg-muted"
          aria-live="polite"
        >
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          {VAULT_FLOW_UI.preparingSecureConfirmation}
        </div>
      ) : null}
      <PortalVaultReviewStep
        context={reviewContext}
        onConfirm={onReviewConfirm}
        onBack={onBackToSetup}
      />
    </>
  )

  return presentation === 'savings' ? wrapSavings(inner) : inner
}

/** Processing / result — hooks Morpho/Ledgity sous WagmiProvider. */
function PortalVaultWeb3ExecutionRunner({
  flowScene,
  onFlowSceneChange,
  presentation,
  isLedgity,
  integrationMode,
  vaultAddress,
  provider,
  operation,
  normalizedAmount,
  numeric,
  walletAddress,
  reviewContext,
  processingContext,
  disclaimer,
  source,
  target,
  onClose,
  onExecutionSuccess,
}: Props) {
  const { execute: executeMorpho } = usePortalMorphoVaultExecution()
  const { execute: executeLedgity } = usePortalLedgityVaultExecution()

  const [executionPhase, setExecutionPhase] = useState<PortalVaultExecutionPhase>('idle')
  const [failureCopy, setFailureCopy] = useState(() => resolveVaultFailureCopy(null))
  const [txHash, setTxHash] = useState<string | null>(null)
  const [resultAmount, setResultAmount] = useState(0)
  const idempotencyKeyRef = useRef<string | null>(null)
  const executionStartedRef = useRef(false)

  const vaultAssetSymbol = reviewContext.assetSymbol
  const integrationLabel = isLedgity ? 'Ledgity vault' : 'Direct vault'

  const resetExecution = useCallback(() => {
    setExecutionPhase('idle')
    setFailureCopy(resolveVaultFailureCopy(null))
    executionStartedRef.current = false
  }, [])

  const runExecution = useCallback(async () => {
    if (!walletAddress || !normalizedAmount || Number(normalizedAmount) <= 0) return

    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = createIdempotencyKey(isLedgity ? 'ledgity' : 'morpho')
    }

    setExecutionPhase('preparing')
    try {
      const execute = isLedgity ? executeLedgity : executeMorpho
      const hash = await execute({
        vaultAddress,
        operation,
        amount: normalizedAmount,
        idempotencyKey: idempotencyKeyRef.current,
        onPhaseChange: setExecutionPhase,
      })
      setResultAmount(numeric)
      setTxHash(typeof hash === 'string' ? hash : null)
      setExecutionPhase('confirmed')
      onFlowSceneChange('result')
      idempotencyKeyRef.current = null
      await onExecutionSuccess?.()
    } catch (e) {
      setExecutionPhase('failed')
      setFailureCopy(resolveVaultFailureCopy(e))
      onFlowSceneChange('result')
    }
  }, [
    executeLedgity,
    executeMorpho,
    isLedgity,
    normalizedAmount,
    numeric,
    onExecutionSuccess,
    onFlowSceneChange,
    operation,
    vaultAddress,
    walletAddress,
  ])

  useEffect(() => {
    if (flowScene !== 'processing' || executionStartedRef.current) return
    executionStartedRef.current = true
    void runExecution()
  }, [flowScene, runExecution])

  const onBackToSetup = useCallback(() => {
    resetExecution()
    onFlowSceneChange('setup')
  }, [onFlowSceneChange, resetExecution])

  const onResultRetry = useCallback(() => {
    resetExecution()
    onFlowSceneChange('review')
  }, [onFlowSceneChange, resetExecution])

  const resultTechRows = useMemo(
    () =>
      buildVaultTechnicalDetailRows({
        vaultAddress,
        providerLabel: provider,
        integrationLabel: presentation === 'savings' ? getPortalDefiIntegrationLabel(integrationMode) : integrationLabel,
        sourceAsset: source.techSource,
        receivedAsset: target.tech,
        disclaimer,
        txHash,
      }),
    [
      disclaimer,
      integrationLabel,
      integrationMode,
      presentation,
      provider,
      source.techSource,
      target.tech,
      txHash,
      vaultAddress,
    ],
  )

  const successCopy = vaultSuccessCopy(operation)
  const successSteps = buildVaultSuccessSteps(operation, processingContext)
  const successSummary = buildVaultSuccessSummary(
    operation,
    processingContext,
    reviewContext.yieldPct,
  )
  const successNote =
    operation === 'deposit' ? VAULT_FLOW_UI.successNoteDeposit : VAULT_FLOW_UI.successNoteWithdraw
  const successStepsTitle =
    operation === 'deposit'
      ? VAULT_FLOW_UI.successStepsTitleDeposit
      : VAULT_FLOW_UI.successStepsTitleWithdraw

  const processingBlock = (
    <TransactionProcessingPage
      title={VAULT_FLOW_UI.processingTitle}
      lead={
        operation === 'deposit'
          ? VAULT_FLOW_UI.processingLeadDeposit(
              processingContext.amountLabel,
              processingContext.vaultLabel,
            )
          : VAULT_FLOW_UI.processingLeadWithdraw(
              processingContext.amountLabel,
              processingContext.vaultLabel,
            )
      }
      steps={buildVaultProcessingSteps(operation, processingContext)}
      progressIndex={vaultProcessingStepperIndex(executionPhase)}
      completedProgressIndex={VAULT_PROCESSING_COMPLETED_INDEX}
      onClose={onBackToSetup}
    />
  )

  const resultBlock = (
    <>
      {executionPhase === 'confirmed' ? (
        <TransactionResultPage
          variant="success"
          layout="full"
          title={successCopy.title}
          lead={
            <>
              <b className="v-tnum">
                {invFmtAmount(resultAmount, resultAmount % 1 === 0 ? 0 : 2)} {vaultAssetSymbol}
              </b>{' '}
              {operation === 'deposit'
                ? `ont été placés sur ${processingContext.vaultLabel}.`
                : `ont été retirés depuis ${processingContext.vaultLabel}.`}
            </>
          }
          stepsTitle={successStepsTitle}
          summaryTitle={VAULT_FLOW_UI.successSummaryTitle}
          steps={successSteps.map((step) => ({
            name: step.name,
            body: <p className="txn-step__amount">{step.body}</p>,
          }))}
          summary={successSummary}
          note={successNote}
          primaryAction={{
            label: presentation === 'invest' ? VAULT_FLOW_UI.viewVaultCta : 'Fermer',
            onClick: onClose,
            icon: presentation === 'invest' ? <KalaiIcon name="wallet" size={16} /> : undefined,
          }}
          onClose={onClose}
        />
      ) : (
        <TransactionResultPage
          variant="impossible"
          copy={failureCopy}
          onRetry={onResultRetry}
          onClose={onClose}
          closeLabel={VAULT_RESULT_IMPOSSIBLE_ACTIONS.close}
          retryLabel={VAULT_RESULT_IMPOSSIBLE_ACTIONS.retry}
        />
      )}
      {executionPhase === 'confirmed' ? <TransactionTechnicalDetails rows={resultTechRows} /> : null}
    </>
  )

  const inner = flowScene === 'processing' ? processingBlock : resultBlock
  const wrapped =
    presentation === 'savings' ? wrapSavings(inner, 'px-4 py-4') : inner

  return wrapped
}

/**
 * Vault review / processing / result (R4.5-F4).
 * WagmiProvider fourni par `invest/vault/(tx)/layout.tsx` (comme wallet/(tx)/swap).
 */
export function PortalVaultExecutionController(props: Props) {
  if (props.flowScene === 'review') {
    return <PortalVaultReviewScene {...props} />
  }
  return <PortalVaultWeb3ExecutionRunner {...props} />
}

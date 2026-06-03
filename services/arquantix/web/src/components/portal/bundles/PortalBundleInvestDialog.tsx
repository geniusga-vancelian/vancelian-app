'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalBundleReviewStep } from '@/components/portal/bundles/PortalBundleReviewStep'
import { useBundleLifiInvest } from '@/components/portal/bundles/useBundleLifiInvest'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import {
  BUNDLE_PROCESSING_COMPLETED_INDEX,
  buildBundleProcessingSteps,
  bundleInvestProcessingStepperIndex,
  resolveBundleFailureCopy,
  resolveBundleInvestResultVariant,
  shouldShowReconciliationForActiveLock,
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
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  fetchActiveBundleInvestLock,
  previewBundleInvest,
  type BundleInvestPreviewPayload,
} from '@/lib/portal/bundleClient'
import type { BundleInvestRunResult } from '@/components/portal/bundles/useBundleLifiInvest'
import {
  displayBundleAssetSymbol,
  formatBundleTargetWeight,
  formatBundleUsdcAmount,
} from '@/lib/portal/bundleFormat'
import {
  clearBundleInvestSession,
  loadBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import {
  BundleInvestTerminalError,
  buildBundleInvestTechnicalDetails,
  detectPartialBundleSuccess,
} from '@/lib/portal/bundleInvestTerminalization'
import type { PortalBundleFlowScene } from '@/lib/portal/bundleFlowTypes'
import type { PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

const PILOT_ENTRY_ASSETS = ['USDC', 'EURC'] as const

type Props = {
  bundle: PortalCryptoBundle
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Page dédiée `/app/invest/bundle/...` — sans overlay modal. */
  asPage?: boolean
}

export function PortalBundleInvestDialog({ bundle, open, onOpenChange, asPage = false }: Props) {
  const { privyReady } = usePortalAuthPrivy()
  const privyReadyRef = useRef(privyReady)
  const [flowScene, setFlowScene] = useState<PortalBundleFlowScene>('setup')
  const [fundingAsset, setFundingAsset] = useState<string>(bundle.entryAssetDefault ?? 'USDC')
  const [amount, setAmount] = useState('')
  const [preview, setPreview] = useState<BundleInvestPreviewPayload | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)
  const [failureCopy, setFailureCopy] = useState(() => resolveBundleFailureCopy(null))
  const [resultVariant, setResultVariant] = useState<PortalBundleInvestResultVariant>('success')
  const [resultAmount, setResultAmount] = useState(0)
  const [activeAllocationAsset, setActiveAllocationAsset] = useState<string | null>(null)
  const [swapMockMode, setSwapMockMode] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)
  const [resumeSession, setResumeSession] = useState<BundleInvestSession | null>(null)
  const [resultTechnicalDetails, setResultTechnicalDetails] = useState<
    TransactionTechnicalDetailsRow[]
  >([])
  const submitGuardRef = useRef(false)
  const executionStartedRef = useRef(false)
  const executionModeRef = useRef<'none' | 'invest' | 'resume'>('none')

  const entryOptions = useMemo(() => {
    const allowed = bundle.entryAssetsAllowed?.length
      ? bundle.entryAssetsAllowed
      : [...PILOT_ENTRY_ASSETS]
    return allowed
      .map((a) => a.toUpperCase())
      .filter((a) => PILOT_ENTRY_ASSETS.includes(a as (typeof PILOT_ENTRY_ASSETS)[number]))
  }, [bundle.entryAssetsAllowed])

  const batchInProgress = flowScene === 'processing' || submitGuardRef.current

  const reset = useCallback(() => {
    setFlowScene('setup')
    setPreview(null)
    setSetupError(null)
    setFailureCopy(resolveBundleFailureCopy(null))
    setResultVariant('success')
    setActiveAllocationAsset(null)
    setExecutionPhase('idle')
    setBlockedMessage(null)
    setResumeSession(null)
    setResultTechnicalDetails([])
    submitGuardRef.current = false
    executionStartedRef.current = false
    executionModeRef.current = 'none'
    setAmount('')
    setFundingAsset(bundle.entryAssetDefault ?? entryOptions[0] ?? 'USDC')
  }, [bundle.entryAssetDefault, entryOptions])

  const { runInvest, inFlightRef } = useBundleLifiInvest(
    swapMockMode,
    fundingAsset,
    setExecutionPhase,
    (_current, _total, asset) => {
      setActiveAllocationAsset(asset)
    },
  )

  const portfolioReady = Boolean(bundle.portfolioId?.trim())

  useEffect(() => {
    privyReadyRef.current = privyReady
  }, [privyReady])

  const showReconciliationTerminal = useCallback(
    (
      session: BundleInvestSession | null,
      lock?: { batch_id: string; status: string },
      failedAsset?: string,
      legStatus?: string,
    ) => {
      setResumeSession(session)
      setResultAmount(session?.fundingAmount ?? 0)
      setResultVariant('reconciliation_required')
      setFailureCopy(BUNDLE_TERMINAL_RECONCILIATION)
      setResultTechnicalDetails(
        buildBundleInvestTechnicalDetails({
          batchId: lock?.batch_id ?? session?.batchId,
          failedAsset,
          legStatus,
          lockStatus: lock?.status,
        }),
      )
      executionModeRef.current = 'none'
      executionStartedRef.current = true
      setFlowScene('result')
    },
    [],
  )

  const refreshLockState = useCallback(async () => {
    if (!portfolioReady) return
    const active = await fetchActiveBundleInvestLock(bundle.portfolioId!)
    const stored = loadBundleInvestSession(bundle.portfolioId!)

    if (active.status === 'active' && active.lock) {
      if (shouldShowReconciliationForActiveLock(active.lock, stored)) {
        const failedLeg = stored?.invest.allocation_details?.find(
          (leg) => leg.status !== 'completed' && leg.status !== 'confirmed',
        )
        showReconciliationTerminal(stored, active.lock, failedLeg?.asset, failedLeg?.status)
        return
      }
      if (stored && detectPartialBundleSuccess(stored.invest, undefined, { lockStatus: active.lock.status })) {
        showReconciliationTerminal(stored, active.lock)
        return
      }
      setBlockedMessage(
        'Un investissement est déjà en cours sur ce portefeuille. Notre équipe finalise la réconciliation si nécessaire.',
      )
      setFlowScene('blocked')
      return
    }

    setBlockedMessage(null)
    if (stored) {
      setResumeSession(stored)
    }
  }, [bundle.portfolioId, portfolioReady, showReconciliationTerminal])

  useEffect(() => {
    if (!open) {
      reset()
      return
    }
    let cancelled = false
    fetchSupportedSwapAssets()
      .then((catalog) => {
        if (!cancelled) setSwapMockMode(Boolean(catalog.mock_mode))
      })
      .catch(() => {
        if (!cancelled) setSwapMockMode(false)
      })
    refreshLockState().catch(() => {
      if (!cancelled) setSetupError('Impossible de vérifier un investissement en cours.')
    })
    return () => {
      cancelled = true
    }
  }, [open, refreshLockState, reset])

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (!next && batchInProgress) {
        const ok = window.confirm(
          'Un investissement est en cours. Fermer maintenant peut laisser une opération incomplète. Continuer ?',
        )
        if (!ok) return
      }
      onOpenChange(next)
    },
    [batchInProgress, onOpenChange],
  )

  const parsedAmount = useMemo(() => Number(amount), [amount])

  const processingContext = useMemo(
    () => ({
      amountLabel: `${formatBundleUsdcAmount(parsedAmount > 0 ? parsedAmount : amount)} ${fundingAsset}`,
      bundleLabel: bundle.title,
      activeAllocationAsset,
    }),
    [activeAllocationAsset, amount, bundle.title, fundingAsset, parsedAmount],
  )

  const reviewContext = useMemo(() => {
    if (!preview) return null
    return {
      bundleTitle: bundle.title,
      fundingAsset,
      amount: parsedAmount,
      preview,
    }
  }, [bundle.title, fundingAsset, parsedAmount, preview])

  const runExecution = useCallback(
    async (runner: () => Promise<unknown>) => {
      setActiveAllocationAsset(null)
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
          setBlockedMessage(pending.payload.message)
          setFlowScene('blocked')
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
          ['completed_full_allocation', 'completed_partial_allocation', 'failed_no_allocation'].includes(
            runResult.terminalStatus,
          )
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
        setFlowScene('result')
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
        setFlowScene('result')
      } finally {
        submitGuardRef.current = false
        setActiveAllocationAsset(null)
      }
    },
    [amount, parsedAmount, resumeSession?.fundingAmount],
  )

  const executeProcessing = useCallback(async () => {
    if (executionStartedRef.current || submitGuardRef.current) return
    if (executionModeRef.current === 'none') return

    executionStartedRef.current = true

    if (executionModeRef.current === 'invest') {
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
    }
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
    if (flowScene !== 'processing') return
    void executeProcessing()
  }, [executeProcessing, flowScene])

  const handleContinueToReview = async () => {
    if (!portfolioReady || batchInProgress || inFlightRef.current) return
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setSetupError('Montant invalide.')
      return
    }
    setPreviewLoading(true)
    setSetupError(null)
    try {
      const result = await previewBundleInvest({
        portfolio_id: bundle.portfolioId!,
        funding_asset: fundingAsset,
        funding_amount: parsedAmount,
      })
      setPreview(result)
      if (result.preview_status === 'invalid') {
        setSetupError('Prévisualisation indisponible pour ce montant.')
        return
      }
      setFlowScene('review')
    } catch (err) {
      setSetupError(err instanceof Error ? err.message : 'Prévisualisation impossible')
    } finally {
      setPreviewLoading(false)
    }
  }

  const onReviewConfirm = () => {
    if (!preview || preview.preview_status === 'invalid') return
    executionModeRef.current = 'invest'
    executionStartedRef.current = false
    setFlowScene('processing')
  }

  const onBackToSetup = () => {
    executionModeRef.current = 'none'
    executionStartedRef.current = false
    setFlowScene('setup')
  }

  const onResultClose = () => {
    reset()
    handleOpenChange(false)
  }

  const setupDisabled =
    !portfolioReady ||
    !privyReady ||
    previewLoading ||
    batchInProgress ||
    inFlightRef.current ||
    flowScene === 'blocked'

  const reviewDisabled =
    !portfolioReady ||
    !privyReady ||
    batchInProgress ||
    inFlightRef.current ||
    preview?.preview_status === 'invalid'

  if (asPage && !open) return null

  const header = asPage ? (
    <header className="space-y-2">
      <h1 className="m-0 font-ui text-[22px] font-semibold text-v-fg">
        {BUNDLE_FLOW_UI.setupTitle(bundle.title)}
      </h1>
      <p className="m-0 font-ui text-[14px] text-v-fg-muted">{BUNDLE_FLOW_UI.setupLead}</p>
    </header>
  ) : (
    <DialogHeader>
      <DialogTitle>{BUNDLE_FLOW_UI.setupTitle(bundle.title)}</DialogTitle>
    </DialogHeader>
  )

  const body = (
    <div className={asPage ? 'flex flex-col gap-4' : undefined}>
      {flowScene === 'setup' || flowScene === 'blocked' ? header : null}

      {flowScene === 'setup' ? (
        <div className="flex flex-col gap-4">
          {!portfolioReady ? (
            <p className="m-0 font-ui text-[13px] text-v-error">
              Ce bundle n’est pas encore provisionné sur votre compte. Rechargez la page Marchés.
            </p>
          ) : null}
          {!privyReady ? (
            <p className="m-0 font-ui text-[13px] text-v-fg-muted">{BUNDLE_FLOW_UI.walletConnecting}</p>
          ) : null}
          <div className="flex flex-col gap-2">
            <Label htmlFor="bundle-entry-asset">Actif d’entrée</Label>
            <select
              id="bundle-entry-asset"
              className="h-10 rounded-v-input border border-v-border bg-v-bg px-3 font-ui text-[14px] text-v-fg"
              value={fundingAsset}
              onChange={(e) => {
                setFundingAsset(e.target.value)
                setPreview(null)
              }}
              disabled={!portfolioReady || batchInProgress}
            >
              {entryOptions.map((asset) => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="bundle-amount">Montant ({fundingAsset})</Label>
            <Input
              id="bundle-amount"
              type="number"
              min="0"
              step="any"
              placeholder="100"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value)
                setPreview(null)
              }}
              disabled={!portfolioReady || batchInProgress}
            />
          </div>

          {preview && preview.allocations && preview.allocations.length > 0 ? (
            <div className="rounded-v-input border border-v-border bg-v-card px-3 py-2">
              <p className="m-0 mb-2 font-ui text-[13px] font-medium text-v-fg">
                {BUNDLE_FLOW_UI.targetAllocationSetup}
              </p>
              <ul className="m-0 list-none space-y-1 p-0">
                {preview.allocations.map((row) => {
                  const label = row.asset_display?.trim() || displayBundleAssetSymbol(row.asset)
                  return (
                    <li
                      key={`${row.asset}-${row.target_weight}`}
                      className="flex justify-between gap-3 font-ui text-[12px] text-v-fg-body"
                    >
                      <span>
                        {label}{' '}
                        <span className="text-v-fg-muted">
                          ({formatBundleTargetWeight(row.target_weight)})
                        </span>
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>
          ) : null}

          {setupError ? <p className="m-0 text-[13px] text-v-error">{setupError}</p> : null}

          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={batchInProgress}
            >
              Annuler
            </Button>
            <Button type="button" onClick={() => void handleContinueToReview()} disabled={setupDisabled}>
              {previewLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Estimation…
                </>
              ) : (
                BUNDLE_FLOW_UI.continueCta
              )}
            </Button>
          </div>
        </div>
      ) : null}

      {flowScene === 'blocked' ? (
        <div className="flex flex-col gap-3">
          <p className="m-0 font-ui text-[14px] text-v-fg">{blockedMessage}</p>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
            Fermer
          </Button>
        </div>
      ) : null}

      {flowScene === 'review' && reviewContext ? (
        <PortalBundleReviewStep
          context={reviewContext}
          onConfirm={onReviewConfirm}
          onBack={onBackToSetup}
          confirmDisabled={reviewDisabled}
        />
      ) : null}

      {flowScene === 'processing' ? (
        <TransactionProcessingPage
          title={BUNDLE_FLOW_UI.processingTitle}
          lead={BUNDLE_FLOW_UI.processingLead(processingContext.amountLabel, processingContext.bundleLabel)}
          steps={buildBundleProcessingSteps('invest', processingContext)}
          progressIndex={bundleInvestProcessingStepperIndex(executionPhase)}
          completedProgressIndex={BUNDLE_PROCESSING_COMPLETED_INDEX}
          onClose={() => {
            if (batchInProgress) {
              const ok = window.confirm(
                'Un investissement est en cours. Fermer maintenant peut laisser une opération incomplète. Continuer ?',
              )
              if (!ok) return
            }
            handleOpenChange(false)
          }}
        />
      ) : null}

      {flowScene === 'result' ? (
        <div className="flex flex-col gap-4">
          {resultVariant === 'success' ? (
            <TransactionResultPage
              variant="success"
              layout="compact"
              title={BUNDLE_FLOW_UI.successTitle}
              lead={
                <>
                  {formatBundleUsdcAmount(resultAmount)} {fundingAsset}
                </>
              }
              subtitle={BUNDLE_FLOW_UI.successSubtitle}
              steps={[]}
              summary={[]}
              primaryAction={{
                label: BUNDLE_FLOW_UI.viewBasketCta,
                onClick: onResultClose,
              }}
              onClose={onResultClose}
            />
          ) : null}
          {resultVariant === 'completed_partial_allocation' ? (
            <TransactionResultPage
              variant="success"
              layout="compact"
              title={BUNDLE_TERMINAL_PARTIAL_ALLOCATION.title}
              lead={BUNDLE_TERMINAL_PARTIAL_ALLOCATION.lines[0]}
              subtitle=""
              steps={[]}
              summary={[]}
              primaryAction={{
                label: BUNDLE_FLOW_UI.viewBasketCta,
                onClick: onResultClose,
              }}
              onClose={onResultClose}
              closeLabel={BUNDLE_RESULT_ACTIONS.close}
              technicalDetails={
                resultTechnicalDetails.length > 0 ? resultTechnicalDetails : undefined
              }
              technicalDetailsTitle={BUNDLE_REVIEW_UI.technicalDetailsTitle}
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
                onClick: onResultClose,
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
              copy={failureCopy.title === BUNDLE_TERMINAL_IMPOSSIBLE.title ? failureCopy : BUNDLE_TERMINAL_IMPOSSIBLE}
              onClose={onResultClose}
              closeLabel={BUNDLE_RESULT_ACTIONS.close}
            />
          ) : null}
        </div>
      ) : null}
    </div>
  )

  if (asPage) return body

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">{body}</DialogContent>
    </Dialog>
  )
}

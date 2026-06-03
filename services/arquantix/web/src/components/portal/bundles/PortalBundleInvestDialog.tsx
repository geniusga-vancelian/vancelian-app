'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import {
  PortalBundleExecutionController,
  type PortalBundleExecutionScene,
} from '@/components/portal/bundles/PortalBundleExecutionController'
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
import {
  displayBundleAssetSymbol,
  formatBundleTargetWeight,
  formatBundleUsdcAmount,
} from '@/lib/portal/bundleFormat'
import {
  loadBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import {
  buildBundleInvestTechnicalDetails,
  detectPartialBundleSuccess,
} from '@/lib/portal/bundleInvestTerminalization'
import {
  shouldShowReconciliationForActiveLock,
} from '@/components/portal/transaction/mappers/bundleSteps'
import {
  BUNDLE_FLOW_UI,
  BUNDLE_RESULT_ACTIONS,
  BUNDLE_REVIEW_UI,
  BUNDLE_TERMINAL_RECONCILIATION,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import type { PortalBundleFlowScene, PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'

const PILOT_ENTRY_ASSETS = ['USDC', 'EURC'] as const

type Props = {
  bundle: PortalCryptoBundle
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Page dédiée `/app/invest/bundle/...` — sans overlay modal. */
  asPage?: boolean
}

/** Bundle invest — setup BFF-only ; exécution Web3 via PortalBundleExecutionController (R4.5-F5-A). */
export function PortalBundleInvestDialog({ bundle, open, onOpenChange, asPage = false }: Props) {
  const [flowScene, setFlowScene] = useState<PortalBundleFlowScene>('setup')
  const [fundingAsset, setFundingAsset] = useState<string>(bundle.entryAssetDefault ?? 'USDC')
  const [amount, setAmount] = useState('')
  const [preview, setPreview] = useState<BundleInvestPreviewPayload | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)
  const [resumeSession, setResumeSession] = useState<BundleInvestSession | null>(null)
  const [swapMockMode, setSwapMockMode] = useState(false)
  /** Terminal lock/reconciliation au open — BFF-only, sans Web3 (E.2-B). */
  const [lockTerminal, setLockTerminal] = useState<{
    variant: PortalBundleInvestResultVariant
    resultAmount: number
    technicalDetails: TransactionTechnicalDetailsRow[]
  } | null>(null)

  const entryOptions = useMemo(() => {
    const allowed = bundle.entryAssetsAllowed?.length
      ? bundle.entryAssetsAllowed
      : [...PILOT_ENTRY_ASSETS]
    return allowed
      .map((a) => a.toUpperCase())
      .filter((a) => PILOT_ENTRY_ASSETS.includes(a as (typeof PILOT_ENTRY_ASSETS)[number]))
  }, [bundle.entryAssetsAllowed])

  const portfolioReady = Boolean(bundle.portfolioId?.trim())
  const parsedAmount = useMemo(() => Number(amount), [amount])
  const isTransactionalExecution =
    flowScene === 'review' ||
    flowScene === 'processing' ||
    (flowScene === 'result' && lockTerminal === null)

  const reset = useCallback(() => {
    setFlowScene('setup')
    setPreview(null)
    setSetupError(null)
    setBlockedMessage(null)
    setResumeSession(null)
    setLockTerminal(null)
    setAmount('')
    setFundingAsset(bundle.entryAssetDefault ?? entryOptions[0] ?? 'USDC')
  }, [bundle.entryAssetDefault, entryOptions])

  const showReconciliationTerminal = useCallback(
    (
      session: BundleInvestSession | null,
      lock?: { batch_id: string; status: string },
      failedAsset?: string,
      legStatus?: string,
    ) => {
      setResumeSession(session)
      setLockTerminal({
        variant: 'reconciliation_required',
        resultAmount: session?.fundingAmount ?? 0,
        technicalDetails: buildBundleInvestTechnicalDetails({
          batchId: lock?.batch_id ?? session?.batchId,
          failedAsset,
          legStatus,
          lockStatus: lock?.status,
        }),
      })
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
      if (!next && flowScene === 'processing') {
        const ok = window.confirm(
          'Un investissement est en cours. Fermer maintenant peut laisser une opération incomplète. Continuer ?',
        )
        if (!ok) return
      }
      onOpenChange(next)
    },
    [flowScene, onOpenChange],
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

  const handleContinueToReview = async () => {
    if (!portfolioReady || previewLoading || flowScene === 'blocked') return
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

  const onResultClose = () => {
    reset()
    handleOpenChange(false)
  }

  const setupDisabled =
    !portfolioReady || previewLoading || flowScene === 'blocked'

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

  const lockTerminalBody =
    flowScene === 'result' && lockTerminal ? (
      <div className="flex flex-col gap-4">
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
            lockTerminal.technicalDetails.length > 0 ? lockTerminal.technicalDetails : undefined
          }
          technicalDetailsTitle={BUNDLE_REVIEW_UI.technicalDetailsTitle}
        />
      </div>
    ) : null

  const body =
    isTransactionalExecution && reviewContext ? (
    <PortalBundleExecutionController
      flowScene={flowScene as PortalBundleExecutionScene}
      onFlowSceneChange={setFlowScene}
      onBlocked={(message) => {
        setBlockedMessage(message)
        setFlowScene('blocked')
      }}
      bundle={bundle}
      fundingAsset={fundingAsset}
      amount={amount}
      parsedAmount={parsedAmount}
      reviewContext={reviewContext}
      swapMockMode={swapMockMode}
      resumeSession={resumeSession}
      portfolioReady={portfolioReady}
      onProcessingClose={() => {
        if (flowScene === 'processing') {
          const ok = window.confirm(
            'Un investissement est en cours. Fermer maintenant peut laisser une opération incomplète. Continuer ?',
          )
          if (!ok) return
        }
        handleOpenChange(false)
      }}
      onResultClose={onResultClose}
    />
  ) : lockTerminalBody ? (
    lockTerminalBody
  ) : (
    <div className={asPage ? 'flex flex-col gap-4' : undefined}>
      {flowScene === 'setup' || flowScene === 'blocked' ? header : null}

      {flowScene === 'setup' ? (
        <div className="flex flex-col gap-4">
          {!portfolioReady ? (
            <p className="m-0 font-ui text-[13px] text-v-error">
              Ce bundle n’est pas encore provisionné sur votre compte. Rechargez la page Marchés.
            </p>
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
              disabled={!portfolioReady}
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
              disabled={!portfolioReady}
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

    </div>
  )

  if (asPage) return body

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">{body}</DialogContent>
    </Dialog>
  )
}

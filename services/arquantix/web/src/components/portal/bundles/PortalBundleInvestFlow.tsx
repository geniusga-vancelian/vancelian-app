'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  PortalBundleExecutionController,
  type PortalBundleExecutionScene,
} from '@/components/portal/bundles/PortalBundleExecutionController'
import { PortalBundleInvestSetup } from '@/components/portal/bundles/PortalBundleInvestSetup'
import { PortalInvestFlowDom } from '@/components/portal/invest/PortalInvestFlowDom'
import { fetchActiveBundleInvestLock } from '@/lib/portal/bundleClient'
import {
  loadBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import {
  buildBundleInvestTechnicalDetails,
  detectPartialBundleSuccess,
} from '@/lib/portal/bundleInvestTerminalization'
import { shouldShowReconciliationForActiveLock } from '@/components/portal/transaction/mappers/bundleSteps'
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
import { buildBundleTargetAllocationRows } from '@/lib/portal/bundleTargetAllocationRows'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'

const PILOT_ENTRY_ASSETS = ['USDC', 'EURC'] as const

type Props = {
  bundle: PortalCryptoBundle
  /** Quitter le flux (retour marchés / invest), comme swap onBack. */
  onExit: () => void
}

/** Invest bundle — page dédiée, allocation théorique + exécution Web3 (aligné PortalSwapFlow, R4.5-F5-A). */
export function PortalBundleInvestFlow({ bundle, onExit }: Props) {
  const [flowScene, setFlowScene] = useState<PortalBundleFlowScene>('setup')
  const [fundingAsset, setFundingAsset] = useState<string>(bundle.entryAssetDefault ?? 'USDC')
  const [amount, setAmount] = useState('')
  const [setupError, setSetupError] = useState<string | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)
  const [resumeSession, setResumeSession] = useState<BundleInvestSession | null>(null)
  const [swapMockMode, setSwapMockMode] = useState(false)

  const [lockTerminal, setLockTerminal] = useState<{
    variant: PortalBundleInvestResultVariant
    resultAmount: number
    technicalDetails: TransactionTechnicalDetailsRow[]
  } | null>(null)

  const targetAllocationRows = useMemo(
    () => buildBundleTargetAllocationRows(bundle),
    [bundle],
  )

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
  }, [refreshLockState])

  const requestExit = useCallback(() => {
    if (flowScene === 'processing') {
      const ok = window.confirm(
        'Un investissement est en cours. Fermer maintenant peut laisser une opération incomplète. Continuer ?',
      )
      if (!ok) return
    }
    onExit()
  }, [flowScene, onExit])

  const reviewContext = useMemo(() => {
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) return null
    return {
      bundleTitle: bundle.title,
      fundingAsset,
      amount: parsedAmount,
      targetAllocationRows,
    }
  }, [bundle.title, fundingAsset, parsedAmount, targetAllocationRows])

  const handleContinueToReview = () => {
    if (!portfolioReady || flowScene === 'blocked') return
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setSetupError('Montant invalide.')
      return
    }
    setSetupError(null)
    setFlowScene('review')
  }

  const onResultClose = () => {
    reset()
    onExit()
  }

  const setupDisabled =
    !portfolioReady ||
    flowScene === 'blocked' ||
    !Number.isFinite(parsedAmount) ||
    parsedAmount <= 0

  if (flowScene === 'result' && lockTerminal) {
    return (
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
    )
  }

  if (isTransactionalExecution && reviewContext) {
    return (
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
        onProcessingClose={requestExit}
        onResultClose={onResultClose}
      />
    )
  }

  return (
    <PortalInvestFlowDom
      scene="form"
      form={
        <>
          {flowScene === 'setup' ? (
            <PortalBundleInvestSetup
              bundleTitle={bundle.title}
              entryOptions={entryOptions}
              fundingAsset={fundingAsset}
              amount={amount}
              targetAllocationRows={targetAllocationRows}
              portfolioReady={portfolioReady}
              setupError={setupError}
              setupDisabled={setupDisabled}
              onFundingAssetChange={setFundingAsset}
              onAmountChange={setAmount}
              onContinue={handleContinueToReview}
              onClose={requestExit}
            />
          ) : null}

          {flowScene === 'blocked' ? (
            <div className="inv-pane">
              <p className="inv-alert">{blockedMessage}</p>
              <button type="button" className="btn btn--secondary" onClick={requestExit}>
                Fermer
              </button>
            </div>
          ) : null}
        </>
      }
    />
  )
}

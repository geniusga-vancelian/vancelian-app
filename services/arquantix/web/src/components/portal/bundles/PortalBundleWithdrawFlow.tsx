'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  PortalBundleWithdrawExecutionController,
  type PortalBundleWithdrawExecutionScene,
} from '@/components/portal/bundles/PortalBundleWithdrawExecutionController'
import { PortalBundleWithdrawSetup } from '@/components/portal/bundles/PortalBundleWithdrawSetup'
import { PortalInvestFlowDom } from '@/components/portal/invest/PortalInvestFlowDom'
import { fetchActiveBundleWithdrawLock } from '@/lib/portal/bundleClient'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'
import {
  loadBundleWithdrawSession,
  type BundleWithdrawSession,
} from '@/lib/portal/bundleWithdrawSession'
import {
  estimateMaxWithdrawAmount,
  splitBundleHoldings,
} from '@/lib/portal/bundleWithdrawFormat'
import { formatCryptoMoney } from '@/lib/portal/cryptoWalletFormat'
import type { PortalBundleFlowScene } from '@/lib/portal/bundleFlowTypes'
import type { PortalBundlePosition } from '@/lib/portal/cryptoWalletTypes'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'

type Props = {
  portfolioId: string
  portfolioName: string
  positions: PortalBundlePosition[] | undefined
  currency: string
  onExit: () => void
  onCompleted?: () => void
}

/** Retrait bundle — page dédiée, destination USDC (sans allocation cible). */
export function PortalBundleWithdrawFlow({
  portfolioId,
  portfolioName,
  positions,
  currency,
  onExit,
  onCompleted,
}: Props) {
  const [flowScene, setFlowScene] = useState<PortalBundleFlowScene>('setup')
  const [fullWithdraw, setFullWithdraw] = useState(false)
  const [amount, setAmount] = useState('')
  const [setupError, setSetupError] = useState<string | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)
  const [resumeSession, setResumeSession] = useState<BundleWithdrawSession | null>(null)
  const [swapMockMode, setSwapMockMode] = useState(false)

  const holdings = useMemo(() => splitBundleHoldings(positions, currency), [currency, positions])
  const entryAsset = holdings.cashLeg?.asset ?? 'USDC'
  const maxAmount = useMemo(() => estimateMaxWithdrawAmount(positions), [positions])

  const parsedAmount = useMemo(() => {
    if (fullWithdraw) return maxAmount
    const n = Number(amount)
    return Number.isFinite(n) ? n : 0
  }, [amount, fullWithdraw, maxAmount])

  const cashCoversWithdraw =
    parsedAmount > 0 && parsedAmount <= holdings.cashLegQuantity + 0.0001

  const amountLabel = useMemo(() => {
    if (fullWithdraw) return formatCryptoMoney(maxAmount, currency)
    return formatBundleUsdcAmount(parsedAmount)
  }, [currency, fullWithdraw, maxAmount, parsedAmount])

  const isTransactionalExecution =
    flowScene === 'review' || flowScene === 'processing' || flowScene === 'result'

  const reviewContext = useMemo(
    () => ({
      portfolioName,
      entryAsset,
      currency,
      amountLabel,
      fullWithdraw,
      maxAmount,
      cashCoversWithdraw,
    }),
    [amountLabel, cashCoversWithdraw, currency, entryAsset, fullWithdraw, maxAmount, portfolioName],
  )

  const refreshLockState = useCallback(async () => {
    const active = await fetchActiveBundleWithdrawLock(portfolioId)
    if (active.status === 'active' && active.lock) {
      const stored = loadBundleWithdrawSession(portfolioId)
      if (stored && stored.batchId === active.lock.batch_id) {
        setResumeSession(stored)
        setBlockedMessage(null)
        return
      }
      setBlockedMessage(
        'Un retrait est déjà en cours sur ce portefeuille. Terminez-le ou attendez la finalisation.',
      )
      setFlowScene('blocked')
      return
    }
    setBlockedMessage(null)
    const stored = loadBundleWithdrawSession(portfolioId)
    if (stored) setResumeSession(stored)
  }, [portfolioId])

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
      if (!cancelled) setSetupError('Impossible de vérifier un retrait en cours.')
    })
    return () => {
      cancelled = true
    }
  }, [refreshLockState])

  const requestExit = useCallback(() => {
    if (flowScene === 'processing') {
      const ok = window.confirm(
        'Un retrait est en cours. Fermer maintenant peut laisser un batch incomplet. Continuer ?',
      )
      if (!ok) return
    }
    onExit()
  }, [flowScene, onExit])

  const handleContinueToReview = () => {
    if (flowScene === 'blocked') return
    if (maxAmount <= 0) {
      setSetupError('Aucune valeur disponible à retirer.')
      return
    }
    if (!fullWithdraw) {
      const parsed = Number(amount)
      if (!Number.isFinite(parsed) || parsed <= 0) {
        setSetupError('Montant invalide.')
        return
      }
      if (parsed > maxAmount + 0.0001) {
        setSetupError('Montant supérieur à la valeur disponible.')
        return
      }
    }
    setSetupError(null)
    setFlowScene('review')
  }

  const setupDisabled = flowScene === 'blocked' || maxAmount <= 0

  const resumeHint = resumeSession
    ? `Retrait en cours (batch ${resumeSession.batchId.slice(0, 8)}…). Vous pouvez reprendre la signature.`
    : null

  if (isTransactionalExecution) {
    return (
      <PortalBundleWithdrawExecutionController
        flowScene={flowScene as PortalBundleWithdrawExecutionScene}
        onFlowSceneChange={setFlowScene}
        onBlocked={(message) => {
          setBlockedMessage(message)
          setFlowScene('blocked')
        }}
        portfolioId={portfolioId}
        portfolioName={portfolioName}
        entryAsset={entryAsset}
        parsedAmount={parsedAmount}
        fullWithdraw={fullWithdraw}
        reviewContext={reviewContext}
        swapMockMode={swapMockMode}
        resumeSession={resumeSession}
        onProcessingClose={requestExit}
        onResultClose={() => {
          onCompleted?.()
          onExit()
        }}
        onCompleted={onCompleted}
      />
    )
  }

  return (
    <PortalInvestFlowDom
      scene="form"
      form={
        <>
          {flowScene === 'setup' ? (
            <PortalBundleWithdrawSetup
              portfolioName={portfolioName}
              entryAsset={entryAsset}
              currency={currency}
              holdings={holdings}
              maxAmount={maxAmount}
              fullWithdraw={fullWithdraw}
              amount={amount}
              setupError={setupError}
              setupDisabled={setupDisabled}
              resumeHint={resumeHint}
              onFullWithdrawChange={setFullWithdraw}
              onAmountChange={setAmount}
              onApplyMax={() => setAmount(String(maxAmount))}
              onResume={
                resumeSession
                  ? () => {
                      setFlowScene('processing')
                    }
                  : undefined
              }
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

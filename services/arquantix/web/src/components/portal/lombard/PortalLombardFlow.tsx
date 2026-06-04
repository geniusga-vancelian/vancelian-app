'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'

import { PortalLombardBorrowForm } from '@/components/portal/lombard/PortalLombardBorrowForm'
import { PortalLombardBorrowReviewStep } from '@/components/portal/lombard/PortalLombardBorrowReviewStep'
import {
  PortalLombardExecutionController,
  type PortalLombardExecutionRequest,
} from '@/components/portal/lombard/PortalLombardExecutionController'
import { PortalLombardBorrowIntro } from '@/components/portal/lombard/PortalLombardBorrowIntro'
import { PortalLombardBorrowProcessing } from '@/components/portal/lombard/PortalLombardBorrowProcessing'
import { PortalLombardBorrowTerminalFailure } from '@/components/portal/lombard/PortalLombardBorrowTerminalFailure'
import { PortalLombardBorrowSuccess } from '@/components/portal/lombard/PortalLombardBorrowSuccess'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalInvestFlowPanel } from '@/components/portal/invest/PortalInvestFlowDom'
import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageSidebar } from '@/components/portal/PortalPageSidebar'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import {
  fetchPortalLombardBorrowCapacity,
  fetchPortalLombardMarkets,
  fetchPortalLombardQuote,
} from '@/lib/portal/lombard/lombardClient'
import { parsePortalBorrowUrlIntent } from '@/lib/portal/lombard/lombardBorrowUrlIntent'
import { buildLombardBorrowRecap, type LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import {
  formatLombardBorrowAmountForApi,
  markBorrowIntroSeen,
  normalizeLombardBorrowAmountForApi,
  readBorrowIntroSeen,
} from '@/lib/portal/lombard/lombardBorrowUi'
import { resolvePortalCollateralBalanceHuman } from '@/lib/portal/lombard/lombardWalletCollateral'
import type {
  LombardBorrowCapacity,
  LombardExecutionPhase,
  LombardMarketSummary,
  LombardQuoteResult,
} from '@/lib/portal/lombard/lombardTypes'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import { portalCryptoWalletAssetRoute, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { bumpLombardPositionsRevision } from '@/lib/portal/lombard/lombardPositionsRefresh'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { isLombardOpeningPhase } from '@/components/portal/transaction/mappers/lombardSteps'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type FlowStep = 'intro' | 'form' | 'review' | 'processing' | 'success'

const OPENING_SUBTEXT_ROTATE_MS = 5_000

const PRIVY_SIGNING_SESSION_HINT =
  'Pour signer le dépôt de garantie, activez votre wallet Vancelian (code e-mail) depuis Mon wallet crypto, puis relancez l’emprunt.'

const DEFAULT_TARGET_LTV_PERCENT = 28
const CAPACITY_DEBOUNCE_MS = 280
const QUOTE_DEBOUNCE_MS = 350

function resolveInitialStep(prefilled: boolean): FlowStep {
  if (prefilled) return 'form'
  return readBorrowIntroSeen() ? 'form' : 'intro'
}

export function PortalLombardFlow() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlIntent = useMemo(
    () => parsePortalBorrowUrlIntent(searchParams),
    [searchParams],
  )
  const prefilled = urlIntent.mode === 'prefilled'
  const { chain, deFiEnabled, executionAddress, isExternalWallet, walletReady, walletScope } =
    usePortalExecutionScope()
  const [step, setStep] = useState<FlowStep>(() => resolveInitialStep(prefilled))
  const showPageSidebar = step !== 'intro'
  const [markets, setMarkets] = useState<LombardMarketSummary[]>([])
  const [lombardMockMode, setLombardMockMode] = useState(false)
  const [marketsLoading, setMarketsLoading] = useState(true)
  const [marketsError, setMarketsError] = useState<string | null>(null)

  const [selectedCollateral, setSelectedCollateral] = useState<string | null>(() =>
    prefilled ? urlIntent.collateral : null,
  )
  const [borrowAmount, setBorrowAmount] = useState('')
  const [targetLtvPercent, setTargetLtvPercent] = useState(DEFAULT_TARGET_LTV_PERCENT)
  const [capacity, setCapacity] = useState<LombardBorrowCapacity | null>(null)
  const [capacityLoading, setCapacityLoading] = useState(false)
  const [capacityRefreshing, setCapacityRefreshing] = useState(false)
  const [capacityError, setCapacityError] = useState<string | null>(null)
  const [quote, setQuote] = useState<LombardQuoteResult | null>(null)
  const [quoteLoading, setQuoteLoading] = useState(false)
  const [quoteRefreshing, setQuoteRefreshing] = useState(false)
  const [quoteError, setQuoteError] = useState<string | null>(null)
  const capacityRequestRef = useRef(0)
  const quoteRequestRef = useRef(0)
  const capacitySnapshotRef = useRef<LombardBorrowCapacity | null>(null)
  const quoteSnapshotRef = useRef<LombardQuoteResult | null>(null)
  capacitySnapshotRef.current = capacity
  quoteSnapshotRef.current = quote

  const [borrowRecap, setBorrowRecap] = useState<LombardBorrowRecap | null>(null)
  const [executionRequest, setExecutionRequest] = useState<PortalLombardExecutionRequest | null>(
    null,
  )
  const openLoanSucceededRef = useRef(false)
  const [executionRunId, setExecutionRunId] = useState(0)
  const [executing, setExecuting] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<LombardExecutionPhase>('idle')
  const [lastProgressPhase, setLastProgressPhase] = useState<LombardExecutionPhase>('preparing')
  const [terminalFailure, setTerminalFailure] = useState(false)
  const [openingSubtextTick, setOpeningSubtextTick] = useState(0)

  const { data: walletData } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:crypto-wallet',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: 'Impossible de charger les soldes crypto.',
    scopeAware: true,
  })

  const positions = useMemo(() => {
    if (!walletData) return []
    return filterCryptoPositionsSummaryByPortalScope(walletData.positions, chain, walletScope).positions
  }, [chain, walletData, walletScope])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setMarketsLoading(true)
      setMarketsError(null)
      try {
        const payload = await fetchPortalLombardMarkets()
        if (cancelled) return
        setMarkets(payload.markets)
        setLombardMockMode(Boolean(payload.mock))
        setSelectedCollateral((current) => current ?? payload.markets[0]?.collateral ?? null)
      } catch (error) {
        if (cancelled) return
        setMarketsError(error instanceof Error ? error.message : 'Impossible de charger le produit.')
      } finally {
        if (!cancelled) setMarketsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const selectedMarket = useMemo(
    () => markets.find((m) => m.collateral === selectedCollateral) ?? null,
    [markets, selectedCollateral],
  )

  const portalCollateralBalanceHuman = useMemo(() => {
    if (!selectedCollateral) return null
    const row = positions.find(
      (p) => p.asset.toLowerCase() === selectedCollateral.toLowerCase(),
    )
    if (!row) return null
    const balance = resolvePortalCollateralBalanceHuman(row)
    if (!(balance > 0)) return null
    const digits = balance < 1 ? 8 : 6
    return formatLombardBorrowAmountForApi(balance) || null
  }, [positions, selectedCollateral])

  const requiresPrivySigning = !lombardMockMode && !isExternalWallet

  useEffect(() => {
    setCapacity(null)
    setCapacityError(null)
    setQuote(null)
    setQuoteError(null)
  }, [selectedCollateral])

  useEffect(() => {
    if (step !== 'form' || !selectedCollateral || !executionAddress || targetLtvPercent <= 0) return

    const requestId = ++capacityRequestRef.current
    const snapshot = capacitySnapshotRef.current
    const hasExistingCapacity =
      snapshot != null && snapshot.collateral === selectedCollateral
    if (hasExistingCapacity) {
      setCapacityRefreshing(true)
    } else {
      setCapacityLoading(true)
    }

    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const next = await fetchPortalLombardBorrowCapacity({
            collateral: selectedCollateral,
            walletAddress: executionAddress,
            targetLtvPercent,
            portalWalletCollateralBalance: portalCollateralBalanceHuman,
          })
          if (requestId !== capacityRequestRef.current) return
          setCapacity(next)
          setCapacityError(null)
        } catch (error) {
          if (requestId !== capacityRequestRef.current) return
          if (!hasExistingCapacity) setCapacity(null)
          setCapacityError(
            error instanceof Error ? error.message : 'Impossible de calculer la capacité d’emprunt.',
          )
        } finally {
          if (requestId !== capacityRequestRef.current) return
          setCapacityLoading(false)
          setCapacityRefreshing(false)
        }
      })()
    }, hasExistingCapacity ? CAPACITY_DEBOUNCE_MS : 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [executionAddress, portalCollateralBalanceHuman, selectedCollateral, step, targetLtvPercent])

  useEffect(() => {
    if (step !== 'form') return
    if (!selectedCollateral || !executionAddress || targetLtvPercent <= 0) return

    const normalizedBorrowAmount = normalizeLombardBorrowAmountForApi(borrowAmount)
    if (!normalizedBorrowAmount) {
      setQuote(null)
      setQuoteError(null)
      setQuoteLoading(false)
      setQuoteRefreshing(false)
      return
    }

    const requestId = ++quoteRequestRef.current
    const quoteSnapshot = quoteSnapshotRef.current
    const hasExistingQuote =
      quoteSnapshot != null && quoteSnapshot.collateral === selectedCollateral
    if (hasExistingQuote) {
      setQuoteRefreshing(true)
    } else {
      setQuoteLoading(true)
    }

    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const next = await fetchPortalLombardQuote({
            collateral: selectedCollateral,
            borrowAmount: borrowAmount.trim(),
            walletAddress: executionAddress,
            targetLtvPercent,
            portalWalletCollateralBalance: portalCollateralBalanceHuman,
          })
          if (requestId !== quoteRequestRef.current) return
          setQuote(next)
          setQuoteError(null)
        } catch (error) {
          if (requestId !== quoteRequestRef.current) return
          if (!hasExistingQuote) setQuote(null)
          setQuoteError(error instanceof Error ? error.message : 'Impossible de calculer le devis.')
        } finally {
          if (requestId !== quoteRequestRef.current) return
          setQuoteLoading(false)
          setQuoteRefreshing(false)
        }
      })()
    }, QUOTE_DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timer)
    }
  }, [borrowAmount, executionAddress, portalCollateralBalanceHuman, selectedCollateral, step, targetLtvPercent])

  useEffect(() => {
    if (step !== 'processing' || terminalFailure) return
    if (!isLombardOpeningPhase(executionPhase)) return
    const timer = window.setInterval(() => {
      setOpeningSubtextTick((tick) => tick + 1)
    }, OPENING_SUBTEXT_ROTATE_MS)
    return () => window.clearInterval(timer)
  }, [executionPhase, step, terminalFailure])

  const handleExecutionPhaseChange = useCallback((phase: LombardExecutionPhase) => {
    setExecutionPhase(phase)
    if (phase !== 'failed' && phase !== 'idle') {
      setLastProgressPhase(phase)
    }
  }, [])

  const goToBorrowReview = useCallback(() => {
    if (executing || !quote) return
    setBorrowRecap(buildLombardBorrowRecap(quote))
    setStep('review')
  }, [executing, quote])

  const startOpenLoan = useCallback(() => {
    if (executing || !selectedCollateral || !quote || !executionAddress) return

    openLoanSucceededRef.current = false
    if (!borrowRecap) {
      setBorrowRecap(buildLombardBorrowRecap(quote))
    }
    setExecutionRequest({
      collateral: selectedCollateral,
      borrowAmount: borrowAmount.trim(),
      walletAddress: executionAddress,
      targetLtvPercent,
    })
    setStep('processing')
    setTerminalFailure(false)
    setOpeningSubtextTick(0)
    setExecutionPhase('preparing')
    setExecutionRunId((id) => id + 1)
  }, [
    borrowAmount,
    executing,
    executionAddress,
    quote,
    selectedCollateral,
    borrowRecap,
    targetLtvPercent,
  ])

  const handleOpeningSubtextTick = useCallback(() => {
    setOpeningSubtextTick((tick) => tick + 1)
  }, [])

  const retryOpenLoan = useCallback(() => {
    if (executing || !executionRequest) return
    openLoanSucceededRef.current = false
    setTerminalFailure(false)
    setOpeningSubtextTick(0)
    setExecutionPhase('preparing')
    setExecutionRunId((id) => id + 1)
  }, [executing, executionRequest])

  const handleIntroContinue = useCallback(() => {
    markBorrowIntroSeen()
    setStep('form')
  }, [])

  const handleBorrowSuccessExit = useCallback(() => {
    bumpLombardPositionsRevision()
    invalidatePortalCache()
    router.replace(portalCryptoWalletAssetRoute('usdc'))
  }, [router])

  const handleOpenLoanSuccess = useCallback(() => {
    openLoanSucceededRef.current = true
    setTerminalFailure(false)
    setStep('success')
  }, [])

  const handleOpenLoanTerminalFailure = useCallback(() => {
    if (openLoanSucceededRef.current) {
      handleOpenLoanSuccess()
      return
    }
    setTerminalFailure(true)
    setExecutionPhase('failed')
  }, [handleOpenLoanSuccess])

  useEffect(() => {
    if (step !== 'processing' || !openLoanSucceededRef.current) return
    if (terminalFailure || executionPhase === 'confirmed') {
      handleOpenLoanSuccess()
    }
  }, [executionPhase, handleOpenLoanSuccess, step, terminalFailure])

  const main = !deFiEnabled ? (
    <p className="font-ui text-[15px] text-v-muted">
      L&apos;avance de liquidité est disponible sur Base uniquement. Changez de réseau pour continuer.
    </p>
  ) : (
    <>
      {marketsLoading && step !== 'intro' ? (
        <div className="flex items-center gap-2 text-v-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="font-ui text-[14px]">Chargement des marchés…</span>
        </div>
      ) : null}

      {marketsError ? <p className="font-ui text-[14px] text-v-error">{marketsError}</p> : null}

      {step === 'intro' ? (
        <PortalLombardBorrowIntro
          onContinue={handleIntroContinue}
          onClose={() => router.push(PORTAL_ROUTES.cryptoWallet)}
        />
      ) : null}

      {step === 'form' && selectedCollateral && markets.length > 0 ? (
        <>
          <PortalLombardBorrowForm
            markets={markets}
            positions={positions}
            selectedCollateral={selectedCollateral}
            onSelectCollateral={setSelectedCollateral}
            capacity={capacity}
            capacityLoading={capacityLoading}
            capacityRefreshing={capacityRefreshing}
            capacityError={capacityError}
            quote={quote}
            quoteLoading={quoteLoading}
            quoteRefreshing={quoteRefreshing}
            quoteError={quoteError}
            maxUserLtvPercent={selectedMarket?.maxUserLtvPercent}
            targetLtvPercent={targetLtvPercent}
            borrowAmount={borrowAmount}
            onTargetLtvChange={setTargetLtvPercent}
            onBorrowAmountChange={setBorrowAmount}
            onBack={() => {
              if (prefilled) {
                router.back()
                return
              }
              if (!readBorrowIntroSeen()) {
                setStep('intro')
                return
              }
              router.push(PORTAL_ROUTES.cryptoWallet)
            }}
            onContinue={goToBorrowReview}
            onClose={() => router.push(PORTAL_ROUTES.cryptoWallet)}
            continueDisabled={
              !walletReady || executing || !quote || quoteLoading || quoteRefreshing
            }
          />

          {requiresPrivySigning ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 font-ui text-[13px] text-amber-950">
              <p className="m-0">{PRIVY_SIGNING_SESSION_HINT}</p>
              <PortalNavLink
                href={PORTAL_ROUTES.walletCreate}
                className="mt-2 inline-block font-medium text-amber-950 underline"
              >
                Activer mon wallet crypto
              </PortalNavLink>
            </div>
          ) : null}

        </>
      ) : null}

      {step === 'review' && borrowRecap ? (
        <PortalInvestFlowPanel>
          <PortalLombardBorrowReviewStep
            recap={borrowRecap}
            onBack={() => setStep('form')}
            onConfirm={startOpenLoan}
            confirmDisabled={executing || !walletReady}
          />
        </PortalInvestFlowPanel>
      ) : null}

      {step === 'processing' && borrowRecap && executionRequest ? (
        <div className="flex flex-col gap-5">
          <PortalLombardExecutionController
            request={executionRequest}
            runId={executionRunId}
            borrowSucceededRef={openLoanSucceededRef}
            requiresPrivySigning={requiresPrivySigning}
            onPhaseChange={handleExecutionPhaseChange}
            onInvisibleRetry={handleOpeningSubtextTick}
            onSuccess={handleOpenLoanSuccess}
            onTerminalFailure={handleOpenLoanTerminalFailure}
            onExecutingChange={setExecuting}
          />
          {!terminalFailure ? (
            <PortalLombardBorrowProcessing
              recap={borrowRecap}
              executionPhase={executionPhase === 'failed' ? lastProgressPhase : executionPhase}
              openingSubtextTick={openingSubtextTick}
              onClose={() => router.push(PORTAL_ROUTES.cryptoWallet)}
            />
          ) : (
            <PortalLombardBorrowTerminalFailure
              retryDisabled={executing}
              onRetry={retryOpenLoan}
              onClose={() => router.push(PORTAL_ROUTES.cryptoWallet)}
            />
          )}
        </div>
      ) : null}

      {step === 'success' && borrowRecap ? (
        <PortalLombardBorrowSuccess
          recap={borrowRecap}
          onViewLoans={handleBorrowSuccessExit}
          onClose={handleBorrowSuccessExit}
        />
      ) : null}
    </>
  )

  return (
    <PortalPageContainer>
      <PortalExecutionScopeGate requirement="defi">
        <PortalPortfolioLayout
          main={main}
          side={showPageSidebar ? <PortalPageSidebar showFeatured /> : undefined}
        />
      </PortalExecutionScopeGate>
    </PortalPageContainer>
  )
}

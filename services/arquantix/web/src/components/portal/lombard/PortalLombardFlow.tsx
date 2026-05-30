'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { usePrivy } from '@privy-io/react-auth'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalLombardBorrowForm } from '@/components/portal/lombard/PortalLombardBorrowForm'
import { PortalLombardBorrowIntro } from '@/components/portal/lombard/PortalLombardBorrowIntro'
import { PortalLombardBorrowProcessing } from '@/components/portal/lombard/PortalLombardBorrowProcessing'
import { PortalLombardBorrowSuccess } from '@/components/portal/lombard/PortalLombardBorrowSuccess'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
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
  markBorrowIntroSeen,
  normalizeLombardBorrowAmountForApi,
  readBorrowIntroSeen,
} from '@/lib/portal/lombard/lombardBorrowUi'
import type {
  LombardBorrowCapacity,
  LombardExecutionPhase,
  LombardMarketSummary,
  LombardQuoteResult,
} from '@/lib/portal/lombard/lombardTypes'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  resolveLombardExecutionFailure,
  usePortalLombardExecution,
} from '@/lib/portal/usePortalLombardExecution'
import type { LombardExecutionFailureView } from '@/lib/portal/lombard/lombardExecutionError'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type FlowStep = 'intro' | 'form' | 'processing' | 'success'

const PRIVY_SIGNING_SESSION_HINT =
  'Pour signer le dépôt de garantie, activez votre wallet Vancelian (code e-mail) depuis Mon wallet crypto, puis relancez l’emprunt.'

const DEFAULT_TARGET_LTV_PERCENT = 28
const CAPACITY_DEBOUNCE_MS = 280
const QUOTE_DEBOUNCE_MS = 350

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `lombard-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

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
  const { ready: privySdkReady, authenticated: privyAuthenticated } = usePrivy()
  const { privyReady: privyProviderReady } = usePortalAuthPrivy()
  const { executeOpenLoan } = usePortalLombardExecution()
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
  const [executing, setExecuting] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<LombardExecutionPhase>('idle')
  const [lastProgressPhase, setLastProgressPhase] = useState<LombardExecutionPhase>('preparing')
  const [executionFailure, setExecutionFailure] = useState<LombardExecutionFailureView | null>(null)
  const idempotencyKeyRef = useRef<string | null>(null)

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

  const requiresPrivySigning = !lombardMockMode && !isExternalWallet
  const privySigningReady =
    !requiresPrivySigning || (privyProviderReady && privySdkReady && privyAuthenticated)
  const privySigningHint =
    requiresPrivySigning && !privySigningReady ? PRIVY_SIGNING_SESSION_HINT : null

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
  }, [executionAddress, selectedCollateral, step, targetLtvPercent])

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
  }, [borrowAmount, executionAddress, selectedCollateral, step, targetLtvPercent])

  const runOpenLoan = useCallback(async () => {
    if (executing || !selectedCollateral || !quote || !executionAddress) return

    setBorrowRecap(buildLombardBorrowRecap(quote))
    setStep('processing')
    setExecuting(true)
    setExecutionFailure(null)
    setExecutionPhase('preparing')
    idempotencyKeyRef.current = createIdempotencyKey()

    try {
      await executeOpenLoan({
        collateral: selectedCollateral,
        borrowAmount: borrowAmount.trim(),
        walletAddress: executionAddress,
        targetLtvPercent,
        idempotencyKey: idempotencyKeyRef.current,
        onPhaseChange: (phase) => {
          setExecutionPhase(phase)
          if (phase !== 'failed' && phase !== 'idle') {
            setLastProgressPhase(phase)
          }
        },
      })
      setStep('success')
    } catch (error) {
      setExecutionPhase('failed')
      setExecutionFailure(resolveLombardExecutionFailure(error))
    } finally {
      setExecuting(false)
    }
  }, [
    borrowAmount,
    executeOpenLoan,
    executing,
    executionAddress,
    quote,
    selectedCollateral,
    targetLtvPercent,
  ])

  const handleIntroContinue = useCallback(() => {
    markBorrowIntroSeen()
    setStep('form')
  }, [])

  const handleViewLoans = useCallback(() => {
    router.push(PORTAL_ROUTES.creditLine)
  }, [router])

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
            onContinue={() => void runOpenLoan()}
            onClose={() => router.push(PORTAL_ROUTES.cryptoWallet)}
            continueDisabled={!walletReady || !privySigningReady || executing}
          />

          {privySigningHint ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 font-ui text-[13px] text-amber-950">
              <p className="m-0">{privySigningHint}</p>
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

      {step === 'processing' && borrowRecap ? (
        <div className="flex flex-col gap-5">
          <PortalLombardBorrowProcessing
            recap={borrowRecap}
            executionPhase={executionPhase === 'failed' ? lastProgressPhase : executionPhase}
            onClose={() => router.push(PORTAL_ROUTES.cryptoWallet)}
          />

          {executionFailure ? (
            <div className="rounded-xl border border-v-error/30 bg-v-error/5 p-4">
              <p className="m-0 font-ui text-[14px] font-medium text-v-error">{executionFailure.headline}</p>
              {executionFailure.stepLabel ? (
                <p className="m-0 mt-2 font-ui text-[13px] text-v-fg">
                  Étape : {executionFailure.stepLabel}
                </p>
              ) : null}
              {executionFailure.txHash ? (
                <p className="m-0 mt-1 break-all font-mono text-[12px] text-v-muted">
                  Transaction : {executionFailure.txHash}
                </p>
              ) : null}
              <div className="brw-foot mt-4">
                <button
                  type="button"
                  className="btn btn--ghost btn--lg"
                  onClick={() => {
                    setExecutionFailure(null)
                    setExecutionPhase('idle')
                    setStep('form')
                  }}
                >
                  Retour
                </button>
                <button
                  type="button"
                  className="btn btn--primary btn--lg brw-foot__cta"
                  disabled={executing || !privySigningReady}
                  onClick={() => void runOpenLoan()}
                >
                  Réessayer
                </button>
              </div>
            </div>
          ) : null}

        </div>
      ) : null}

      {step === 'success' && borrowRecap ? (
        <PortalLombardBorrowSuccess
          recap={borrowRecap}
          onViewLoans={handleViewLoans}
          onClose={handleViewLoans}
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

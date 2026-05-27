'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { usePrivy } from '@privy-io/react-auth'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalLombardLtvSlider } from '@/components/portal/lombard/PortalLombardLtvSlider'
import { PortalLombardQaDebugPanel } from '@/components/portal/lombard/PortalLombardQaDebugPanel'
import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { Button } from '@/components/ui/button'
import type { PortalCryptoPosition, PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import {
  fetchPortalLombardBorrowCapacity,
  fetchPortalLombardMarkets,
  fetchPortalLombardQuote,
} from '@/lib/portal/lombard/lombardClient'
import { parsePortalBorrowUrlIntent } from '@/lib/portal/lombard/lombardBorrowUrlIntent'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  formatLombardApyPercent,
} from '@/lib/portal/lombard/lombardFormat'
import type {
  LombardBorrowCapacity,
  LombardExecutionPhase,
  LombardMarketSummary,
  LombardQuoteResult,
} from '@/lib/portal/lombard/lombardTypes'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

const PRIVY_SIGNING_SESSION_HINT =
  'Pour signer le dépôt de garantie, activez votre wallet Vancelian (code e-mail) depuis Mon wallet crypto, puis relancez l’emprunt.'
import {
  lombardExecutionPhaseLabel,
  resolveLombardExecutionFailure,
  usePortalLombardExecution,
} from '@/lib/portal/usePortalLombardExecution'
import type { LombardExecutionFailureView } from '@/lib/portal/lombard/lombardExecutionError'
import { usePortalLombardQaDebug } from '@/lib/portal/lombard/usePortalLombardQaDebug'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type FlowStep = 'product' | 'asset' | 'amount' | 'summary'

const LIQUIDATION_DISCLAIMER =
  'If the value of your guarantee falls too much, part of your crypto may be sold automatically to repay the loan.'

const DEFAULT_TARGET_LTV_PERCENT = 35

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `lombard-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function findGuaranteeBalance(positions: PortalCryptoPosition[], collateral: string): string {
  const row = positions.find((p) => p.asset.toLowerCase() === collateral.toLowerCase())
  if (!row) return '0'
  const value = row.availableBalance ?? row.balance
  return String(value)
}

export function PortalLombardFlow() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlIntent = useMemo(
    () => parsePortalBorrowUrlIntent(searchParams),
    [searchParams],
  )
  const { chain, deFiEnabled, executionAddress, isExternalWallet, walletReady, walletScope } =
    usePortalExecutionScope()
  const { ready: privySdkReady, authenticated: privyAuthenticated } = usePrivy()
  const { privyReady: privyProviderReady } = usePortalAuthPrivy()
  const { executeOpenLoan } = usePortalLombardExecution()
  const { visible: qaDebugVisible, betaCaps, maxUserLtvPercent } = usePortalLombardQaDebug(executionAddress)

  const [step, setStep] = useState<FlowStep>(() =>
    urlIntent.mode === 'prefilled' ? 'amount' : 'product',
  )
  const [markets, setMarkets] = useState<LombardMarketSummary[]>([])
  const [lombardMockMode, setLombardMockMode] = useState(false)
  const [marketsLoading, setMarketsLoading] = useState(true)
  const [marketsError, setMarketsError] = useState<string | null>(null)

  const [selectedCollateral, setSelectedCollateral] = useState<string | null>(() =>
    urlIntent.mode === 'prefilled' ? urlIntent.collateral : null,
  )
  const [borrowAmount, setBorrowAmount] = useState('')
  const [targetLtvPercent, setTargetLtvPercent] = useState(DEFAULT_TARGET_LTV_PERCENT)
  const [capacity, setCapacity] = useState<LombardBorrowCapacity | null>(null)
  const [capacityLoading, setCapacityLoading] = useState(false)
  const [capacityError, setCapacityError] = useState<string | null>(null)
  const [quote, setQuote] = useState<LombardQuoteResult | null>(null)
  const [quoteLoading, setQuoteLoading] = useState(false)
  const [quoteError, setQuoteError] = useState<string | null>(null)

  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<LombardExecutionPhase>('idle')
  const [executionFailure, setExecutionFailure] = useState<LombardExecutionFailureView | null>(null)
  const [success, setSuccess] = useState(false)
  const [ledgerGroupId, setLedgerGroupId] = useState<string | null>(null)
  const idempotencyKeyRef = useRef<string | null>(null)

  const { data: walletData } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:crypto-wallet',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: 'Unable to load wallet balances.',
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
      } catch (error) {
        if (cancelled) return
        setMarketsError(error instanceof Error ? error.message : 'Unable to load product.')
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

  const qaDebugPanel =
    qaDebugVisible && (step === 'amount' || step === 'summary') ? (
      <PortalLombardQaDebugPanel
        marketId={selectedMarket?.marketId ?? null}
        walletAddress={executionAddress ?? null}
        quote={quote}
        maxUserLtvPercent={maxUserLtvPercent}
        betaCaps={betaCaps}
        executionPhase={executionPhase}
        ledgerGroupId={ledgerGroupId}
        executionFailure={executionFailure}
        mockMode={lombardMockMode}
      />
    ) : null

  const loadCapacity = useCallback(async () => {
    if (!selectedCollateral || !executionAddress || targetLtvPercent <= 0) return
    setCapacityLoading(true)
    setCapacityError(null)
    try {
      const next = await fetchPortalLombardBorrowCapacity({
        collateral: selectedCollateral,
        walletAddress: executionAddress,
        targetLtvPercent,
      })
      setCapacity(next)
    } catch (error) {
      setCapacity(null)
      setCapacityError(error instanceof Error ? error.message : 'Unable to load borrowing capacity.')
    } finally {
      setCapacityLoading(false)
    }
  }, [executionAddress, selectedCollateral, targetLtvPercent])

  useEffect(() => {
    if (step !== 'amount' || !selectedCollateral || !executionAddress) return
    void loadCapacity()
  }, [executionAddress, loadCapacity, selectedCollateral, step])

  const handleTargetLtvChange = useCallback((ltvPercent: number) => {
    setTargetLtvPercent(ltvPercent)
  }, [])

  const handleBorrowAmountChange = useCallback((amount: string) => {
    setBorrowAmount(amount)
  }, [])

  const loadQuote = useCallback(async () => {
    if (!selectedCollateral || !borrowAmount.trim() || !executionAddress || targetLtvPercent <= 0) return
    setQuoteLoading(true)
    setQuoteError(null)
    try {
      const next = await fetchPortalLombardQuote({
        collateral: selectedCollateral,
        borrowAmount: borrowAmount.trim(),
        walletAddress: executionAddress,
        targetLtvPercent,
      })
      setQuote(next)
    } catch (error) {
      setQuote(null)
      setQuoteError(error instanceof Error ? error.message : 'Unable to compute quote.')
    } finally {
      setQuoteLoading(false)
    }
  }, [borrowAmount, executionAddress, selectedCollateral, targetLtvPercent])

  useEffect(() => {
    if (step !== 'amount' && step !== 'summary') return
    if (!borrowAmount.trim() || targetLtvPercent <= 0) {
      setQuote(null)
      return
    }
    const timer = window.setTimeout(() => {
      void loadQuote()
    }, 350)
    return () => window.clearTimeout(timer)
  }, [borrowAmount, loadQuote, step, targetLtvPercent])

  const handleConfirm = useCallback(async () => {
    if (!selectedCollateral || !borrowAmount.trim() || !disclaimerAccepted || !executionAddress) return
    setExecuting(true)
    setExecutionFailure(null)
    setSuccess(false)
    idempotencyKeyRef.current = createIdempotencyKey()
    setLedgerGroupId(idempotencyKeyRef.current)
    try {
      await executeOpenLoan({
        collateral: selectedCollateral,
        borrowAmount: borrowAmount.trim(),
        walletAddress: executionAddress,
        targetLtvPercent,
        idempotencyKey: idempotencyKeyRef.current,
        onPhaseChange: setExecutionPhase,
      })
      setSuccess(true)
    } catch (error) {
      setExecutionPhase('failed')
      setExecutionFailure(resolveLombardExecutionFailure(error))
    } finally {
      setExecuting(false)
    }
  }, [borrowAmount, disclaimerAccepted, executeOpenLoan, executionAddress, selectedCollateral, targetLtvPercent])

  if (!deFiEnabled) {
    return (
      <PortalPageContainer>
        <p className="font-ui text-[15px] text-v-muted">
          Liquidity advance is available on Base only. Switch network to continue.
        </p>
      </PortalPageContainer>
    )
  }

  return (
    <PortalPageContainer>
      <PortalExecutionScopeGate requirement="defi">
        {step === 'product' ? (
          <section className="flex flex-col gap-6">
            <PortalPageIntro
              eyebrow="Liquidity"
              title="Avance de liquidité"
              description="Obtenez des USDC sans vendre vos cbBTC ou cbETH. Vous gardez votre exposition au Bitcoin ou à Ethereum."
            />
            <div className="rounded-2xl border border-v-border bg-v-surface p-5">
              <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg">
                Déposez vos cbBTC ou cbETH en garantie et recevez des USDC directement dans votre wallet.
              </p>
              <p className="m-0 mt-3 font-ui text-[13px] text-v-muted">{VANCELIAN_LOMBARD_V1.poweredByLabel}</p>
            </div>
            <Button type="button" className="w-full" onClick={() => setStep('asset')}>
              Borrow USDC
            </Button>
          </section>
        ) : null}

        {step === 'asset' ? (
          <section className="flex flex-col gap-5">
            <PortalPageIntro
              eyebrow="Guarantee"
              title="Choose your guarantee"
              description="Choose the asset you want to use as guarantee."
            />
            {marketsLoading ? (
              <div className="flex items-center gap-2 text-v-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="font-ui text-[14px]">Loading markets…</span>
              </div>
            ) : null}
            {marketsError ? <p className="font-ui text-[14px] text-v-error">{marketsError}</p> : null}
            <div className="flex flex-col gap-3">
              {markets.map((market) => (
                <button
                  key={market.marketId}
                  type="button"
                  onClick={() => {
                    setSelectedCollateral(market.collateral)
                    setStep('amount')
                  }}
                  className="flex items-center justify-between rounded-2xl border border-v-border bg-v-surface p-4 text-left transition hover:border-v-accent"
                >
                  <div className="flex items-center gap-3">
                    <PortalCryptoAvatar ticker={market.collateral} size="md" />
                    <div>
                      <p className="m-0 font-ui text-[16px] font-semibold text-v-fg">{market.collateral}</p>
                      <p className="m-0 font-ui text-[13px] text-v-muted">{market.collateralName} exposure</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="m-0 font-ui text-[12px] text-v-muted">Balance</p>
                    <p className="m-0 font-ui text-[14px] font-medium text-v-fg">
                      {findGuaranteeBalance(positions, market.collateral)} {market.collateral}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </section>
        ) : null}

        {step === 'amount' && selectedCollateral && !selectedMarket && marketsLoading ? (
          <div className="flex items-center gap-2 text-v-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="font-ui text-[14px]">Loading market…</span>
          </div>
        ) : null}

        {step === 'amount' && selectedMarket ? (
          <section className="flex flex-col gap-5">
            <PortalPageIntro
              eyebrow="Emprunt"
              title="Choisissez votre niveau d'emprunt"
              description="Fixez d'abord votre LTV (niveau de risque), puis le montant USDC souhaité. Seule la garantie nécessaire sera déposée sur Morpho."
            />
            {capacityLoading ? (
              <div className="flex items-center gap-2 text-v-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="font-ui text-[14px]">Calcul de votre capacité…</span>
              </div>
            ) : null}
            {capacityError ? <p className="font-ui text-[14px] text-v-error">{capacityError}</p> : null}
            {capacity ? (
              <PortalLombardLtvSlider
                capacity={capacity}
                targetLtvPercent={targetLtvPercent}
                quote={quote}
                borrowAmount={borrowAmount}
                disabled={quoteLoading || !walletReady}
                onTargetLtvChange={handleTargetLtvChange}
                onBorrowAmountChange={handleBorrowAmountChange}
              />
            ) : null}
            {quoteLoading ? (
              <div className="flex items-center gap-2 text-v-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="font-ui text-[13px]">Mise à jour du devis…</span>
              </div>
            ) : null}
            {quoteError ? <p className="font-ui text-[14px] text-v-error">{quoteError}</p> : null}
            {qaDebugPanel}
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  if (urlIntent.mode === 'prefilled') {
                    router.back()
                    return
                  }
                  setStep('asset')
                }}
              >
                Retour
              </Button>
              <Button
                type="button"
                className="flex-1"
                disabled={!quote || quoteLoading || !walletReady || targetLtvPercent <= 0}
                onClick={() => setStep('summary')}
              >
                Continuer
              </Button>
            </div>
          </section>
        ) : null}

        {step === 'summary' && quote && selectedMarket ? (
          <section className="flex flex-col gap-5">
            <PortalPageIntro eyebrow="Review" title="Summary" description="Review before confirming." />
            <div className="rounded-2xl border border-v-border bg-v-surface p-5 font-ui text-[15px]">
              <dl className="m-0 grid gap-3">
                <div>
                  <dt className="text-v-muted">You will use</dt>
                  <dd className="m-0 font-medium text-v-fg">
                    {quote.guaranteeAmount} {quote.collateral} as guarantee
                  </dd>
                </div>
                <div>
                  <dt className="text-v-muted">You will receive</dt>
                  <dd className="m-0 font-medium text-v-fg">{quote.borrowAmount} USDC in your Vancelian wallet</dd>
                </div>
                <div>
                  <dt className="text-v-muted">LTV cible</dt>
                  <dd className="m-0 font-medium text-v-fg">{quote.targetLtvPercent} %</dd>
                </div>
                <div>
                  <dt className="text-v-muted">Current safety level</dt>
                  <dd className="m-0 font-medium text-v-fg">
                    {quote.safetyLabel} — {quote.projectedLtvPercent}% of your maximum borrowing capacity
                  </dd>
                </div>
                <div>
                  <dt className="text-v-muted">Estimated yearly interest</dt>
                  <dd className="m-0 font-medium text-v-fg">{formatLombardApyPercent(quote.borrowApyPercent)}</dd>
                </div>
                <div>
                  <dt className="text-v-muted">Liquidation warning</dt>
                  <dd className="m-0 text-v-fg">{LIQUIDATION_DISCLAIMER}</dd>
                </div>
              </dl>
              <p className="m-0 mt-4 text-[13px] text-v-muted">{VANCELIAN_LOMBARD_V1.poweredByLabel}</p>
            </div>
            {lombardMockMode ? (
              <p className="m-0 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 font-ui text-[13px] text-amber-900">
                Local mock mode — no wallet signature required.
              </p>
            ) : null}
            <label className="flex items-start gap-3 font-ui text-[14px] text-v-fg">
              <input
                type="checkbox"
                checked={disclaimerAccepted}
                onChange={(e) => setDisclaimerAccepted(e.target.checked)}
                className="mt-1"
              />
              <span>I understand that my crypto can be liquidated if its value falls too much.</span>
            </label>
            {executing || success ? (
              <div className="rounded-xl border border-v-border bg-v-surface p-4">
                <p className="m-0 font-ui text-[14px] font-medium text-v-fg">
                  {lombardExecutionPhaseLabel(executionPhase)}
                </p>
                {executionPhase === 'authorizing' ? (
                  <p className="m-0 mt-1 font-ui text-[13px] text-v-muted">Step 1 — Authorising your guarantee</p>
                ) : null}
                {executionPhase === 'locking' || executionPhase === 'sending' ? (
                  <p className="m-0 mt-1 font-ui text-[13px] text-v-muted">Step 2 — Locking your guarantee</p>
                ) : null}
                {executionPhase === 'sending' || executionPhase === 'confirmed' ? (
                  <p className="m-0 mt-1 font-ui text-[13px] text-v-muted">Step 3 — Sending USDC to your wallet</p>
                ) : null}
              </div>
            ) : null}
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
            {executionFailure ? (
              <div className="rounded-xl border border-v-error/30 bg-v-error/5 p-4">
                <p className="m-0 font-ui text-[14px] font-medium text-v-error">{executionFailure.headline}</p>
                {executionFailure.stepLabel ? (
                  <p className="m-0 mt-2 font-ui text-[13px] text-v-fg">
                    Step: {executionFailure.stepLabel}
                  </p>
                ) : null}
                {executionFailure.txHash ? (
                  <p className="m-0 mt-1 break-all font-mono text-[12px] text-v-muted">
                    Transaction: {executionFailure.txHash}
                  </p>
                ) : null}
              </div>
            ) : null}
            {qaDebugPanel}
            {success ? (
              <Button type="button" className="w-full" onClick={() => router.push(PORTAL_ROUTES.cryptoWallet)}>
                View wallet
              </Button>
            ) : (
              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setStep('amount')}>
                  Back
                </Button>
                <Button
                  type="button"
                  className="flex-1"
                  disabled={!disclaimerAccepted || executing || !privySigningReady}
                  onClick={() => void handleConfirm()}
                >
                  {executing ? 'Processing…' : 'Confirm and receive USDC'}
                </Button>
              </div>
            )}
          </section>
        ) : null}
      </PortalExecutionScopeGate>
    </PortalPageContainer>
  )
}

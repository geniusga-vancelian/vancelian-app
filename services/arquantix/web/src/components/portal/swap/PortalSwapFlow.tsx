'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalSwapUnsupportedNotice } from '@/components/portal/swap/PortalSwapUnsupportedNotice'
import { PortalSwapAmountStep } from '@/components/portal/swap/PortalSwapAmountStep'
import { PortalSwapReviewStep } from '@/components/portal/swap/PortalSwapReviewStep'
import { PortalSwapFromStep, type SwapFromOption } from '@/components/portal/swap/PortalSwapFromStep'
import { PortalSwapToStep } from '@/components/portal/swap/PortalSwapToStep'
import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import { PortalSwapLayout } from '@/components/portal/swap/PortalSwapLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import {
  buildSwapProcessingSteps,
  resolveSwapFailureCopy,
  SWAP_PROCESSING_COMPLETED_INDEX,
  swapProcessingStepperIndex,
  type SwapProcessingContext,
} from '@/components/portal/transaction/mappers/swapSteps'
import { SWAP_FLOW_UI, SWAP_RESULT_IMPOSSIBLE_ACTIONS } from '@/components/portal/transaction/mappers/swapUiCopy'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import { PORTAL_ROUTES, portalCryptoWalletAssetRoute } from '@/lib/portal/portalRouting'
import { buildPortalScopeCacheSuffix } from '@/lib/portal/portalScopeQuery'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { resolveSpendableSwapBalance } from '@/lib/portal/swapAmountValidation'
import {
  buildSwapFromOptions,
  buildSwapToOptions,
  formatSwapCryptoAmount,
  type SwapToOption,
} from '@/lib/portal/swapFlowFormat'
import {
  executeSwap,
  fetchSupportedSwapAssets,
  type SwapQuotePayload,
  type SwapSupportedAssetsPayload,
} from '@/lib/portal/swapClient'
import type { PortalSwapFlowStep, SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  parsePortalSwapUrlIntent,
  pickSwapCatalogListsForChain,
} from '@/lib/portal/swapFlowTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

export function PortalSwapFlow() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { chain, chainLabel, walletScope, walletScopeId, swapChainKey } = usePortalExecutionScope()

  const [step, setStep] = useState<PortalSwapFlowStep>('to')
  const [catalog, setCatalog] = useState<SwapSupportedAssetsPayload | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState<string | null>(null)

  const [toAsset, setToAsset] = useState('')
  const [toChain, setToChain] = useState('')
  const [fromAsset, setFromAsset] = useState('')
  const [fromChain, setFromChain] = useState('')
  const [sourceBalance, setSourceBalance] = useState(0)
  const [amount, setAmount] = useState('')
  const [quote, setQuote] = useState<SwapQuotePayload | null>(null)

  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [failureCopy, setFailureCopy] = useState(() => resolveSwapFailureCopy(null))
  const executionStartedRef = useRef(false)

  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    Boolean(catalog?.mock_mode),
    setExecutionPhase,
    fromAsset,
  )

  const { data: walletData, loading: walletLoading } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:crypto-wallet',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: 'Impossible de charger les positions crypto.',
    scopeAware: true,
  })

  const positions = useMemo(() => {
    if (!walletData) return []
    return filterCryptoPositionsSummaryByPortalScope(walletData.positions, chain, walletScope).positions
  }, [chain, walletData, walletScope])

  const supportedChainKeys = useMemo(
    () => catalog?.chains.map((row) => row.key) ?? [],
    [catalog],
  )

  const activeSwapChain = useMemo(() => {
    if (!swapChainKey) return null
    return supportedChainKeys.includes(swapChainKey) ? swapChainKey : null
  }, [supportedChainKeys, swapChainKey])

  const { source: sourceAssets, destination: destinationAssets } = useMemo(
    () => (catalog ? pickSwapCatalogListsForChain(catalog, activeSwapChain) : { source: [], destination: [] }),
    [activeSwapChain, catalog],
  )

  const urlIntent = useMemo(
    () => parsePortalSwapUrlIntent(searchParams, activeSwapChain),
    [activeSwapChain, searchParams],
  )

  const swapProcessingContext = useMemo((): SwapProcessingContext | null => {
    if (!quote) return null
    const parsed = Number(amount.replace(',', '.'))
    const payLabel = formatSwapCryptoAmount(parsed > 0 ? parsed : quote.amount_in)
    const receiveLabel = `${formatSwapCryptoAmount(quote.estimated_receive)} ${toAsset}`
    return {
      fromAsset,
      toAsset,
      payLabel,
      receiveLabel,
    }
  }, [amount, fromAsset, quote, toAsset])

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true)
    setCatalogError(null)
    try {
      const data = await fetchSupportedSwapAssets()
      setCatalog(data)
    } catch (e) {
      setCatalogError(e instanceof Error ? e.message : 'Catalogue indisponible')
    } finally {
      setCatalogLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  const resetExecution = useCallback(() => {
    setExecutionPhase('idle')
    setFailureCopy(resolveSwapFailureCopy(null))
    executionStartedRef.current = false
  }, [])

  useEffect(() => {
    setAmount('')
    setQuote(null)
    resetExecution()
  }, [resetExecution, swapChainKey])

  useEffect(() => {
    if (!activeSwapChain) return

    if (urlIntent.mode === 'buy') {
      setToAsset(urlIntent.toAsset)
      setToChain(urlIntent.toChain)
      setFromAsset('')
      setFromChain('')
      setSourceBalance(0)
      setStep('from')
      return
    }

    if (urlIntent.mode === 'sell') {
      const position = positions.find(
        (p) => p.asset.toUpperCase() === urlIntent.fromAsset,
      )
      setFromAsset(urlIntent.fromAsset)
      setFromChain(urlIntent.fromChain)
      setSourceBalance(
        position
          ? resolveSpendableSwapBalance(position)
          : 0,
      )
      setToAsset('')
      setToChain('')
      setStep('to')
      return
    }

    setStep('to')
    setToAsset('')
    setToChain('')
    setFromAsset('')
    setFromChain('')
    setSourceBalance(0)
  }, [activeSwapChain, positions, urlIntent])

  const onSelectTo = useCallback(
    (asset: string) => {
      if (!activeSwapChain) return
      setToAsset(asset)
      setToChain(activeSwapChain)
      setStep('from')
    },
    [activeSwapChain],
  )

  const onSelectFrom = useCallback(
    (option: SwapFromOption) => {
      if (!activeSwapChain) return
      setFromAsset(option.asset)
      setFromChain(activeSwapChain)
      setSourceBalance(
        option.position ? resolveSpendableSwapBalance(option.position) : option.balance,
      )
      setStep('amount')
    },
    [activeSwapChain],
  )

  const swapFromOptions = useMemo(() => {
    if (!toAsset || !toChain) return []
    return buildSwapFromOptions(sourceAssets, positions, toAsset, toChain)
  }, [positions, sourceAssets, toAsset, toChain])

  const swapToOptions = useMemo(() => {
    if (!fromAsset || !activeSwapChain) return []
    return buildSwapToOptions(destinationAssets, fromAsset, activeSwapChain)
  }, [activeSwapChain, destinationAssets, fromAsset])

  const onChangeFromOnAmount = useCallback(
    (option: SwapFromOption) => {
      if (!activeSwapChain) return
      setFromAsset(option.asset)
      setFromChain(activeSwapChain)
      setSourceBalance(
        option.position ? resolveSpendableSwapBalance(option.position) : option.balance,
      )
    },
    [activeSwapChain],
  )

  const onChangeToOnAmount = useCallback(
    (option: SwapToOption) => {
      if (!activeSwapChain) return
      setToAsset(option.asset)
      setToChain(activeSwapChain)
    },
    [activeSwapChain],
  )

  const onAmountContinue = useCallback((nextAmount: string, nextQuote: SwapQuotePayload) => {
    setAmount(nextAmount)
    setQuote(nextQuote)
    resetExecution()
    setStep('review')
  }, [resetExecution])

  const runExecution = useCallback(async () => {
    if (!quote) return
    setExecutionPhase('preparing')

    try {
      const exec = await executeSwap(quote.swap_id)
      if (!exec.transaction) {
        throw new Error('Payload transaction manquant')
      }

      await signAndSubmit(exec)

      setExecutionPhase('bridging')
      const status = await pollUntilTerminal(quote.swap_id)

      if (status.status !== 'CONFIRMED') {
        throw new Error('Swap non confirmé')
      }

      setExecutionPhase('completed')
      setStep('result')
    } catch (e) {
      setExecutionPhase('failed')
      setFailureCopy(resolveSwapFailureCopy(e))
      setStep('result')
    }
  }, [pollUntilTerminal, quote, signAndSubmit])

  useEffect(() => {
    if (step !== 'processing' || !quote || executionStartedRef.current) return
    executionStartedRef.current = true
    void runExecution()
  }, [quote, runExecution, step])

  const onReviewConfirm = useCallback(() => {
    if (!quote) return
    resetExecution()
    executionStartedRef.current = false
    setStep('processing')
  }, [quote, resetExecution])

  const onProcessingClose = useCallback(() => {
    resetExecution()
    router.push(PORTAL_ROUTES.cryptoWallet)
  }, [resetExecution, router])

  const onResultSuccess = useCallback(() => {
    resetExecution()
    const ticker = toAsset.trim().toUpperCase()
    const scopeSuffix = buildPortalScopeCacheSuffix(chain, walletScopeId)
    invalidatePortalCache(`portal:crypto-wallet:${scopeSuffix}`)
    if (ticker) invalidatePortalCache(`portal:crypto-wallet:${ticker}:${scopeSuffix}`)
    router.push(
      ticker ? portalCryptoWalletAssetRoute(ticker) : PORTAL_ROUTES.cryptoWallet,
    )
  }, [chain, resetExecution, router, toAsset, walletScopeId])

  const onResultRetry = useCallback(() => {
    resetExecution()
    setStep('review')
  }, [resetExecution])

  const onResultClose = useCallback(() => {
    resetExecution()
    router.push(PORTAL_ROUTES.cryptoWallet)
  }, [resetExecution, router])

  if (catalogLoading || (walletLoading && !walletData)) {
    return (
      <Container className="flex min-h-[40vh] items-center justify-center py-10">
        <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" />
      </Container>
    )
  }

  if (catalogError || !catalog) {
    return (
      <PortalPageContainer>
        <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-16 text-center">
          <p className="m-0 font-ui text-[15px] text-v-error">
            {catalogError ?? 'Catalogue swap indisponible'}
          </p>
          <Button type="button" onClick={() => void loadCatalog()}>
            Réessayer
          </Button>
        </div>
      </PortalPageContainer>
    )
  }

  return (
    <PortalExecutionScopeGate requirement="wallet">
      {!activeSwapChain ? (
        <PortalSwapUnsupportedNotice
          chainLabel={chainLabel}
          supportedChainKeys={supportedChainKeys}
          onBack={() => router.push(PORTAL_ROUTES.cryptoWallet)}
        />
      ) : step === 'to' ? (
        <PortalSwapToStep
          description={
            urlIntent.mode === 'sell'
              ? `Choose what to receive for your ${urlIntent.fromAsset} on ${chainLabel}.`
              : undefined
          }
          assets={
            fromAsset && fromChain
              ? destinationAssets.filter(
                  (a) => a.symbol.toUpperCase() !== fromAsset.toUpperCase(),
                )
              : destinationAssets
          }
          onSelect={onSelectTo}
          onBack={() => {
            if (urlIntent.mode === 'sell') {
              router.push(portalCryptoWalletAssetRoute(urlIntent.fromAsset))
              return
            }
            router.push(PORTAL_ROUTES.cryptoWallet)
          }}
        />
      ) : step === 'from' && toAsset && toChain ? (
        <PortalSwapFromStep
          toAsset={toAsset}
          toChain={toChain}
          catalog={sourceAssets}
          positions={positions}
          onSelect={onSelectFrom}
          stepEyebrow={urlIntent.mode === 'buy' ? 'Step 1' : 'Step 2'}
          description={
            urlIntent.mode === 'buy'
              ? `Pay with USDC, EURC or ETH on ${chainLabel} to buy ${toAsset}.`
              : undefined
          }
          onBack={() => {
            if (urlIntent.mode === 'buy') {
              router.push(portalCryptoWalletAssetRoute(toAsset))
              return
            }
            setToAsset('')
            setToChain('')
            setStep('to')
          }}
        />
      ) : step === 'amount' && fromAsset && toAsset && fromChain && toChain ? (
        <PortalSwapLayout
          backHref={
            urlIntent.mode === 'sell'
              ? portalCryptoWalletAssetRoute(urlIntent.fromAsset)
              : PORTAL_ROUTES.cryptoWallet
          }
          backLabel={urlIntent.mode === 'sell' ? 'Back to asset' : 'Back to wallet'}
          onBackClick={() =>
            setStep(urlIntent.mode === 'sell' ? 'to' : urlIntent.mode === 'buy' ? 'from' : 'from')
          }
        >
          <PortalSwapAmountStep
            fromAsset={fromAsset}
            toAsset={toAsset}
            fromChain={fromChain}
            toChain={toChain}
            sourceBalance={sourceBalance}
            fromOptions={swapFromOptions}
            toOptions={swapToOptions}
            onChangeFrom={onChangeFromOnAmount}
            onChangeTo={onChangeToOnAmount}
            onContinue={onAmountContinue}
            onBack={() =>
              setStep(urlIntent.mode === 'sell' ? 'to' : urlIntent.mode === 'buy' ? 'from' : 'from')
            }
          />
        </PortalSwapLayout>
      ) : step === 'review' && quote ? (
        <PortalSwapLayout backLabel="Back to amount" onBackClick={() => setStep('amount')}>
          <PortalSwapReviewStep
            fromAsset={fromAsset}
            toAsset={toAsset}
            amount={amount}
            quote={quote}
            onConfirm={onReviewConfirm}
            onBack={() => setStep('amount')}
          />
        </PortalSwapLayout>
      ) : step === 'processing' && quote && swapProcessingContext ? (
        <PortalSwapLayout backLabel={SWAP_FLOW_UI.backToWallet} onBackClick={onProcessingClose}>
          <TransactionProcessingPage
            title={SWAP_FLOW_UI.processingTitle}
            lead={
              <>
                {SWAP_FLOW_UI.processingLead(
                  swapProcessingContext.payLabel,
                  fromAsset,
                  toAsset,
                )}
              </>
            }
            steps={buildSwapProcessingSteps(swapProcessingContext)}
            progressIndex={swapProcessingStepperIndex(executionPhase)}
            completedProgressIndex={SWAP_PROCESSING_COMPLETED_INDEX}
            onClose={onProcessingClose}
          />
        </PortalSwapLayout>
      ) : step === 'result' && quote && swapProcessingContext ? (
        <PortalSwapLayout backLabel={SWAP_FLOW_UI.backToWallet} onBackClick={onResultClose}>
          {executionPhase === 'completed' ? (
            <TransactionResultPage
              variant="success"
              layout="compact"
              title={SWAP_FLOW_UI.successTitle}
              lead={
                <>
                  +<span className="v-tnum">{swapProcessingContext.receiveLabel}</span>
                </>
              }
              subtitle={
                <>
                  {SWAP_FLOW_UI.successSubtitle(swapProcessingContext.payLabel, fromAsset)}
                </>
              }
              steps={[]}
              summary={[]}
              primaryAction={{
                label: SWAP_FLOW_UI.viewWalletCta(toAsset),
                onClick: onResultSuccess,
              }}
              onClose={onResultClose}
            />
          ) : (
            <TransactionResultPage
              variant="impossible"
              copy={failureCopy}
              onRetry={onResultRetry}
              onClose={onResultClose}
              closeLabel={SWAP_RESULT_IMPOSSIBLE_ACTIONS.close}
              retryLabel={SWAP_RESULT_IMPOSSIBLE_ACTIONS.retry}
            />
          )}
        </PortalSwapLayout>
      ) : null}
    </PortalExecutionScopeGate>
  )
}

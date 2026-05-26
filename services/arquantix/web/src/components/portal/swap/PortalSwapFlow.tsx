'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalSwapUnsupportedNotice } from '@/components/portal/swap/PortalSwapUnsupportedNotice'
import { PortalSwapAmountStep } from '@/components/portal/swap/PortalSwapAmountStep'
import { PortalSwapConfirmStep } from '@/components/portal/swap/PortalSwapConfirmStep'
import { PortalSwapFromStep, type SwapFromOption } from '@/components/portal/swap/PortalSwapFromStep'
import { PortalSwapProcessingOverlay } from '@/components/portal/swap/PortalSwapProcessingOverlay'
import { PortalSwapToStep } from '@/components/portal/swap/PortalSwapToStep'
import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import { PORTAL_ROUTES, portalCryptoWalletAssetRoute } from '@/lib/portal/portalRouting'
import { buildPortalScopeCacheSuffix } from '@/lib/portal/portalScopeQuery'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import {
  executeSwap,
  fetchSupportedSwapAssets,
  type SwapQuotePayload,
  type SwapSupportedAssetsPayload,
} from '@/lib/portal/swapClient'
import type { PortalSwapFlowStep, SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  isSwapV1Token,
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
  const [preselectApplied, setPreselectApplied] = useState(false)

  const [toAsset, setToAsset] = useState('')
  const [toChain, setToChain] = useState('')
  const [fromAsset, setFromAsset] = useState('')
  const [fromChain, setFromChain] = useState('')
  const [sourceBalance, setSourceBalance] = useState(0)
  const [amount, setAmount] = useState('')
  const [quote, setQuote] = useState<SwapQuotePayload | null>(null)

  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [executionError, setExecutionError] = useState<string | null>(null)
  const [executing, setExecuting] = useState(false)

  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    Boolean(catalog?.mock_mode),
    setExecutionPhase,
    fromAsset,
  )

  const showResultModal =
    executionPhase === 'completed' || (executionPhase === 'failed' && Boolean(executionError))

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
    setExecutionError(null)
    setExecuting(false)
  }, [])

  useEffect(() => {
    setStep('to')
    setToAsset('')
    setToChain('')
    setFromAsset('')
    setFromChain('')
    setSourceBalance(0)
    setAmount('')
    setQuote(null)
    setPreselectApplied(false)
    resetExecution()
  }, [resetExecution, swapChainKey])

  useEffect(() => {
    if (!catalog || preselectApplied || !searchParams || !activeSwapChain) return
    const toParam = searchParams.get('to')?.trim().toUpperCase()
    if (!toParam || !isSwapV1Token(toParam)) return
    const dest = destinationAssets.find((a) => a.symbol.toUpperCase() === toParam)
    if (!dest) return
    setToAsset(dest.symbol)
    setToChain(activeSwapChain)
    setStep('from')
    setPreselectApplied(true)
  }, [activeSwapChain, catalog, destinationAssets, preselectApplied, searchParams])

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
      setSourceBalance(option.balance)
      setStep('amount')
    },
    [activeSwapChain],
  )

  const onAmountContinue = useCallback((nextAmount: string, nextQuote: SwapQuotePayload) => {
    setAmount(nextAmount)
    setQuote(nextQuote)
    setStep('confirm')
  }, [])

  const onConfirm = useCallback(async () => {
    if (!quote) return
    setExecuting(true)
    setExecutionError(null)
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
    } catch (e) {
      setExecutionPhase('failed')
      setExecutionError(e instanceof Error ? e.message : 'Exécution impossible')
    } finally {
      setExecuting(false)
    }
  }, [pollUntilTerminal, quote, signAndSubmit])

  const onProcessingClose = useCallback(() => {
    resetExecution()
  }, [resetExecution])

  const onProcessingDone = useCallback(() => {
    resetExecution()
    const ticker = toAsset.trim().toUpperCase()
    const scopeSuffix = buildPortalScopeCacheSuffix(chain, walletScopeId)
    invalidatePortalCache(`portal:crypto-wallet:${scopeSuffix}`)
    if (ticker) invalidatePortalCache(`portal:crypto-wallet:${ticker}:${scopeSuffix}`)
    router.push(
      ticker ? portalCryptoWalletAssetRoute(ticker) : PORTAL_ROUTES.cryptoWallet,
    )
  }, [chain, resetExecution, router, toAsset, walletScopeId])

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
          assets={destinationAssets}
          onSelect={onSelectTo}
          onBack={() => router.push(PORTAL_ROUTES.cryptoWallet)}
        />
      ) : step === 'from' && toAsset && toChain ? (
        <PortalSwapFromStep
          toAsset={toAsset}
          toChain={toChain}
          catalog={sourceAssets}
          positions={positions}
          onSelect={onSelectFrom}
          onBack={() => setStep('to')}
        />
      ) : step === 'amount' && fromAsset && toAsset && fromChain && toChain ? (
        <PortalSwapAmountStep
          fromAsset={fromAsset}
          toAsset={toAsset}
          fromChain={fromChain}
          toChain={toChain}
          sourceBalance={sourceBalance}
          onContinue={onAmountContinue}
          onBack={() => setStep('from')}
        />
      ) : step === 'confirm' && quote ? (
        <>
          <PortalSwapConfirmStep
            fromAsset={fromAsset}
            toAsset={toAsset}
            amount={amount}
            quote={quote}
            executionPhase={executionPhase}
            executing={executing}
            error={showResultModal ? null : executionError}
            onConfirm={() => void onConfirm()}
            onBack={() => setStep('amount')}
          />
          <PortalSwapProcessingOverlay
            open={showResultModal}
            fromAsset={fromAsset}
            toAsset={toAsset}
            quote={quote}
            phase={executionPhase}
            error={executionError}
            onClose={onProcessingClose}
            onDone={onProcessingDone}
          />
        </>
      ) : null}
    </PortalExecutionScopeGate>
  )
}

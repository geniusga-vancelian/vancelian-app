'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'

import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalSwapUnsupportedNotice } from '@/components/portal/swap/PortalSwapUnsupportedNotice'
import { PortalSwapAmountStep } from '@/components/portal/swap/PortalSwapAmountStep'
import { PortalSwapExecutionController } from '@/components/portal/swap/PortalSwapExecutionController'
import { PortalSwapFromStep, type SwapFromOption } from '@/components/portal/swap/PortalSwapFromStep'
import { PortalSwapToStep } from '@/components/portal/swap/PortalSwapToStep'
import { PortalSwapLayout } from '@/components/portal/swap/PortalSwapLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
import type { SwapProcessingContext } from '@/components/portal/transaction/mappers/swapSteps'
import { SWAP_FLOW_UI } from '@/components/portal/transaction/mappers/swapUiCopy'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import { filterCryptoPositionsSummaryByPortalScope } from '@/lib/portal/portalWalletScopeFilter'
import { PORTAL_ROUTES, portalCryptoWalletAssetRoute } from '@/lib/portal/portalRouting'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { resolveSpendableSwapBalance } from '@/lib/portal/swapAmountValidation'
import {
  buildSwapFromOptions,
  buildSwapToOptions,
  formatSwapCryptoAmount,
  pickDefaultSwapFromOption,
  pickDefaultSwapToOption,
  SWAP_DEFAULT_GENERIC_TARGET_ASSET,
  SWAP_DEFAULT_STABLE_ASSET,
  type SwapToOption,
} from '@/lib/portal/swapFlowFormat'
import {
  fetchSupportedSwapAssets,
  type SwapQuotePayload,
  type SwapSupportedAssetsPayload,
} from '@/lib/portal/swapClient'
import type { PortalSwapFlowStep } from '@/lib/portal/swapFlowTypes'
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
  const [priceChangeNotice, setPriceChangeNotice] = useState<string | null>(null)

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

  useEffect(() => {
    setAmount('')
    setQuote(null)
  }, [swapChainKey])

  useEffect(() => {
    if (!activeSwapChain || !catalog) return
    if (step !== 'to' && step !== 'from') return

    const applyAmountStep = (args: {
      from: string
      fromChain: string
      to: string
      toChain: string
      balance: number
    }) => {
      setFromAsset(args.from)
      setFromChain(args.fromChain)
      setToAsset(args.to)
      setToChain(args.toChain)
      setSourceBalance(args.balance)
      setAmount('')
      setQuote(null)
      setStep('amount')
    }

    if (urlIntent.mode === 'buy') {
      const fromOpt = pickDefaultSwapFromOption(
        sourceAssets,
        positions,
        urlIntent.toAsset,
        urlIntent.toChain,
        SWAP_DEFAULT_STABLE_ASSET,
      )
      if (fromOpt) {
        applyAmountStep({
          from: fromOpt.asset,
          fromChain: fromOpt.chain,
          to: urlIntent.toAsset,
          toChain: urlIntent.toChain,
          balance: fromOpt.balance,
        })
      } else {
        setToAsset(urlIntent.toAsset)
        setToChain(urlIntent.toChain)
        setFromAsset('')
        setFromChain('')
        setSourceBalance(0)
        setStep('from')
      }
      return
    }

    if (urlIntent.mode === 'sell') {
      const position = positions.find(
        (p) => p.asset.toUpperCase() === urlIntent.fromAsset,
      )
      const toOpt = pickDefaultSwapToOption(
        destinationAssets,
        urlIntent.fromAsset,
        urlIntent.fromChain,
        SWAP_DEFAULT_STABLE_ASSET,
      )
      if (toOpt) {
        applyAmountStep({
          from: urlIntent.fromAsset,
          fromChain: urlIntent.fromChain,
          to: toOpt.asset,
          toChain: toOpt.chain,
          balance: position ? resolveSpendableSwapBalance(position) : 0,
        })
      } else {
        setFromAsset(urlIntent.fromAsset)
        setFromChain(urlIntent.fromChain)
        setSourceBalance(position ? resolveSpendableSwapBalance(position) : 0)
        setToAsset('')
        setToChain('')
        setStep('to')
      }
      return
    }

    const genericTo =
      pickDefaultSwapToOption(
        destinationAssets,
        SWAP_DEFAULT_STABLE_ASSET,
        activeSwapChain,
        SWAP_DEFAULT_GENERIC_TARGET_ASSET,
      ) ??
      pickDefaultSwapToOption(destinationAssets, SWAP_DEFAULT_STABLE_ASSET, activeSwapChain)
    const genericFrom = genericTo
      ? pickDefaultSwapFromOption(
          sourceAssets,
          positions,
          genericTo.asset,
          activeSwapChain,
          SWAP_DEFAULT_STABLE_ASSET,
        )
      : null

    if (genericFrom && genericTo) {
      applyAmountStep({
        from: genericFrom.asset,
        fromChain: genericFrom.chain,
        to: genericTo.asset,
        toChain: genericTo.chain,
        balance: genericFrom.balance,
      })
      return
    }

    setStep('to')
    setToAsset('')
    setToChain('')
    setFromAsset('')
    setFromChain('')
    setSourceBalance(0)
  }, [
    activeSwapChain,
    catalog,
    destinationAssets,
    positions,
    sourceAssets,
    step,
    urlIntent,
  ])

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

  const fromMinAmount = useMemo(() => {
    const row = sourceAssets.find(
      (asset) => asset.symbol.toUpperCase() === fromAsset.toUpperCase(),
    )
    return row?.min_amount ?? null
  }, [fromAsset, sourceAssets])

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
    setStep('review')
  }, [])

  const isExecutionStep = step === 'review' || step === 'processing' || step === 'result'

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
          onBackClick={() => {
            if (urlIntent.mode === 'sell') {
              router.push(portalCryptoWalletAssetRoute(urlIntent.fromAsset))
              return
            }
            if (urlIntent.mode === 'buy') {
              router.push(portalCryptoWalletAssetRoute(toAsset))
              return
            }
            router.push(PORTAL_ROUTES.cryptoWallet)
          }}
        >
          <PortalSwapAmountStep
            fromAsset={fromAsset}
            toAsset={toAsset}
            fromChain={fromChain}
            toChain={toChain}
            sourceBalance={sourceBalance}
            minAmount={fromMinAmount}
            fromOptions={swapFromOptions}
            toOptions={swapToOptions}
            onChangeFrom={onChangeFromOnAmount}
            onChangeTo={onChangeToOnAmount}
            onContinue={onAmountContinue}
            onBack={() => {
              if (urlIntent.mode === 'sell') {
                router.push(portalCryptoWalletAssetRoute(urlIntent.fromAsset))
                return
              }
              if (urlIntent.mode === 'buy') {
                router.push(portalCryptoWalletAssetRoute(toAsset))
                return
              }
              router.push(PORTAL_ROUTES.cryptoWallet)
            }}
          />
        </PortalSwapLayout>
      ) : isExecutionStep && quote && swapProcessingContext ? (
        <PortalSwapExecutionController
          step={step}
          quote={quote}
          amount={amount}
          fromAsset={fromAsset}
          toAsset={toAsset}
          swapMockMode={Boolean(catalog.mock_mode)}
          swapProcessingContext={swapProcessingContext}
          onStepChange={setStep}
          onResetExecutionState={() => {}}
          onQuoteUpdate={setQuote}
          priceChangeNotice={priceChangeNotice}
          onClearPriceChangeNotice={() => setPriceChangeNotice(null)}
          onPriceChanged={() => setPriceChangeNotice(SWAP_FLOW_UI.priceChangedReviewBanner)}
        />
      ) : null}
    </PortalExecutionScopeGate>
  )
}

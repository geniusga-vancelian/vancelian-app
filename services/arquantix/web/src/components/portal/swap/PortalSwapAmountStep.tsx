'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalExecutionScopeBanner } from '@/components/portal/PortalExecutionScopeBanner'
import { PortalCryptoExchangeDirection } from '@/components/portal/swap/PortalCryptoExchangeDirection'
import { PortalSwapFlowShell } from '@/components/portal/swap/PortalSwapFlowShell'
import { Button } from '@/components/ui/button'
import { isSwapAmountOverPrivyBalance } from '@/lib/portal/swapAmountValidation'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import { requestSwapQuote, type SwapQuotePayload } from '@/lib/portal/swapClient'
import {
  buildSwapSigningWalletQuoteParams,
  formatSwapSigningWalletShort,
} from '@/lib/portal/swapSigningWallet'
import { useExecutionWallet } from '@/lib/wallet/useExecutionWallet'

type Props = {
  fromAsset: string
  toAsset: string
  fromChain: string
  toChain: string
  sourceBalance: number
  onContinue: (amount: string, quote: SwapQuotePayload) => void
  onBack: () => void
}

export function PortalSwapAmountStep({
  fromAsset,
  toAsset,
  fromChain,
  toChain,
  sourceBalance,
  onContinue,
  onBack,
}: Props) {
  const {
    mode,
    selectedExternalWalletId,
    externalWallets,
    privyEmbeddedAddress,
    loading: walletLoading,
  } = useExecutionWallet()

  const [amount, setAmount] = useState('')
  const [quote, setQuote] = useState<SwapQuotePayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedExternal = useMemo(
    () => externalWallets.find((row) => row.id === selectedExternalWalletId) ?? externalWallets[0] ?? null,
    [externalWallets, selectedExternalWalletId],
  )

  const signingWalletAddress = mode === 'external_evm' ? selectedExternal?.address ?? null : privyEmbeddedAddress

  const parsed = Number(amount.replace(',', '.'))
  const usesPrivyBalance = mode === 'privy_embedded'
  const overBalance = usesPrivyBalance && isSwapAmountOverPrivyBalance(parsed, sourceBalance)
  const canContinue = parsed > 0 && !overBalance && quote !== null && !loading && !walletLoading

  const fetchQuote = useCallback(async () => {
    if (parsed <= 0) {
      setQuote(null)
      setError(null)
      return
    }

    if (walletLoading) return

    setLoading(true)
    setError(null)
    try {
      const signing = buildSwapSigningWalletQuoteParams({
        mode,
        privyEmbeddedAddress,
        externalWalletAddress: selectedExternal?.address ?? null,
      })
      const result = await requestSwapQuote({
        from_asset: fromAsset,
        to_asset: toAsset,
        amount: String(parsed),
        from_chain: fromChain,
        to_chain: toChain,
        ...signing,
      })
      setQuote(result)
    } catch (e) {
      setQuote(null)
      setError(e instanceof Error ? e.message : 'Estimation impossible')
    } finally {
      setLoading(false)
    }
  }, [
    fromAsset,
    fromChain,
    mode,
    parsed,
    privyEmbeddedAddress,
    selectedExternal?.address,
    toAsset,
    toChain,
    walletLoading,
  ])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchQuote()
    }, 500)
    return () => window.clearTimeout(timer)
  }, [fetchQuote])

  const chainLabel = SWAP_CHAIN_LABELS[fromChain] ?? fromChain

  return (
    <PortalSwapFlowShell
      title="Swap"
      onBack={onBack}
      centered
      footer={
        <Button
          type="button"
          className="h-[52px] w-full rounded-full font-ui text-[16px] font-semibold"
          disabled={!canContinue}
          onClick={() => quote && onContinue(amount, quote)}
        >
          Continuer
        </Button>
      }
    >
      <div className="flex w-full max-w-md flex-col items-center gap-5 text-center">
        <PortalCryptoExchangeDirection fromAsset={fromAsset} toAsset={toAsset} />
        <h2 className="m-0 max-w-sm font-ui text-[22px] font-bold leading-snug text-v-fg">
          Vous êtes sur le point de convertir
        </h2>

        <PortalExecutionScopeBanner context="swap" className="w-full text-left" />

        <label className="w-full">
          <span className="sr-only">Montant</span>
          <input
            type="text"
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder={`0 ${fromAsset}`}
            className={`w-full border-0 bg-transparent text-center font-ui text-[34px] font-bold tracking-tight outline-none ${
              overBalance ? 'text-red-600' : 'text-v-fg'
            }`}
          />
        </label>

        <div className="min-h-[24px] font-ui text-[14px] font-semibold text-v-fg">
          {loading ? (
            <span className="inline-flex items-center gap-2 text-v-fg-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
              Estimation...
            </span>
          ) : quote ? (
            <span>≈ {formatSwapCryptoAmount(quote.estimated_receive)} {toAsset}</span>
          ) : (
            <span className="text-v-fg-muted">≈ 0 {toAsset}</span>
          )}
        </div>

        {usesPrivyBalance ? (
          <p className="m-0 font-ui text-[13px] text-v-fg-muted">
            {sourceBalance > 0 ? (
              <>
                Solde wallet Vancelian : {formatSwapCryptoAmount(sourceBalance)} {fromAsset}
              </>
            ) : (
              <>Solde {fromAsset} indisponible — sélectionnez un actif source avec un solde positif.</>
            )}
          </p>
        ) : null}

        {overBalance ? (
          <p className="m-0 rounded-v-control bg-red-50 px-3 py-2 font-ui text-[13px] text-v-error">
            {sourceBalance > 0
              ? `Montant supérieur au solde disponible (${formatSwapCryptoAmount(sourceBalance)} ${fromAsset}).`
              : `Solde ${fromAsset} insuffisant pour ce montant.`}
          </p>
        ) : null}

        {mode === 'external_evm' && signingWalletAddress ? (
          <p className="m-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
            Route LI.FI pour{' '}
            <span className="font-medium text-v-fg">{formatSwapSigningWalletShort(signingWalletAddress)}</span>{' '}
            sur {chainLabel}. Vérifiez le solde {fromAsset} et l&apos;ETH gas sur cette adresse MetaMask.
          </p>
        ) : null}

        {error ? (
          <p className="m-0 rounded-v-control bg-red-50 px-3 py-2 font-ui text-[13px] text-v-error">{error}</p>
        ) : null}
      </div>
    </PortalSwapFlowShell>
  )
}

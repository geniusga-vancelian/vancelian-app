'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Copy,
  ExternalLink,
  Loader2,
  Shield,
  Wallet,
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Button } from '@/components/ui/button'
import {
  formatEvmNetworkLabel,
  formatEvmNetworkShort,
  resolveEvmExplorerAddressUrl,
} from '@/lib/portal/evmNetworkLabel'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  fetchPortalPersonCryptoWallets,
  resolvePrimaryPersonCryptoWallet,
  type PortalPersonCryptoWallet,
} from '@/lib/portal/privyWalletClient'

const DEPOSIT_STEPS = [
  {
    title: 'Copiez votre adresse',
    body: 'Utilisez le bouton ci-dessous ou sélectionnez l’adresse pour la copier.',
  },
  {
    title: 'Envoyez depuis un wallet externe',
    body: 'Exchange (Binance, Coinbase…) ou wallet personnel — uniquement sur le réseau indiqué.',
  },
  {
    title: 'Attendez la confirmation',
    body: 'Une fois la transaction confirmée on-chain, le solde apparaît dans votre wallet Vancelian.',
  },
] as const

export function PortalCryptoDepositScreen() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [wallets, setWallets] = useState<PortalPersonCryptoWallet[]>([])
  const [copied, setCopied] = useState(false)

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setError('')
    try {
      const rows = await fetchPortalPersonCryptoWallets()
      setWallets(rows)
      if (rows.length === 0) {
        router.replace(PORTAL_ROUTES.walletCreate)
        return
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger votre adresse de dépôt.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [router])

  useEffect(() => {
    void load()
  }, [load])

  const primaryWallet = useMemo(() => resolvePrimaryPersonCryptoWallet(wallets), [wallets])
  const networkLabel = formatEvmNetworkLabel(primaryWallet?.chain_id)
  const networkShort = formatEvmNetworkShort(primaryWallet?.chain_id)
  const explorerUrl = primaryWallet
    ? resolveEvmExplorerAddressUrl(primaryWallet.address, primaryWallet.chain_id)
    : null

  const copyAddress = useCallback(async (address: string) => {
    try {
      await navigator.clipboard.writeText(address)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2500)
    } catch {
      setError('Copie impossible — sélectionnez l’adresse manuellement.')
    }
  }, [])

  if (loading) {
    return (
      <PortalPageContainer className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" aria-hidden />
        <span className="sr-only">Chargement</span>
      </PortalPageContainer>
    )
  }

  if (!primaryWallet) {
    return (
      <PortalPageContainer className="py-8 sm:py-10">
        <div className="mx-auto w-full max-w-lg text-center">
          <p className="m-0 font-ui text-[15px] text-v-error">
            {error || 'Aucune adresse de dépôt disponible.'}
          </p>
          <Button type="button" className="mt-4" onClick={() => void load()}>
            Réessayer
          </Button>
        </div>
      </PortalPageContainer>
    )
  }

  const otherWallets = wallets.filter((w) => w.id !== primaryWallet.id)

  return (
    <PortalPageContainer className="py-8 sm:py-10">
      <div className="mx-auto w-full max-w-xl">
        <Link
          href={PORTAL_ROUTES.dashboard}
          className="mb-6 inline-flex items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Dashboard
        </Link>

        <div className="mb-6">
          <VEyebrow>Dépôt</VEyebrow>
          <h1 className="m-0 font-ui text-[26px] font-semibold tracking-v-tight text-v-fg sm:text-[28px]">
            Recevoir des cryptos
          </h1>
          <p className="mt-2 mb-0 max-w-prose font-ui text-[15px] leading-relaxed text-v-fg-body">
            Transférez des actifs vers votre wallet embedded Vancelian (non custodial, sécurisé par
            Privy). Seul le réseau EVM ci-dessous est accepté.
          </p>
        </div>

        <div className="space-y-4">
          <section className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
            <div className="border-b border-v-fg-10 bg-v-fg-05 px-4 py-3 sm:px-5">
              <p className="m-0 font-ui text-[12px] font-semibold uppercase tracking-wide text-v-fg-muted">
                Réseau de dépôt
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center rounded-v-pill bg-[#0D1B2A] px-3 py-1 font-ui text-[13px] font-semibold text-white">
                  EVM
                </span>
                <span className="font-ui text-[15px] font-semibold text-v-fg">{networkLabel}</span>
              </div>
              <p className="mt-2 mb-0 font-ui text-[13px] text-v-fg-muted">
                {networkShort} — tokens compatibles uniquement (ex. ETH, USDC, USDT sur ce réseau).
              </p>
            </div>

            <div className="px-4 py-5 sm:px-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="m-0 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-muted">
                  Votre adresse de dépôt
                </p>
                <span className="inline-flex items-center gap-1 font-ui text-[12px] text-v-fg-muted">
                  <Shield className="h-3.5 w-3.5" aria-hidden />
                  Embedded · Privy
                </span>
              </div>

              <div
                className="rounded-v-card border border-v-fg-10 bg-v-fg-05 px-3 py-3 sm:px-4"
                role="group"
                aria-label="Adresse EVM de dépôt"
              >
                <p
                  className="m-0 break-all font-mono text-[14px] leading-relaxed text-v-fg sm:text-[15px]"
                  tabIndex={0}
                >
                  {primaryWallet.address}
                </p>
              </div>

              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <Button
                  type="button"
                  className="w-full gap-2 sm:flex-1"
                  onClick={() => void copyAddress(primaryWallet.address)}
                >
                  {copied ? (
                    <>
                      <Check className="h-4 w-4" aria-hidden />
                      Adresse copiée
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4" aria-hidden />
                      Copier l’adresse
                    </>
                  )}
                </Button>
                {explorerUrl ? (
                  <Button type="button" variant="outline" className="w-full gap-2 sm:w-auto" asChild>
                    <a href={explorerUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" aria-hidden />
                      Vérifier on-chain
                    </a>
                  </Button>
                ) : null}
              </div>
            </div>
          </section>

          <section
            className="rounded-v-card border border-amber-200/80 bg-amber-50 px-4 py-4 sm:px-5"
            role="note"
          >
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" aria-hidden />
              <div>
                <p className="m-0 font-ui text-[14px] font-semibold text-amber-950">
                  Envoyez uniquement sur ce réseau EVM
                </p>
                <ul className="mt-2 mb-0 list-disc space-y-1 pl-4 font-ui text-[13px] leading-relaxed text-amber-950/90">
                  <li>
                    N’envoyez pas de BTC, SOL, XRP, TRX ou tout actif d’un autre réseau — les fonds
                    peuvent être perdus définitivement.
                  </li>
                  <li>
                    Vérifiez le réseau choisi sur votre exchange avant de valider le retrait (
                    {networkLabel}).
                  </li>
                  <li>
                    Les dépôts peuvent prendre plusieurs minutes selon la congestion blockchain.
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <section className="rounded-v-card border border-v-fg-10 bg-v-card px-4 py-5 shadow-v-subtle sm:px-5">
            <p className="m-0 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-muted">
              Comment ça marche
            </p>
            <ol className="mt-4 m-0 list-none space-y-4 p-0">
              {DEPOSIT_STEPS.map((step, index) => (
                <li key={step.title} className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-v-fg-05 font-ui text-[13px] font-semibold text-v-fg">
                    {index + 1}
                  </span>
                  <div>
                    <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">{step.title}</p>
                    <p className="mt-1 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-body">
                      {step.body}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {otherWallets.length > 0 ? (
            <section className="rounded-v-card border border-v-fg-10 bg-v-card px-4 py-4 sm:px-5">
              <p className="m-0 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-muted">
                Autres adresses
              </p>
              <ul className="mt-3 m-0 list-none space-y-3 p-0">
                {otherWallets.map((wallet) => (
                  <li
                    key={wallet.id}
                    className="flex flex-col gap-2 border-b border-v-fg-05 pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="m-0 font-ui text-[13px] font-medium text-v-fg">
                        {wallet.wallet_type} · {formatEvmNetworkShort(wallet.chain_id)}
                      </p>
                      <p className="mt-1 mb-0 break-all font-mono text-[12px] text-v-fg-muted">
                        {wallet.address}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="shrink-0 gap-1.5"
                      onClick={() => void copyAddress(wallet.address)}
                    >
                      <Copy className="h-3.5 w-3.5" aria-hidden />
                      Copier
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
              <Link href={PORTAL_ROUTES.cryptoWallet}>
                <Wallet className="h-4 w-4" aria-hidden />
                Voir mon wallet crypto
              </Link>
            </Button>
            <button
              type="button"
              disabled={refreshing}
              onClick={() => void load(true)}
              className="v-text-link border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50"
            >
              {refreshing ? 'Actualisation…' : 'Actualiser'}
            </button>
          </div>

          {error ? <p className="portal-auth__error m-0">{error}</p> : null}
        </div>
      </div>
    </PortalPageContainer>
  )
}

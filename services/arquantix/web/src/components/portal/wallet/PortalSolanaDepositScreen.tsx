'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Copy,
  ExternalLink,
  Shield,
  Wallet,
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Button } from '@/components/ui/button'
import {
  PORTAL_ROUTES,
  portalCryptoInstrumentRoute,
  portalCryptoWalletAssetRoute,
} from '@/lib/portal/portalRouting'
import {
  fetchPortalSolanaWalletStatus,
  resolveSolanaExplorerAddressUrl,
} from '@/lib/portal/solanaWalletClient'
import { cn } from '@/lib/utils'

const DEPOSIT_STEPS = [
  {
    title: 'Copiez votre adresse Solana',
    body: 'Utilisez le bouton ci-dessous ou sélectionnez l’adresse pour la copier. Vérifiez chaque caractère avant d’envoyer des fonds.',
  },
  {
    title: 'Envoyez uniquement des SOL (Solana)',
    body: 'Depuis un exchange (Binance, Coinbase, Kraken…) ou un wallet personnel — réseau Solana mainnet uniquement, actif natif SOL.',
  },
  {
    title: 'Attendez la confirmation on-chain',
    body: 'Une fois la transaction confirmée sur Solana, le solde apparaît dans votre wallet Vancelian (généralement sous quelques minutes).',
  },
] as const

export function PortalSolanaDepositScreen() {
  const router = useRouter()
  const [address, setAddress] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    setError('')
    try {
      const status = await fetchPortalSolanaWalletStatus()
      if (status.status === 'missing') {
        router.replace(portalCryptoInstrumentRoute('sol'))
        return
      }
      if (status.status === 'unlinked') {
        router.replace(portalCryptoInstrumentRoute('sol'))
        return
      }
      const addr = status.address?.trim() ?? ''
      if (!addr) {
        setError('Adresse Solana indisponible. Réessayez ou contactez le support.')
        return
      }
      setAddress(addr)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger votre adresse Solana.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [router])

  useEffect(() => {
    void load()
  }, [load])

  const addressReady = Boolean(address) && !loading
  const explorerUrl = address ? resolveSolanaExplorerAddressUrl(address) : null

  const copyAddress = useCallback(async (value: string) => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2500)
    } catch {
      setError('Copie impossible — sélectionnez l’adresse manuellement.')
    }
  }, [])

  return (
    <PortalPageContainer className="py-8 sm:py-10">
      <div className="mx-auto w-full max-w-xl">
        <PortalNavLink
          href={portalCryptoWalletAssetRoute('sol')}
          className="mb-6 inline-flex items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Wallet Solana
        </PortalNavLink>

        <div className="mb-6">
          <VEyebrow>Dépôt</VEyebrow>
          <h1 className="m-0 font-ui text-[26px] font-semibold tracking-v-tight text-v-fg sm:text-[28px]">
            Recevoir des SOL
          </h1>
          <p className="mt-2 mb-0 max-w-prose font-ui text-[15px] leading-relaxed text-v-fg-body">
            Transférez des SOL vers votre wallet embedded Vancelian (non-custodial, sécurisé par
            Privy). Seul le réseau Solana mainnet ci-dessous est pris en charge pour cet actif.
          </p>
        </div>

        <div className="space-y-4">
          <section className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
            <div className="border-b border-v-fg-10 bg-v-fg-05 px-4 py-3 sm:px-5">
              <p className="m-0 font-ui text-[12px] font-semibold uppercase tracking-wide text-v-fg-muted">
                Réseau de dépôt
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span
                  className="inline-flex items-center rounded-v-pill px-3 py-1 font-ui text-[13px] font-semibold text-white"
                  style={{ background: 'linear-gradient(135deg, #9945FF 0%, #14F195 100%)' }}
                >
                  Solana
                </span>
                <span className="font-ui text-[15px] font-semibold text-v-fg">Mainnet</span>
              </div>
              <p className="mt-2 mb-0 font-ui text-[13px] text-v-fg-muted">
                Actif natif <strong className="font-semibold text-v-fg">SOL</strong> uniquement —
                pas de tokens ERC-20, SPL ou autres réseaux sur cette adresse.
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
                aria-label="Adresse de dépôt Solana"
                aria-busy={loading}
              >
                {addressReady ? (
                  <p
                    className="m-0 break-all font-mono text-[14px] leading-relaxed text-v-fg sm:text-[15px]"
                    tabIndex={0}
                  >
                    {address}
                  </p>
                ) : (
                  <div className="portal-shimmer h-[22px] w-full max-w-md rounded-v-input" aria-hidden />
                )}
              </div>

              {!loading && !address && error ? (
                <p className="mt-3 m-0 font-ui text-[14px] text-v-error">{error}</p>
              ) : null}

              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <Button
                  type="button"
                  className="w-full gap-2 sm:flex-1"
                  disabled={!addressReady}
                  onClick={() => address && void copyAddress(address)}
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
                {loading ? (
                  <div
                    className="portal-shimmer h-10 w-full rounded-v-pill sm:w-[168px]"
                    aria-hidden
                  />
                ) : explorerUrl ? (
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
                  Envoyez uniquement des SOL sur Solana mainnet
                </p>
                <ul className="mt-2 mb-0 list-disc space-y-1 pl-4 font-ui text-[13px] leading-relaxed text-amber-950/90">
                  <li>
                    N’envoyez jamais ETH, BTC, USDC (Ethereum), XRP ou tout actif d’un autre réseau
                    — les fonds seraient définitivement perdus.
                  </li>
                  <li>
                    Ne déposez pas de tokens SPL (USDC Solana, BONK, etc.) sauf si Vancelian les
                    prend explicitement en charge : cette adresse est prévue pour le{' '}
                    <strong>SOL natif</strong> uniquement.
                  </li>
                  <li>
                    Sur votre exchange, vérifiez que le réseau sélectionné est bien{' '}
                    <strong>Solana</strong> (parfois libellé « SOL » ou « Solana mainnet »).
                  </li>
                  <li>
                    L’adresse Solana est sensible à la casse — recopiez-la entièrement, sans espace
                    ni retour à la ligne.
                  </li>
                  <li>
                    Les dépôts peuvent prendre plusieurs minutes selon la congestion du réseau
                    Solana.
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

          <section className="rounded-v-card border border-v-fg-10 bg-v-fg-05 px-4 py-4 sm:px-5">
            <p className="m-0 font-ui text-[13px] leading-relaxed text-v-fg-body">
              <strong className="font-semibold text-v-fg">Besoin d’ETH ou de stablecoins ?</strong>{' '}
              Utilisez la page de dépôt EVM pour recevoir ETH, USDC, USDT ou EURC sur Ethereum
              mainnet — adresse différente de votre wallet Solana.
            </p>
            <Button type="button" variant="outline" size="sm" className="mt-3 gap-1.5" asChild>
              <PortalNavLink href={PORTAL_ROUTES.walletDeposit}>Dépôt EVM (Ethereum)</PortalNavLink>
            </Button>
          </section>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
              <PortalNavLink href={portalCryptoWalletAssetRoute('sol')}>
                <Wallet className="h-4 w-4" aria-hidden />
                Voir ma position SOL
              </PortalNavLink>
            </Button>
            <button
              type="button"
              disabled={refreshing}
              onClick={() => void load(true)}
              className={cn(
                'v-text-link border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50',
              )}
            >
              {refreshing ? 'Actualisation…' : 'Actualiser'}
            </button>
          </div>

          {error && addressReady ? <p className="portal-auth__error m-0">{error}</p> : null}
        </div>
      </div>
    </PortalPageContainer>
  )
}

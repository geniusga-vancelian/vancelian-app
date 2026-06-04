'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { PortalBundleInvestFlow } from '@/components/portal/bundles/PortalBundleInvestFlow'
import { PortalBundleWithdrawFlow } from '@/components/portal/bundles/PortalBundleWithdrawFlow'
import { PortalDefiVaultInvestLayout } from '@/components/portal/invest/PortalDefiVaultInvestLayout'
import { PortalInvestFlowPanel } from '@/components/portal/invest/PortalInvestFlowDom'
import type { PortalCryptoWalletBundleDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import { parsePortalVaultFlowMode, PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  portfolioId: string
}

function findBundleByPortfolioId(
  bundles: PortalCryptoBundle[],
  portfolioId: string,
): PortalCryptoBundle | null {
  const normalized = portfolioId.trim()
  return bundles.find((row) => row.portfolioId?.trim() === normalized) ?? null
}

export function PortalBundleInvestScreen({ portfolioId }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = parsePortalVaultFlowMode(searchParams?.get('mode') ?? null)
  const fromMarkets = searchParams?.get('from') === 'markets'
  const [bundle, setBundle] = useState<PortalCryptoBundle | null>(null)
  const [walletDetail, setWalletDetail] = useState<PortalCryptoWalletBundleDetailPayload | null>(
    null,
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const backHref = fromMarkets ? PORTAL_ROUTES.markets : PORTAL_ROUTES.invest
  const backLabel = fromMarkets ? 'Retour aux marchés' : 'Back to vaults'

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [marketsRes, walletRes] = await Promise.all([
        fetch(`/api/portal/markets?locale=${PORTAL_CONTENT_LOCALE}`, { cache: 'no-store' }),
        mode === 'withdraw'
          ? fetch(`/api/portal/crypto-wallet/bundle/${encodeURIComponent(portfolioId)}`, {
              cache: 'no-store',
            })
          : Promise.resolve(null),
      ])

      const marketsData = (await marketsRes.json().catch(() => null)) as PortalMarketsPayload | null
      if (!marketsRes.ok || !marketsData?.bundles) {
        throw new Error('Unable to load basket.')
      }

      const match = findBundleByPortfolioId(marketsData.bundles, portfolioId)
      if (!match) {
        setError('This basket is not available on your account.')
        setBundle(null)
        setWalletDetail(null)
        return
      }
      setBundle(match)

      if (mode === 'withdraw') {
        if (!walletRes?.ok) {
          throw new Error('Unable to load your basket position.')
        }
        const walletPayload = (await walletRes.json()) as PortalCryptoWalletBundleDetailPayload
        setWalletDetail(walletPayload)
      } else {
        setWalletDetail(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load basket.')
      setBundle(null)
      setWalletDetail(null)
    } finally {
      setLoading(false)
    }
  }, [mode, portfolioId])

  useEffect(() => {
    void load()
  }, [load])

  const exitFlow = useCallback(() => {
    router.push(backHref)
  }, [backHref, router])

  const flow = useMemo(() => {
    if (!bundle?.portfolioId) return null
    if (mode === 'withdraw') {
      return (
        <PortalBundleWithdrawFlow
          portfolioId={bundle.portfolioId}
          portfolioName={bundle.title}
          positions={walletDetail?.bundle?.positions}
          currency={walletDetail?.currency ?? 'EUR'}
          onExit={exitFlow}
        />
      )
    }
    return <PortalBundleInvestFlow bundle={bundle} onExit={exitFlow} />
  }, [bundle, exitFlow, mode, walletDetail?.bundle?.positions, walletDetail?.currency])

  return (
    <PortalDefiVaultInvestLayout
      loading={loading}
      error={error}
      onRetry={() => void load()}
      backHref={backHref}
      backLabel={backLabel}
    >
      {flow ? <PortalInvestFlowPanel>{flow}</PortalInvestFlowPanel> : null}
    </PortalDefiVaultInvestLayout>
  )
}

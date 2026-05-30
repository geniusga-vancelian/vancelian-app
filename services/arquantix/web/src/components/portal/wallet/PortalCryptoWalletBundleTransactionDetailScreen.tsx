'use client'

import { useMemo } from 'react'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoTransactionDetailView } from '@/components/portal/wallet/PortalCryptoTransactionDetailView'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildBundleTransactionDetail,
  findBundleTransactionById,
} from '@/lib/portal/bundleTransactionDetailFormat'
import type { PortalCryptoWalletBundleDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import { portalCryptoWalletBundleRoute } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  portfolioId: string
  txId: string
}

export function PortalCryptoWalletBundleTransactionDetailScreen({ portfolioId, txId }: Props) {
  const id = portfolioId.trim()
  const { data, loading, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletBundleDetailPayload>({
      cacheKey: `portal:crypto-wallet:bundle:${id}`,
      url: `/api/portal/crypto-wallet/bundle/${encodeURIComponent(id)}`,
      ttlMs: 45_000,
      errorMessage: 'Unable to load transaction.',
    })

  const tx = useMemo(() => {
    if (!data?.transactions?.length) return undefined
    return findBundleTransactionById(data.transactions, txId)
  }, [data?.transactions, txId])

  const detail = useMemo(() => {
    if (!tx || !data) return null
    return buildBundleTransactionDetail(tx, data.currency)
  }, [tx, data])

  const backHref = portalCryptoWalletBundleRoute(id)
  const backLabel = data?.bundle?.portfolioName
    ? `Back to ${data.bundle.portfolioName}`
    : 'Back to bundle'

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void refresh()}>
          Retry
        </Button>
      </Container>
    )
  }

  if (!detail) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-fg-muted">
          Transaction not found.
        </p>
        <PortalNavLink href={backHref} className="btn btn--secondary no-underline">
          {backLabel}
        </PortalNavLink>
      </Container>
    )
  }

  return (
    <PortalPageContainer>
      <PortalCryptoTransactionDetailView
        detail={detail}
        backHref={backHref}
        backLabel={backLabel}
      />
    </PortalPageContainer>
  )
}

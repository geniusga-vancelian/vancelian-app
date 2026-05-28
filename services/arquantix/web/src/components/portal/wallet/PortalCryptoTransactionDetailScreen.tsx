'use client'

import { useMemo } from 'react'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoTransactionDetailView } from '@/components/portal/wallet/PortalCryptoTransactionDetailView'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildCryptoTransactionDetail,
  findCryptoWalletTransactionById,
} from '@/lib/portal/cryptoTransactionDetailFormat'
import { consolidateSwapTransactions } from '@/lib/portal/cryptoTransactionHistoryFormat'
import type { PortalCryptoWalletDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import {
  portalCryptoWalletAssetRoute,
  portalCryptoWalletTransactionsRoute,
} from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  asset: string
  txId: string
}

export function PortalCryptoTransactionDetailScreen({ asset, txId }: Props) {
  const ticker = asset.trim().toUpperCase()
  const { data, loading, error, refresh } = usePortalCachedScreen<PortalCryptoWalletDetailPayload>({
    cacheKey: `portal:crypto-wallet:${ticker}`,
    url: `/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`,
    ttlMs: 45_000,
    errorMessage: 'Impossible de charger la transaction.',
    scopeAware: true,
  })

  const tx = useMemo(() => {
    if (!data?.transactions?.length) return undefined
    const consolidated = consolidateSwapTransactions(data.transactions)
    return findCryptoWalletTransactionById(consolidated, txId)
  }, [data?.transactions, txId])

  const detail = useMemo(() => {
    if (!tx || !data) return null
    return buildCryptoTransactionDetail(tx, data.currency)
  }, [tx, data])

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void refresh()}>
          Réessayer
        </Button>
      </Container>
    )
  }

  if (!detail) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-fg-muted">
          Transaction introuvable.
        </p>
        <PortalNavLink
          href={portalCryptoWalletAssetRoute(ticker)}
          className="btn btn--secondary no-underline"
        >
          Retour à la position
        </PortalNavLink>
      </Container>
    )
  }

  return (
    <PortalPageContainer>
      <PortalCryptoTransactionDetailView
        detail={detail}
        backHref={portalCryptoWalletAssetRoute(ticker)}
        backLabel="Retour à la position"
      />
    </PortalPageContainer>
  )
}

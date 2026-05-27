'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { Button } from '@/components/ui/button'
import type { PortalChain } from '@/config/portalChains'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  lombardDepositCtaLabel,
  lombardGuaranteeTagline,
  normalizeLombardCollateralSymbol,
} from '@/lib/portal/lombard/lombardWalletAsset'
import { useLombardV1PortalEnabled } from '@/lib/portal/lombard/useLombardV1PortalEnabled'
import { trackLombardCtaClicked } from '@/lib/portal/portalProductAnalytics'
import {
  portalBorrowRoute,
  portalSwapBuyRoute,
} from '@/lib/portal/portalRouting'

type Props = {
  asset: string
  chain: PortalChain
  balance: number
}

function lombardDepositHref(collateral: 'cbBTC' | 'cbETH'): string {
  if (collateral === 'cbBTC') {
    return portalSwapBuyRoute('CBBTC', 'base')
  }
  return portalSwapBuyRoute('CBETH', 'base')
}

export function PortalLombardWalletAssetCta({ asset, chain, balance }: Props) {
  const { enabled, loading } = useLombardV1PortalEnabled()
  const collateral = normalizeLombardCollateralSymbol(asset)

  if (loading || !enabled || chain !== 'base' || !collateral) {
    return null
  }

  const hasBalance = Number.isFinite(balance) && balance > 0
  const tagline = lombardGuaranteeTagline(collateral)

  const trackClick = (cta: 'borrow_usdc' | 'deposit_to_borrow') => {
    trackLombardCtaClicked({
      asset: collateral,
      chainId: VANCELIAN_LOMBARD_V1.chainId,
      source: 'wallet_asset_detail',
      cta,
    })
  }

  return (
    <section className="flex w-full flex-col gap-3 rounded-2xl border border-v-border bg-v-surface p-5">
      <div className="flex flex-col gap-1">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Avance de liquidité</h2>
        <p className="m-0 font-ui text-[14px] leading-relaxed text-v-muted">{tagline}</p>
        <p className="m-0 font-ui text-[12px] text-v-muted">{VANCELIAN_LOMBARD_V1.poweredByLabel}</p>
      </div>

      {hasBalance ? (
        <PortalNavLink
          href={portalBorrowRoute({ collateral })}
          className="no-underline"
          onClick={() => trackClick('borrow_usdc')}
        >
          <Button type="button" className="w-full">
            Borrow USDC
          </Button>
        </PortalNavLink>
      ) : (
        <PortalNavLink
          href={lombardDepositHref(collateral)}
          className="no-underline"
          onClick={() => trackClick('deposit_to_borrow')}
        >
          <Button type="button" variant="outline" className="w-full">
            {lombardDepositCtaLabel(collateral)}
          </Button>
        </PortalNavLink>
      )}
    </section>
  )
}

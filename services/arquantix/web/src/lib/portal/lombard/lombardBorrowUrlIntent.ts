import type { LombardCollateralSymbol } from '@/lib/portal/lombard/lombardConfig'
import { normalizeLombardCollateralSymbol } from '@/lib/portal/lombard/lombardWalletAsset'

export type PortalBorrowUrlIntent =
  | { mode: 'full' }
  | { mode: 'prefilled'; collateral: LombardCollateralSymbol }

export function parsePortalBorrowUrlIntent(params: URLSearchParams | null): PortalBorrowUrlIntent {
  if (!params) return { mode: 'full' }

  const raw =
    params.get('collateral')?.trim() ??
    params.get('asset')?.trim() ??
    params.get('guarantee')?.trim() ??
    ''

  const collateral = normalizeLombardCollateralSymbol(raw)
  if (!collateral) return { mode: 'full' }

  return { mode: 'prefilled', collateral }
}

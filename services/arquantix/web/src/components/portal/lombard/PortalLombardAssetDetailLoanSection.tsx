'use client'

import type { PortalChain } from '@/config/portalChains'
import { PortalLombardAssetLoanCompactCard } from '@/components/portal/lombard/PortalLombardAssetLoanCompactCard'
import {
  resolveLombardAssetDetailLoanPosition,
  shouldShowLombardAssetDetailLoanCard,
} from '@/lib/portal/lombard/lombardPositionVisibility'
import { usePortalLombardPositions } from '@/lib/portal/lombard/usePortalLombardPositions'
import { useLombardV1PortalEnabled } from '@/lib/portal/lombard/useLombardV1PortalEnabled'

type Props = {
  asset: string
  chain: PortalChain
}

export function PortalLombardAssetDetailLoanSection({ asset, chain }: Props) {
  const { enabled: lombardEnabled } = useLombardV1PortalEnabled()
  const { positions } = usePortalLombardPositions()
  const position = resolveLombardAssetDetailLoanPosition(positions, asset)

  if (
    !shouldShowLombardAssetDetailLoanCard({
      asset,
      lombardEnabled,
      chain,
      position,
    }) ||
    !position
  ) {
    return null
  }

  return <PortalLombardAssetLoanCompactCard position={position} />
}

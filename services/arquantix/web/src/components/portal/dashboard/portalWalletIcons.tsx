import type { PortalWalletRow } from '@/lib/portal/dashboardTypes'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

const WALLET_KALAI_ICON: Record<PortalWalletRow['iconKey'], string> = {
  euro: 'payment-card',
  savings: 'suitcase',
  offers: 'star',
  portfolio: 'pie-chart',
  crypto: 'bitcoin',
}

const WALLET_AVT_TONE: Record<PortalWalletRow['iconTone'], string> = {
  blue: 'avt--blue',
  green: 'avt--green',
  terracotta: 'avt--terra',
  fg: 'avt--dark',
  'fg-body': 'avt--dark',
}

/** Avatar 52px — preview/67-card-account (anthracite) ou teintes produit. */
export function PortalWalletRowAvatar({
  iconKey,
  iconTone,
  locked,
  surface = 'account',
}: {
  iconKey: PortalWalletRow['iconKey']
  iconTone: PortalWalletRow['iconTone']
  locked?: boolean
  /** `account` = avt--dark (DS 67) · `product` = teinte par ligne. */
  surface?: 'account' | 'product'
}) {
  return (
    <span
      className={cn(
        'avt avt--52 shrink-0',
        surface === 'account' ? 'avt--dark' : WALLET_AVT_TONE[iconTone],
        locked && 'opacity-50',
      )}
    >
      <KalaiIcon name={WALLET_KALAI_ICON[iconKey]} size={24} className="avt__ic !h-[50%] !w-[50%]" />
    </span>
  )
}

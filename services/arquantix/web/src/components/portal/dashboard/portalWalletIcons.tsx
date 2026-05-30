import type { PortalWalletRow } from '@/lib/portal/dashboardTypes'
import {
  AppAccountDot,
  type AppAccountDotVariant,
} from '@/components/design-system/app/AppAccountDot'
import type { KalaiIconProps } from '@/components/ui/KalaiIcon'

type WalletAvatarId = PortalWalletRow['id'] | 'credit-line'

type AvatarConfig = {
  variant: AppAccountDotVariant
  glyph: string | { name: NonNullable<KalaiIconProps['name']> }
  glyphSize?: number
}

/** Couleurs + glyphes — handoff Portfolio.html `ACCOUNT_GROUPS` / `AccountDot`. */
const ROW_AVATAR: Record<PortalWalletRow['id'], AvatarConfig> = {
  euro: { variant: 'warm', glyph: '€' },
  savings: { variant: 'green', glyph: 'É' },
  offers: { variant: 'terra', glyph: { name: 'star' } },
  portfolio: { variant: 'blue', glyph: { name: 'suitcase' } },
  crypto: { variant: 'safran', glyph: { name: 'bitcoin' } },
}

const CREDIT_LINE_AVATAR: AvatarConfig = {
  variant: 'warm',
  glyph: { name: 'money-dollar' },
  glyphSize: 20,
}

function resolveWalletAvatarConfig(rowId: WalletAvatarId, locked?: boolean): AvatarConfig {
  if (rowId === 'credit-line') return CREDIT_LINE_AVATAR

  const base = ROW_AVATAR[rowId]
  if (rowId === 'euro') {
    return { ...base, variant: locked ? 'warm' : 'dark' }
  }
  return base
}

/** Pastille compte — teintes produit DS (`.avt--warm`, `--green`, `--terra`, …). */
export function PortalWalletRowAvatar({
  rowId,
  locked,
}: {
  rowId: WalletAvatarId
  locked?: boolean
}) {
  const config = resolveWalletAvatarConfig(rowId, locked)

  return (
    <AppAccountDot
      size={48}
      variant={config.variant}
      glyph={config.glyph}
      glyphSize={config.glyphSize ?? 20}
      className="shrink-0"
    />
  )
}

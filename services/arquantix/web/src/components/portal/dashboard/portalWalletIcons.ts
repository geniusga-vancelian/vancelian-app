import type { PortalWalletRow } from '@/lib/portal/dashboardTypes'
import type { LucideIcon } from 'lucide-react'
import {
  ArrowDownToLine,
  Bitcoin,
  Euro,
  Percent,
  PieChart,
  PiggyBank,
} from 'lucide-react'

const WALLET_ICON_TONE_CLASS: Record<PortalWalletRow['iconTone'], string> = {
  blue: 'bg-v-blue text-white',
  green: 'bg-v-green text-white',
  terracotta: 'bg-v-terracotta text-white',
  fg: 'bg-v-fg text-white',
  'fg-body': 'bg-v-fg-body text-white',
}

export function portalWalletIconToneClass(tone: PortalWalletRow['iconTone']): string {
  return WALLET_ICON_TONE_CLASS[tone]
}

export function portalWalletIcon(iconKey: PortalWalletRow['iconKey']): LucideIcon {
  switch (iconKey) {
    case 'euro':
      return Euro
    case 'savings':
      return PiggyBank
    case 'offers':
      return Percent
    case 'portfolio':
      return PieChart
    case 'crypto':
      return Bitcoin
    default:
      return ArrowDownToLine
  }
}

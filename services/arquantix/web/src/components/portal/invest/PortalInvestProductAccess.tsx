'use client'

import type { LucideIcon } from 'lucide-react'
import {
  Bitcoin,
  Home,
  PieChart,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import {
  PortalSettingsCard,
  PortalSettingsRow,
} from '@/components/portal/profile/PortalProfileUi'

type ProductAccess = {
  id: string
  title: string
  description: string
  value: string
  icon: LucideIcon
  iconClassName: string
}

const INVEST_PRODUCT_ACCESS: ProductAccess[] = [
  {
    id: 'savings',
    title: 'Épargne rémunérée',
    description: 'Jusqu’à 9% APY, disponible à tout moment.',
    value: '9% max',
    icon: Wallet,
    iconClassName: 'bg-[#E8F0FE] text-[#2563EB]',
  },
  {
    id: 'exclusive',
    title: 'Offres exclusives',
    description: 'Projets sélectionnés jusqu’à 13% APR.',
    value: '13% APR',
    icon: Home,
    iconClassName: 'bg-[#EEF2FF] text-[#4F46E5]',
  },
  {
    id: 'managed',
    title: 'Gestion déléguée',
    description: 'Stratégie sur mesure par nos gérants.',
    value: 'Sur mesure',
    icon: TrendingUp,
    iconClassName: 'bg-[#FEF3C7] text-[#D97706]',
  },
  {
    id: 'crypto',
    title: 'Acheter des crypto',
    description: 'Plus de 50 cryptoactifs disponibles.',
    value: '50+ actifs',
    icon: Bitcoin,
    iconClassName: 'bg-[#FEF9C3] text-[#CA8A04]',
  },
  {
    id: 'themes',
    title: 'Thématiques',
    description: 'Paniers DeFi, Layer 2, métavers…',
    value: 'Paniers',
    icon: PieChart,
    iconClassName: 'bg-[#DCFCE7] text-[#16A34A]',
  },
]

function AccessIcon({ icon: Icon, className }: { icon: LucideIcon; className: string }) {
  return (
    <span
      className={`inline-flex h-10 w-10 items-center justify-center rounded-v-input ${className}`}
    >
      <Icon className="h-5 w-5" strokeWidth={1.75} />
    </span>
  )
}

/** Accès produits — équivalent Flutter `OffersScreen._investOptions`. */
export function PortalInvestProductAccess() {
  return (
    <PortalSettingsCard>
      {INVEST_PRODUCT_ACCESS.map((item) => (
        <PortalSettingsRow
          key={item.id}
          title={item.title}
          subtitle={item.description}
          leading={<AccessIcon icon={item.icon} className={item.iconClassName} />}
          trailing={
            <span className="flex items-center gap-2">
              <span className="font-ui text-[14px] font-medium text-v-fg-muted">{item.value}</span>
              <span className="font-ui text-[14px] text-v-fg-muted" aria-hidden>
                ›
              </span>
            </span>
          }
        />
      ))}
    </PortalSettingsCard>
  )
}

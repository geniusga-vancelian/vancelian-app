import type { LucideIcon } from 'lucide-react'
import { Bitcoin, GraduationCap, Home, Search, TrendingUp } from 'lucide-react'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export type PortalNavTab = {
  id: string
  label: string
  href: string
  icon: LucideIcon
}

/** Tabs principaux — alignés sur `DEFAULT_APP_MAIN_TABS` / shell Flutter. */
export const PORTAL_MAIN_NAV_TABS: PortalNavTab[] = [
  { id: 'home', label: 'My portfolio', href: PORTAL_ROUTES.dashboard, icon: Home },
  { id: 'invest', label: 'Investing', href: PORTAL_ROUTES.invest, icon: TrendingUp },
  { id: 'markets', label: 'Markets', href: PORTAL_ROUTES.markets, icon: Bitcoin },
  { id: 'academy', label: 'Academy', href: PORTAL_ROUTES.academy, icon: GraduationCap },
]

/** Action Search (hors tab bar mobile, bouton distinct). */
export const PORTAL_SEARCH_NAV = {
  label: 'Search',
  href: PORTAL_ROUTES.search,
  icon: Search,
} as const

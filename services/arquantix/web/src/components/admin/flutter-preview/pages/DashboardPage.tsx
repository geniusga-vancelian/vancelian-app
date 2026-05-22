import { Bell, Settings } from 'lucide-react'

import { colors, spacing } from '@/lib/admin/flutter-preview/tokens'
import { MockAppTopNavBar } from '../mocks/AppTopNavBar'
import { MockAppTabBar, DEFAULT_MAIN_TABS } from '../mocks/AppTabBar'
import { MockBalanceHeader } from '../mocks/BalanceHeader'
import { MockMyAccountWidget } from '../mocks/MyAccountWidget'
import { MockExclusiveOffersWidget } from '../mocks/ExclusiveOffersWidget'
import { MockBlogALaUneCard } from '../mocks/BlogALaUneCard'

/// Composition page **Dashboard** (id=`dashboard`).
/// Topnav (profile + notifications + settings) → balance header → widgets
/// account / exclusive offers / news → tab bar bas.
export function DashboardPagePreview() {
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: colors.pageBackground,
        position: 'relative',
        paddingBottom: 80,
      }}
    >
      <MockAppTopNavBar
        leading={{ kind: 'profile', initials: 'JA' }}
        actions={[
          { icon: <Bell size={20} color={colors.textPrimary} />, showDot: true },
          { icon: <Settings size={20} color={colors.textPrimary} /> },
        ]}
      />
      <MockBalanceHeader />
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.s2 }}>
        <MockMyAccountWidget />
        <MockExclusiveOffersWidget />
        <MockBlogALaUneCard />
      </div>
      <MockAppTabBar items={DEFAULT_MAIN_TABS} selectedIndex={0} />
    </div>
  )
}

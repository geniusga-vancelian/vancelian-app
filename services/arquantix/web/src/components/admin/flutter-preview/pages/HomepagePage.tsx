import { Bell } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'
import { MockAppTopNavBar } from '../mocks/AppTopNavBar'
import { MockAppTabBar, DEFAULT_MAIN_TABS } from '../mocks/AppTabBar'
import { MockBlogALaUneCard } from '../mocks/BlogALaUneCard'
import { MockExclusiveOffersWidget } from '../mocks/ExclusiveOffersWidget'

/// Composition page **Homepage** (id=`home`).
/// Hero (gradient + accroche) → news à la Une → offres exclusives → tab bar.
export function HomepagePagePreview() {
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
        actions={[{ icon: <Bell size={20} color={colors.textPrimary} /> }]}
      />

      {/* Hero */}
      <div
        style={{
          margin: `${spacing.s2}px ${spacing.lg}px`,
          borderRadius: 20,
          padding: spacing.s5,
          background: 'linear-gradient(135deg, #6155F5 0%, #00C3D0 100%)',
          color: colors.white,
          minHeight: 180,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: spacing.s4,
        }}
      >
        <div>
          <div style={{ ...typoStyle(typo.labelEmphasized), color: 'rgba(255,255,255,0.85)' }}>
            VANCELIAN INVEST
          </div>
          <div
            style={{
              ...typoStyle(typo.headerPrimary),
              color: colors.white,
              marginTop: spacing.s2,
            }}
          >
            Vos investissements, simplifiés.
          </div>
        </div>
        <div
          style={{
            alignSelf: 'flex-start',
            padding: '10px 16px',
            borderRadius: 100,
            backgroundColor: 'rgba(255,255,255,0.22)',
            ...typoStyle(typo.buttonEmphasized),
            color: colors.white,
          }}
        >
          Découvrir
        </div>
      </div>

      <MockBlogALaUneCard />
      <MockExclusiveOffersWidget />

      <MockAppTabBar items={DEFAULT_MAIN_TABS} selectedIndex={0} />
    </div>
  )
}

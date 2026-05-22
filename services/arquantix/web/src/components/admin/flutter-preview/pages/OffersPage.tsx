import { Search } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'
import { MockAppTopNavBar } from '../mocks/AppTopNavBar'
import { MockAppTabBar, DEFAULT_MAIN_TABS } from '../mocks/AppTabBar'
import { MockSavingVaultsWidget } from '../mocks/SavingVaultsWidget'
import { MockExclusiveOffersWidget } from '../mocks/ExclusiveOffersWidget'

const CATEGORIES = [
  { label: 'Tous', active: true },
  { label: 'Crypto' },
  { label: 'Immo' },
  { label: 'Obligations' },
  { label: 'Actions' },
]

/// Composition page **Offers** (id=`offers`).
/// Topnav avec titre "Offers", chips de catégories, widget Saving Vaults,
/// puis carousel d'offres exclusives.
export function OffersPagePreview() {
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
        leading={{ kind: 'none' }}
        title="Offres"
        actions={[{ icon: <Search size={20} color={colors.textPrimary} /> }]}
      />

      {/* Page header (Figma `headerPrimary`) */}
      <div style={{ padding: `${spacing.s2}px ${spacing.lg}px ${spacing.s4}px` }}>
        <div style={{ ...typoStyle(typo.headerPrimary), color: colors.textPrimary }}>
          Investir
        </div>
        <div
          style={{
            ...typoStyle(typo.bodyRegular),
            color: colors.textSecondary,
            marginTop: 4,
          }}
        >
          Découvrez nos offres exclusives et vaults d’épargne.
        </div>
      </div>

      {/* Chips catégories */}
      <div
        style={{
          display: 'flex',
          gap: spacing.s2,
          padding: `0 ${spacing.lg}px`,
          overflowX: 'auto',
          marginBottom: spacing.s3,
        }}
      >
        {CATEGORIES.map((c) => (
          <div
            key={c.label}
            style={{
              padding: '8px 14px',
              borderRadius: 100,
              backgroundColor: c.active ? colors.indigo : colors.cardBackground,
              color: c.active ? colors.white : colors.textPrimary,
              ...typoStyle(typo.bodySmEmphasized),
              whiteSpace: 'nowrap',
              border: c.active ? 'none' : `1px solid ${colors.separatorOpaque}`,
            }}
          >
            {c.label}
          </div>
        ))}
      </div>

      <MockSavingVaultsWidget />
      <MockExclusiveOffersWidget />

      <MockAppTabBar items={DEFAULT_MAIN_TABS} selectedIndex={1} />
    </div>
  )
}

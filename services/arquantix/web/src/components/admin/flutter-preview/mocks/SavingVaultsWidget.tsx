import { Lock, ChevronRight } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

const VAULTS = [
  { title: 'BTC Vault', subtitle: 'Pegged BTC index', apy: '8.2%', accent: '#FF9230' },
  { title: 'ETH Vault', subtitle: 'Liquid staking', apy: '5.4%', accent: '#627EEA' },
  { title: 'EUR Vault', subtitle: 'Yield Euro', apy: '3.1%', accent: '#2196F3' },
]

/// Mock du widget "Saving Vaults" (page Offers). Carte avec liste de vaults.
export function MockSavingVaultsWidget() {
  return (
    <div
      style={{
        margin: `${spacing.s2}px ${spacing.lg}px`,
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: spacing.s4,
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.05)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: spacing.s3,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.s2 }}>
          <Lock size={18} color={colors.indigo} />
          <div style={{ ...typoStyle(typo.sectionTitle), color: colors.textPrimary }}>
            Saving Vaults
          </div>
        </div>
        <ChevronRight size={20} color={colors.textMuted} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {VAULTS.map((v, idx) => (
          <div
            key={v.title}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: spacing.s3,
              padding: `${spacing.s3}px 0`,
              borderTop: idx === 0 ? 'none' : `1px solid ${colors.separatorOpaque}`,
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                backgroundColor: v.accent,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Lock size={18} color={colors.white} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary }}>
                {v.title}
              </div>
              <div style={{ ...typoStyle(typo.itemSupporting), color: colors.textSecondary }}>
                {v.subtitle}
              </div>
            </div>
            <div
              style={{
                ...typoStyle(typo.itemPrimary),
                color: colors.semanticPositive,
              }}
            >
              {v.apy}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

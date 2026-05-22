import { Wallet, ChevronRight } from 'lucide-react'

import { colors, spacing, typo, typoStyle, cryptoBrandColor } from '@/lib/admin/flutter-preview/tokens'

type Holding = { ticker: string; name: string; balance: string; counterValue: string; delta: number }

const HOLDINGS: Holding[] = [
  { ticker: 'EUR', name: 'Euro', balance: '€8,200.10', counterValue: '€8,200.10', delta: 0 },
  { ticker: 'BTC', name: 'Bitcoin', balance: '0.0521', counterValue: '€2,910.78', delta: 1.4 },
  { ticker: 'ETH', name: 'Ethereum', balance: '0.84', counterValue: '€1,729.33', delta: -0.6 },
]

/// Mock du widget "My account" (dashboard).
/// Carte blanche radius 16, header (titre + chevron), liste de holdings.
export function MockMyAccountWidget() {
  return (
    <ModuleCard
      header={
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.s2 }}>
            <Wallet size={18} color={colors.indigo} />
            <div style={{ ...typoStyle(typo.sectionTitle), color: colors.textPrimary }}>
              My account
            </div>
          </div>
          <ChevronRight size={20} color={colors.textMuted} />
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {HOLDINGS.map((h, idx) => (
          <div
            key={h.ticker}
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
                borderRadius: 20,
                backgroundColor: cryptoBrandColor(h.ticker),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: colors.white,
                ...typoStyle(typo.bodySmEmphasized),
              }}
            >
              {h.ticker}
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary }}>
                {h.name}
              </div>
              <div style={{ ...typoStyle(typo.itemSupporting), color: colors.textSecondary }}>
                {h.balance} {h.ticker}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary }}>
                {h.counterValue}
              </div>
              <div
                style={{
                  ...typoStyle(typo.bodySmEmphasized),
                  color:
                    h.delta > 0
                      ? colors.semanticPositive
                      : h.delta < 0
                        ? colors.semanticNegative
                        : colors.textMuted,
                }}
              >
                {h.delta > 0 ? '+' : ''}
                {h.delta.toFixed(2)}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </ModuleCard>
  )
}

/// Carte module standard (background blanc, radius 16, padding s4).
/// Réutilisé par les autres widgets dashboard.
export function ModuleCard({
  header,
  children,
}: {
  header?: React.ReactNode
  children: React.ReactNode
}) {
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
      {header ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: spacing.s3,
          }}
        >
          {header}
        </div>
      ) : null}
      {children}
    </div>
  )
}

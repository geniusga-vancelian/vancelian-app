import { ArrowDownToLine, ArrowUpFromLine, BarChart3, RefreshCw } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

/// Mock du header `Dashboard` Flutter : balance principale + variation +
/// mini line chart + 4 boutons d'action ronds (Top up, Withdraw, Trade,
/// Convert). Couleurs et typo ports DS.
export function MockBalanceHeader() {
  const actions: Array<{ icon: React.ReactNode; label: string }> = [
    { icon: <ArrowDownToLine size={20} color={colors.indigo} />, label: 'Top up' },
    { icon: <ArrowUpFromLine size={20} color={colors.indigo} />, label: 'Withdraw' },
    { icon: <BarChart3 size={20} color={colors.indigo} />, label: 'Trade' },
    { icon: <RefreshCw size={20} color={colors.indigo} />, label: 'Convert' },
  ]

  return (
    <div
      style={{
        padding: `${spacing.s4}px ${spacing.lg}px ${spacing.s6}px ${spacing.lg}px`,
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.s4,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ ...typoStyle(typo.labelEmphasized), color: colors.textSecondary }}>
          Total balance
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: spacing.s2,
          }}
        >
          <div style={{ ...typoStyle(typo.amountPrimary), color: colors.textPrimary }}>
            €12,840.21
          </div>
          <div
            style={{
              ...typoStyle(typo.bodySmEmphasized),
              color: colors.semanticPositive,
            }}
          >
            +1.24%
          </div>
        </div>
      </div>

      <MiniLineChart />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: spacing.s2,
        }}
      >
        {actions.map((a) => (
          <div
            key={a.label}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 24,
                backgroundColor: colors.cardBackground,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 1px 2px rgba(15, 23, 42, 0.06)',
              }}
            >
              {a.icon}
            </div>
            <div style={{ ...typoStyle(typo.bodySmEmphasized), color: colors.textPrimary }}>
              {a.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MiniLineChart() {
  /// Simple polyline path SVG — pas de data dynamique (mock V1).
  const points = '0,40 25,35 50,38 75,28 100,32 125,20 150,24 175,12 200,18 225,8 250,14 275,5 300,10'
  return (
    <div
      style={{
        height: 56,
        width: '100%',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <svg viewBox="0 0 300 50" width="100%" height="100%" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke={colors.indigo}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  )
}

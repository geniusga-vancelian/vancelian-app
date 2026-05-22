import { ChevronDown } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

const FAQ = [
  { q: 'Quelle est la durée minimale de blocage ?', open: true, a: 'La durée minimale est de 6 mois. Vous pouvez ensuite retirer vos fonds à tout moment.' },
  { q: 'Y a-t-il des frais ?', open: false },
  { q: 'Puis-je sortir avant la fin ?', open: false },
  { q: 'Comment sont calculés les rendements ?', open: false },
]

/// Mock du module "FAQ" (page projet) — accordion. Mock V1 : la 1ère ligne
/// est ouverte, les autres fermées (visuel statique, pas d'interaction).
export function MockFaqModule() {
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
      <div style={{ ...typoStyle(typo.sectionTitle), color: colors.textPrimary, marginBottom: spacing.s3 }}>
        FAQ
      </div>
      {FAQ.map((row, idx) => (
        <div
          key={idx}
          style={{
            borderTop: idx === 0 ? 'none' : `1px solid ${colors.separatorOpaque}`,
            padding: `${spacing.s3}px 0`,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: spacing.s3,
            }}
          >
            <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary, flex: 1 }}>
              {row.q}
            </div>
            <ChevronDown
              size={20}
              color={colors.textMuted}
              style={{
                transition: 'transform 200ms ease',
                transform: row.open ? 'rotate(180deg)' : 'rotate(0deg)',
              }}
            />
          </div>
          {row.open && row.a ? (
            <div
              style={{
                ...typoStyle(typo.bodyRegular),
                color: colors.textSecondary,
                marginTop: spacing.s2,
              }}
            >
              {row.a}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  )
}

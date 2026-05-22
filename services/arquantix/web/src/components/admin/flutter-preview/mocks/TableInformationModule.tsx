import { Info } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

const ROWS: Array<{ label: string; value: string }> = [
  { label: 'Type', value: 'Real estate' },
  { label: 'Pays', value: 'France' },
  { label: 'Ville', value: 'Lyon' },
  { label: 'Durée', value: '24 mois' },
  { label: 'Rendement cible', value: '7.2%' },
  { label: 'Ticket d’entrée', value: '€1,000' },
  { label: 'Devise', value: 'EUR' },
]

/// Mock du module "Table information" (page projet).
/// Carte avec en-tête + liste de lignes label / value séparées par border-bottom.
export function MockTableInformationModule() {
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
          gap: spacing.s2,
          marginBottom: spacing.s3,
        }}
      >
        <Info size={18} color={colors.indigo} />
        <div style={{ ...typoStyle(typo.sectionTitle), color: colors.textPrimary }}>
          Informations clés
        </div>
      </div>
      <div>
        {ROWS.map((r, idx) => (
          <div
            key={r.label}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: `${spacing.s3}px 0`,
              borderTop: idx === 0 ? 'none' : `1px solid ${colors.separatorOpaque}`,
            }}
          >
            <div style={{ ...typoStyle(typo.itemSecondary), color: colors.textSecondary }}>
              {r.label}
            </div>
            <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary }}>
              {r.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

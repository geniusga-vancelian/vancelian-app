import { Star, ChevronRight } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

const OFFERS = [
  {
    title: 'Vault Sphere I',
    subtitle: 'BTC Index — 12 mois',
    yield: '+8.2%',
    cover: 'linear-gradient(135deg, #6155F5 0%, #DB34F2 100%)',
  },
  {
    title: 'Real Estate Lyon',
    subtitle: 'Fond immobilier',
    yield: '+6.4%',
    cover: 'linear-gradient(135deg, #00C3D0 0%, #00DAC3 100%)',
  },
  {
    title: 'Green Bonds',
    subtitle: 'Obligations vertes',
    yield: '+4.9%',
    cover: 'linear-gradient(135deg, #34C759 0%, #00DAC3 100%)',
  },
]

/// Mock du widget "Exclusive offers" (dashboard).
/// Carte avec carousel horizontal d'offres (3 cards visibles).
export function MockExclusiveOffersWidget() {
  return (
    <div
      style={{
        margin: `${spacing.s2}px 0`,
        padding: `${spacing.s4}px 0 0 0`,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `0 ${spacing.lg}px`,
          marginBottom: spacing.s3,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.s2 }}>
          <Star size={18} color={colors.indigo} />
          <div style={{ ...typoStyle(typo.sectionTitle), color: colors.textPrimary }}>
            Exclusive offers
          </div>
        </div>
        <ChevronRight size={20} color={colors.textMuted} />
      </div>
      <div
        style={{
          display: 'flex',
          gap: spacing.s3,
          padding: `0 ${spacing.lg}px ${spacing.s2}px`,
          overflowX: 'auto',
          scrollSnapType: 'x mandatory',
        }}
      >
        {OFFERS.map((offer, idx) => (
          <div
            key={idx}
            style={{
              flex: '0 0 220px',
              scrollSnapAlign: 'start',
              borderRadius: 16,
              overflow: 'hidden',
              backgroundColor: colors.cardBackground,
              boxShadow: '0 1px 2px rgba(15, 23, 42, 0.05)',
            }}
          >
            <div
              style={{
                height: 110,
                background: offer.cover,
                position: 'relative',
                color: colors.white,
                padding: spacing.s3,
                display: 'flex',
                alignItems: 'flex-end',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: spacing.s3,
                  right: spacing.s3,
                  padding: '4px 8px',
                  borderRadius: 12,
                  backgroundColor: 'rgba(0,0,0,0.35)',
                  ...typoStyle(typo.labelEmphasized),
                  color: colors.white,
                }}
              >
                {offer.yield}
              </div>
            </div>
            <div style={{ padding: spacing.s3 }}>
              <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary }}>
                {offer.title}
              </div>
              <div
                style={{
                  ...typoStyle(typo.itemSupporting),
                  color: colors.textSecondary,
                  marginTop: 2,
                }}
              >
                {offer.subtitle}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

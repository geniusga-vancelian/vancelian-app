import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

const CARDS = [
  {
    title: 'Invitez un ami',
    subtitle: 'Gagnez 25 € de crédit',
    cta: 'Partager',
    bg: 'linear-gradient(135deg, #6155F5 0%, #00C3D0 100%)',
  },
  {
    title: 'Activez 2FA',
    subtitle: 'Sécurisez votre compte',
    cta: 'Activer',
    bg: 'linear-gradient(135deg, #1C1C1E 0%, #6155F5 100%)',
  },
  {
    title: 'Nouveau : Vault BTC',
    subtitle: 'Découvrez l\'offre',
    cta: 'Voir',
    bg: 'linear-gradient(135deg, #FF8D28 0%, #FF383C 100%)',
  },
]

/// Mock du carousel "Marketing cards" (small) — utilisé sur Compte Euro et
/// d'autres pages. Cards compactes 220×100, scrollable horizontalement.
export function MockMarketingCardSlider() {
  return (
    <div
      style={{
        display: 'flex',
        gap: spacing.s3,
        padding: `${spacing.s2}px ${spacing.lg}px`,
        overflowX: 'auto',
        scrollSnapType: 'x mandatory',
      }}
    >
      {CARDS.map((c, idx) => (
        <div
          key={idx}
          style={{
            flex: '0 0 240px',
            height: 110,
            borderRadius: 16,
            background: c.bg,
            scrollSnapAlign: 'start',
            padding: spacing.s4,
            color: colors.white,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ ...typoStyle(typo.itemPrimary), color: colors.white }}>
              {c.title}
            </div>
            <div
              style={{
                ...typoStyle(typo.bodySmRegular),
                color: 'rgba(255,255,255,0.85)',
                marginTop: 2,
              }}
            >
              {c.subtitle}
            </div>
          </div>
          <div
            style={{
              alignSelf: 'flex-start',
              padding: '6px 12px',
              borderRadius: 100,
              backgroundColor: 'rgba(255,255,255,0.22)',
              ...typoStyle(typo.labelEmphasized),
              color: colors.white,
            }}
          >
            {c.cta}
          </div>
        </div>
      ))}
    </div>
  )
}

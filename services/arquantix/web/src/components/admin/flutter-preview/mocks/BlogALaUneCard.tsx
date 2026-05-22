import { Newspaper, ChevronRight } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

const ARTICLES = [
  {
    title: 'Le marché crypto reprend des couleurs après la décision de la Fed',
    tag: 'Macro',
    readTime: '4 min',
    cover: 'linear-gradient(135deg, #1C1C1E 0%, #6155F5 100%)',
  },
  {
    title: 'Vancelian lance une nouvelle offre exclusive immobilière',
    tag: 'Communiqué',
    readTime: '3 min',
    cover: 'linear-gradient(135deg, #00C3D0 0%, #6155F5 100%)',
  },
  {
    title: 'Comment diversifier votre portefeuille en 2026',
    tag: 'Analyse',
    readTime: '6 min',
    cover: 'linear-gradient(135deg, #FF8D28 0%, #FF383C 100%)',
  },
]

/// Mock du module `blog_a_la_une` (article hero + liste de news).
/// La carte hero (1ère news) a un cover plus grand, les autres sont des
/// rangées compactes en dessous.
export function MockBlogALaUneCard() {
  const [hero, ...rest] = ARTICLES

  return (
    <div
      style={{
        margin: `${spacing.s2}px ${spacing.lg}px`,
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        overflow: 'hidden',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.05)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `${spacing.s3}px ${spacing.s4}px 0`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.s2 }}>
          <Newspaper size={18} color={colors.indigo} />
          <div style={{ ...typoStyle(typo.sectionTitle), color: colors.textPrimary }}>
            News à la Une
          </div>
        </div>
        <ChevronRight size={20} color={colors.textMuted} />
      </div>

      <div style={{ padding: `${spacing.s3}px ${spacing.s4}px` }}>
        {/* Hero article */}
        <div
          style={{
            borderRadius: 12,
            overflow: 'hidden',
            marginBottom: spacing.s3,
          }}
        >
          <div
            style={{
              height: 130,
              background: hero.cover,
              position: 'relative',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: spacing.s3,
                left: spacing.s3,
                padding: '4px 10px',
                borderRadius: 12,
                backgroundColor: 'rgba(255,255,255,0.92)',
                ...typoStyle(typo.labelEmphasized),
                color: colors.indigo,
              }}
            >
              {hero.tag}
            </div>
          </div>
          <div style={{ paddingTop: spacing.s3 }}>
            <div
              style={{
                ...typoStyle(typo.itemPrimary),
                color: colors.textPrimary,
              }}
            >
              {hero.title}
            </div>
            <div
              style={{
                ...typoStyle(typo.bodySmRegular),
                color: colors.textSecondary,
                marginTop: 4,
              }}
            >
              {hero.readTime} · {hero.tag}
            </div>
          </div>
        </div>

        {/* Liste compacte */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {rest.map((a, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                gap: spacing.s3,
                padding: `${spacing.s3}px 0`,
                borderTop: `1px solid ${colors.separatorOpaque}`,
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 10,
                  background: a.cover,
                  flexShrink: 0,
                }}
              />
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  gap: 2,
                }}
              >
                <div
                  style={{
                    ...typoStyle(typo.itemPrimary),
                    color: colors.textPrimary,
                  }}
                >
                  {a.title}
                </div>
                <div
                  style={{
                    ...typoStyle(typo.bodySmRegular),
                    color: colors.textSecondary,
                  }}
                >
                  {a.readTime} · {a.tag}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

import { Heart, Share2 } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'
import { MockAppTopNavBar } from '../mocks/AppTopNavBar'
import { MockTableInformationModule } from '../mocks/TableInformationModule'
import { MockFaqModule } from '../mocks/FaqModule'

/// Composition page **Page projet (offre exclusive)** (id=`projet`).
/// Hero photographique (60 % hauteur) avec topnav glass → carte projet
/// (titre + tag rendement) → modules : Table info + FAQ.
/// Pas de tab bar (on est en niveau 2).
export function ProjetPagePreview() {
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: colors.pageBackground,
        position: 'relative',
        paddingBottom: spacing.s10,
      }}
    >
      {/* Hero image (60 % hauteur device) avec navbar superposée glass */}
      <div
        style={{
          position: 'relative',
          height: 360,
          background: 'linear-gradient(180deg, #1C1C1E 0%, #6155F5 100%)',
          padding: `${spacing.s2}px 0 0 0`,
          overflow: 'hidden',
        }}
      >
        <MockAppTopNavBar
          leading={{ kind: 'back' }}
          actions={[
            { icon: <Heart size={20} color={colors.textPrimary} /> },
            { icon: <Share2 size={20} color={colors.textPrimary} /> },
          ]}
          background="transparent"
        />
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            padding: spacing.lg,
            color: colors.white,
          }}
        >
          <div
            style={{
              alignSelf: 'flex-start',
              display: 'inline-block',
              padding: '4px 10px',
              borderRadius: 12,
              backgroundColor: 'rgba(255,255,255,0.25)',
              ...typoStyle(typo.labelEmphasized),
              color: colors.white,
              marginBottom: spacing.s2,
            }}
          >
            Real estate · Lyon
          </div>
          <div style={{ ...typoStyle(typo.headerPrimary), color: colors.white }}>
            Hôtel particulier — Croix Rousse
          </div>
          <div
            style={{
              ...typoStyle(typo.bodyEmphasized),
              color: 'rgba(255,255,255,0.9)',
              marginTop: 4,
            }}
          >
            Rendement cible 7,2 % · 24 mois
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.s2, marginTop: spacing.s2 }}>
        <MockTableInformationModule />
        <MockFaqModule />
      </div>
    </div>
  )
}

import { ChevronLeft, X } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

/// Mock visuel de `AppTopNavBar` (Flutter `app_top_nav_bar.dart`).
/// Hauteur fixe 60 px (Figma `TopAppBar`), gauche optionnelle (back / profile / close),
/// titre centré optionnel, actions droite optionnelles.
export type MockTopNavLeading =
  | { kind: 'back' }
  | { kind: 'close' }
  | { kind: 'profile'; initials?: string }
  | { kind: 'none' }

export function MockAppTopNavBar({
  leading = { kind: 'profile', initials: 'JA' },
  title,
  actions = [],
  background = colors.pageBackground,
  showProfileDot = false,
}: {
  leading?: MockTopNavLeading
  title?: string
  actions?: Array<{ icon: React.ReactNode; showDot?: boolean }>
  background?: string
  showProfileDot?: boolean
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 60,
        backgroundColor: background,
        paddingLeft: spacing.lg,
        paddingRight: spacing.lg,
        position: 'relative',
      }}
    >
      <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
        {leading.kind === 'back' && <Disk><ChevronLeft size={22} color={colors.textPrimary} /></Disk>}
        {leading.kind === 'close' && <Disk><X size={20} color={colors.textPrimary} /></Disk>}
        {leading.kind === 'profile' && (
          <ProfileAvatar initials={leading.initials ?? 'JA'} showDot={showProfileDot} />
        )}
      </div>
      {title ? (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              ...typoStyle(typo.headerAppbar),
              color: colors.textPrimary,
              maxWidth: 200,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {title}
          </div>
        </div>
      ) : null}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: spacing.s2,
        }}
      >
        {actions.map((a, idx) => (
          <Disk key={idx} dot={a.showDot}>
            {a.icon}
          </Disk>
        ))}
      </div>
    </div>
  )
}

function Disk({ children, dot }: { children: React.ReactNode; dot?: boolean }) {
  return (
    <div
      style={{
        position: 'relative',
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: colors.cardBackground,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.05)',
      }}
    >
      {children}
      {dot ? (
        <span
          style={{
            position: 'absolute',
            top: 2,
            right: 2,
            width: 10,
            height: 10,
            borderRadius: 5,
            backgroundColor: '#4FC3F7',
          }}
        />
      ) : null}
    </div>
  )
}

function ProfileAvatar({ initials, showDot }: { initials: string; showDot?: boolean }) {
  return (
    <div
      style={{
        position: 'relative',
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: 'rgba(0,0,0,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: colors.textPrimary,
        fontFamily: '"Inter", system-ui, sans-serif',
        fontWeight: 600,
        fontSize: 14,
      }}
    >
      {initials}
      {showDot ? (
        <span
          style={{
            position: 'absolute',
            top: 2,
            right: 2,
            width: 10,
            height: 10,
            borderRadius: 5,
            backgroundColor: '#4FC3F7',
          }}
        />
      ) : null}
    </div>
  )
}

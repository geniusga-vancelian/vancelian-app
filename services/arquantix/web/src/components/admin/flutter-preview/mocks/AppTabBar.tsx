import {
  Home,
  Briefcase,
  TrendingUp,
  User,
  Search,
  type LucideIcon,
} from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

export type MockTabItem = {
  iconKey: string
  label: string
}

const ICON_MAP: Record<string, LucideIcon> = {
  home: Home,
  briefcase: Briefcase,
  trending: TrendingUp,
  user: User,
  search: Search,
}

/// Mock visuel de `AppTabBar` Flutter (iOS-style glass tab bar).
/// - 54 px de haut, radius 40, fond glassmorphism (translucide gris-bleu).
/// - Pill blanche sous le tab actif (active = `selectedIndex`).
/// - Bouton circulaire d'action (search) à droite, séparé de 8 px.
export function MockAppTabBar({
  items,
  selectedIndex = 0,
  showAction = true,
  actionIconKey = 'search',
}: {
  items: MockTabItem[]
  selectedIndex?: number
  showAction?: boolean
  actionIconKey?: string
}) {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 8,
        left: 0,
        right: 0,
        padding: `0 ${spacing.s4}px`,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <div
        style={{
          flex: 1,
          height: 54,
          borderRadius: 40,
          backgroundColor: 'rgba(235, 235, 245, 0.7)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-around',
          padding: '0 6px',
          position: 'relative',
        }}
      >
        {items.map((item, idx) => {
          const Icon = ICON_MAP[item.iconKey] ?? Home
          const isActive = idx === selectedIndex
          return (
            <div
              key={`${item.label}-${idx}`}
              style={{
                position: 'relative',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 2,
                height: 46,
                margin: '0 2px',
                borderRadius: 22,
                backgroundColor: isActive ? colors.white : 'transparent',
                boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.05)' : undefined,
              }}
            >
              <Icon
                size={20}
                color={isActive ? colors.indigo : colors.textPrimary}
              />
              <div
                style={{
                  ...typoStyle(typo.navBarLabel),
                  color: isActive ? colors.indigo : colors.textPrimary,
                }}
              >
                {item.label}
              </div>
            </div>
          )
        })}
      </div>
      {showAction ? (
        <div
          style={{
            width: 52,
            height: 52,
            borderRadius: 26,
            backgroundColor: 'rgba(235, 235, 245, 0.7)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {(() => {
            const Icon = ICON_MAP[actionIconKey] ?? Search
            return <Icon size={20} color={colors.textPrimary} />
          })()}
        </div>
      ) : null}
    </div>
  )
}

export const DEFAULT_MAIN_TABS: MockTabItem[] = [
  { iconKey: 'home', label: 'Home' },
  { iconKey: 'briefcase', label: 'Offers' },
  { iconKey: 'trending', label: 'Markets' },
  { iconKey: 'user', label: 'Profile' },
]

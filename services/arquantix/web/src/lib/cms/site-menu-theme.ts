import { prisma } from '@/lib/prisma'
import type { TopnavSurface } from '@/hooks/useTopnavSurfaceObserver'
import {
  menuThemeJsonSchema,
  normalizeMenuThemeJson,
  parseMenuThemeStorage,
  type MenuThemeJson,
  type MenuThemeSurfaceOverrides,
} from '@/lib/cms/menuThemeStorage'

export type TopnavPalette = {
  background: string
  borderBottom: string
  linkColor: string
  underlineColor: string
  textLinkColor: string
  logoInvert: boolean
  ctaBg: string
  ctaFg: string
  ctaHoverBg: string
  /** Variante bouton DS (`default` sur fond clair, `darkPrimary` sur fond sombre / hero). */
  ctaVariant: 'default' | 'darkPrimary'
}

const BASE_TOPNAV_PALETTES: Record<TopnavSurface, TopnavPalette> = {
  transparent: {
    background: 'transparent',
    borderBottom: '1px solid rgba(255, 255, 255, 0.18)',
    linkColor: 'var(--v-dark-fg)',
    underlineColor: 'var(--v-dark-fg)',
    textLinkColor: 'var(--v-dark-fg)',
    logoInvert: true,
    ctaBg: 'var(--v-dark-fg)',
    ctaFg: 'var(--v-fg)',
    ctaHoverBg: 'var(--v-card)',
    ctaVariant: 'darkPrimary',
  },
  solid: {
    background: 'var(--v-bg)',
    borderBottom: '1px solid var(--v-fg-10)',
    linkColor: 'var(--v-fg)',
    underlineColor: 'var(--v-fg)',
    textLinkColor: 'var(--v-terracotta)',
    logoInvert: false,
    ctaBg: 'var(--v-fg)',
    ctaFg: 'var(--v-dark-fg)',
    ctaHoverBg: 'color-mix(in srgb, var(--v-fg) 82%, var(--v-dark-fg))',
    ctaVariant: 'default',
  },
  warm: {
    background: 'var(--v-card-warm)',
    borderBottom: '1px solid color-mix(in srgb, var(--v-fg) 6%, transparent)',
    linkColor: 'var(--v-fg)',
    underlineColor: 'var(--v-fg)',
    textLinkColor: 'var(--v-terracotta)',
    logoInvert: false,
    ctaBg: 'var(--v-fg)',
    ctaFg: 'var(--v-dark-fg)',
    ctaHoverBg: 'color-mix(in srgb, var(--v-fg) 82%, var(--v-dark-fg))',
    ctaVariant: 'default',
  },
  dark: {
    background: 'var(--v-dark-bg)',
    borderBottom: '1px solid color-mix(in srgb, var(--v-dark-fg) 8%, transparent)',
    linkColor: 'var(--v-dark-fg)',
    underlineColor: 'var(--v-dark-fg)',
    textLinkColor: 'var(--v-dark-fg)',
    logoInvert: true,
    ctaBg: 'var(--v-dark-fg)',
    ctaFg: 'var(--v-fg)',
    ctaHoverBg: 'color-mix(in srgb, var(--v-dark-fg) 12%, white)',
    ctaVariant: 'darkPrimary',
  },
}

function mergeSurfacePalette(
  base: TopnavPalette,
  overrides: MenuThemeSurfaceOverrides | undefined,
): TopnavPalette {
  if (!overrides) return base
  return {
    ...base,
    ...overrides,
    logoInvert: base.logoInvert,
    ctaVariant: base.ctaVariant,
  }
}

export function buildTopnavPalettes(theme?: MenuThemeJson | null): Record<TopnavSurface, TopnavPalette> {
  const surfaces = theme?.surfaces
  return {
    transparent: mergeSurfacePalette(BASE_TOPNAV_PALETTES.transparent, surfaces?.transparent),
    solid: mergeSurfacePalette(BASE_TOPNAV_PALETTES.solid, surfaces?.solid),
    warm: mergeSurfacePalette(BASE_TOPNAV_PALETTES.warm, surfaces?.warm),
    dark: mergeSurfacePalette(BASE_TOPNAV_PALETTES.dark, surfaces?.dark),
  }
}

export function getDefaultMenuThemeJson(): MenuThemeJson {
  return menuThemeJsonSchema.parse({ version: 1 })
}

export async function getSiteMenuTheme(): Promise<MenuThemeJson> {
  try {
    const menu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      select: { themeJson: true },
    })
    if (!menu?.themeJson) {
      return getDefaultMenuThemeJson()
    }
    return parseMenuThemeStorage(menu.themeJson)
  } catch {
    return getDefaultMenuThemeJson()
  }
}

export function serializeMenuThemeForSave(theme: MenuThemeJson): MenuThemeJson {
  return normalizeMenuThemeJson(menuThemeJsonSchema.parse(theme))
}

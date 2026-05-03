/**
 * Utilitaires de thème pour la page Design System « Hermès ».
 *
 * Hermès n'a pas de mode dark/light comme Cursor. La page expose deux fonds :
 *   - **beige** : `#fcf7f1` (par défaut, identique au site).
 *   - **dark**  : `#2e2d2d` (vue inversée, fond `dark-level-5`).
 *
 * On factorise ici les couleurs UI réutilisées par tous les modules de la
 * vitrine.
 */

export type HermesThemeMode = 'beige' | 'dark'

export const HERMES_THEME_BG: Record<HermesThemeMode, string> = {
  beige: '#fcf7f1',
  dark: '#2e2d2d',
}

export const HERMES_THEME_FG: Record<HermesThemeMode, string> = {
  beige: '#2e2d2d',
  dark: '#fcf7f1',
}

export const HERMES_THEME_CARD: Record<HermesThemeMode, string> = {
  beige: '#fffcf7',
  dark: '#1f1e1e',
}

export const HERMES_THEME_BORDER: Record<HermesThemeMode, string> = {
  beige: '#e2d8ce',
  dark: '#4a4949',
}

export const HERMES_THEME_MUTED: Record<HermesThemeMode, string> = {
  beige: '#696969',
  dark: '#cbcbcb',
}

export const HERMES_THEME_ACCENT: Record<HermesThemeMode, string> = {
  beige: '#9d2a1e',
  dark: '#9d2a1e',
}

export const HERMES_ACCENT = '#9d2a1e'

/* -------------------------------------------------------------------------- */
/*  HEX UTILS                                                                  */
/* -------------------------------------------------------------------------- */

export function parseHex(
  input: string,
): { r: number; g: number; b: number; a: number } | null {
  const hex = input.trim().replace(/^#/, '')
  if (![3, 4, 6, 8].includes(hex.length)) return null
  const expand = (s: string) => (s.length === 1 ? s + s : s)
  let r: string, g: string, b: string
  let a = 'ff'
  if (hex.length <= 4) {
    r = expand(hex[0]!)
    g = expand(hex[1]!)
    b = expand(hex[2]!)
    if (hex.length === 4) a = expand(hex[3]!)
  } else {
    r = hex.slice(0, 2)
    g = hex.slice(2, 4)
    b = hex.slice(4, 6)
    if (hex.length === 8) a = hex.slice(6, 8)
  }
  const ri = parseInt(r, 16)
  const gi = parseInt(g, 16)
  const bi = parseInt(b, 16)
  const ai = parseInt(a, 16) / 255
  if ([ri, gi, bi].some((n) => Number.isNaN(n))) return null
  return { r: ri, g: gi, b: bi, a: ai }
}

function srgbToLin(c: number): number {
  const v = c / 255
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
}

/** Renvoie noir/blanc pour rester lisible sur la couleur composée sur le thème. */
export function pickContrastColor(hex: string, themeBg: string): string {
  const rgba = parseHex(hex)
  if (!rgba) return '#000'
  const bg = parseHex(themeBg) ?? { r: 252, g: 247, b: 241, a: 1 }
  const a = rgba.a
  const r = Math.round(rgba.r * a + bg.r * (1 - a))
  const g = Math.round(rgba.g * a + bg.g * (1 - a))
  const b = Math.round(rgba.b * a + bg.b * (1 - a))
  const luminance =
    0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b)
  return luminance > 0.55 ? '#2e2d2d' : '#fcf7f1'
}

export function extractAlphaPercent(hex: string): number | null {
  const parsed = parseHex(hex)
  if (!parsed) return null
  if (parsed.a >= 0.999) return null
  return Math.round(parsed.a * 100)
}

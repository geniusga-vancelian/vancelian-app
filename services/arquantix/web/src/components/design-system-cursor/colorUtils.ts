export type ThemeMode = 'light' | 'dark'

export const THEME_BG: Record<ThemeMode, string> = {
  light: '#f7f7f4',
  dark: '#14120b',
}

export const THEME_FG: Record<ThemeMode, string> = {
  light: '#26251e',
  dark: '#edecec',
}

export const THEME_CARD: Record<ThemeMode, string> = {
  light: '#f2f1ed',
  dark: '#1b1913',
}

export const THEME_BORDER: Record<ThemeMode, string> = {
  light: '#26251e1a',
  dark: '#edecec1a',
}

export const THEME_MUTED: Record<ThemeMode, string> = {
  light: '#26251e99',
  dark: '#edecec99',
}

export const ACCENT = '#f54e00'

export function parseHex(
  input: string,
): { r: number; g: number; b: number; a: number } | null {
  const hex = input.trim().replace(/^#/, '')
  if (![3, 4, 6, 8].includes(hex.length)) return null
  const expand = (s: string) => (s.length === 1 ? s + s : s)
  let r: string, g: string, b: string, a = 'ff'
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

/**
 * Renvoie une couleur de texte lisible (noir ou blanc cassé) sur un fond
 * donné, en composant l'alpha sur le fond du thème.
 */
export function pickContrastColor(hex: string, themeBg: string): string {
  const rgba = parseHex(hex)
  if (!rgba) return '#000'
  const bg = parseHex(themeBg) ?? { r: 247, g: 247, b: 244, a: 1 }
  const a = rgba.a
  const r = Math.round(rgba.r * a + bg.r * (1 - a))
  const g = Math.round(rgba.g * a + bg.g * (1 - a))
  const b = Math.round(rgba.b * a + bg.b * (1 - a))
  const luminance =
    0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b)
  return luminance > 0.55 ? '#26251e' : '#f7f7f4'
}

export function extractAlphaPercent(hex: string): number | null {
  const parsed = parseHex(hex)
  if (!parsed) return null
  if (parsed.a >= 0.999) return null
  return Math.round(parsed.a * 100)
}

/**
 * Tokens du **DS Flutter** (couleurs, typo, spacing) portés en TS pour la
 * preview HTML/CSS du builder admin (`/admin/flutter` split-screen).
 *
 * Source : `services/arquantix/mobile/lib/design_system/atoms/app_colors.dart`,
 * `app_typography.dart`, `app_spacing.dart`.
 *
 * Ces constantes ne sont **pas** la source de vérité du DS — c'est le Dart qui
 * l'est. Si le DS Flutter évolue, il faut resync ce fichier à la main.
 * Acceptable pour une preview admin (cf. plan : trade-off explicite).
 */

import type { CSSProperties } from 'react'

export const colors = {
  // Base palette
  red: '#FF4245',
  mint: '#00DAC3',
  orange: '#FF9230',
  yellow: '#FFD600',
  green: '#30D158',
  teal: '#00D2E0',
  cyan: '#3CD3FE',
  actionPrimaryBlue: '#007AFF',
  blue: '#0091FF',
  /// CTA marque (#6155F5) — Figma `primary`.
  indigo: '#6155F5',
  iosChromeBackground: '#F2F2F7',
  purple: '#DB34F2',
  pink: '#FF375F',
  brown: '#B78A66',

  // Gray scale
  black: '#000000',
  gray: '#8E8E93',
  gray2: '#636366',
  gray3: '#48484A',
  gray4: '#3A3A3C',
  gray5: '#2C2C2E',
  gray6: '#1C1C1E',
  white: '#FFFFFF',

  // Semantic aliases (light theme)
  textPrimary: '#000000',
  textSecondary: '#64748B',
  textMuted: '#8E8E93',
  accent: '#6155F5',
  accentLight: '#EFEEFE',
  pageBackground: '#F5F5F5',
  cardBackground: '#FFFFFF',
  placeholderBg: '#E2E8F0',
  placeholderIcon: '#94A3B8',
  navBarBackground: '#FFFFFF',
  navBarActivePill: '#F1F5F9',
  navBarInactive: '#64748B',
  border: '#E5E7EB',
  separatorOpaque: '#E5E7EB',
  errorBackground: '#FEF2F2',
  errorText: '#991B1B',
  progressTrackLight: '#E5E5EA',

  // Semantic palette (Figma)
  semanticNeutral: '#AEAEB2',
  semanticActive: '#00C3D0',
  semanticActiveLight: '#E5F9FA',
  semanticInfo: '#0088FF',
  semanticInfoLight: '#E5F3FF',
  semanticWarning: '#FF8D28',
  semanticWarningLight: '#FFF4E9',
  semanticDanger: '#FF383C',
  semanticDangerLight: '#FFEBEB',
  semanticPositive: '#34C759',
  semanticPositiveLight: '#EBF9EE',
  semanticNegative: '#FF2D55',
  semanticNegativeLight: '#FFEAEE',
} as const

/// Marques crypto (atomes communs) — `cryptoAssetBrand` Dart.
export const cryptoBrand: Record<string, string> = {
  EUR: '#2196F3',
  BTC: '#FF9230',
  ETH: '#627EEA',
  USDT: '#26A17B',
  USDC: '#2775CA',
  XRP: '#23292F',
  SOL: '#9945FF',
  BNB: '#F3BA2F',
  ADA: '#0033AD',
  AVAX: '#E84142',
  DOGE: '#C2A633',
  DOT: '#E6007A',
  LINK: '#2A5ADA',
  TRX: '#EF0027',
}

export function cryptoBrandColor(ticker: string): string {
  return cryptoBrand[ticker.toUpperCase()] ?? colors.textMuted
}

/// Échelle d'espacement (base unit = 4px) — port `app_spacing.dart`.
export const spacing = {
  s0: 0,
  s1: 4,
  s2: 8,
  s3: 12,
  s4: 16,
  s5: 20,
  s6: 24,
  s7: 28,
  s8: 32,
  s10: 40,
  s12: 48,
  s16: 64,
  s20: 80,
  s24: 96,

  // Legacy aliases (utilisés partout dans le DS Flutter)
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  pageEdge: 16,
} as const

/// Tokens typographiques portés depuis `AppTypography` Dart (Inter).
/// Forme : { fontSize, fontWeight, letterSpacing, lineHeight (px) }.
export type TypoToken = {
  fontSize: number
  fontWeight: number
  letterSpacing?: number
  /// Hauteur de ligne en **px** (Flutter exprime height en multiplicateur du fontSize ;
  /// ici on stocke directement la valeur calculée pour simplifier l'usage CSS).
  lineHeight: number
  fontStyle?: 'italic' | 'normal'
}

export const typo = {
  // ── Page ──
  /// Page header (34/700/-0.136/41)
  headerPrimary: {
    fontSize: 34,
    fontWeight: 700,
    letterSpacing: -0.136,
    lineHeight: 41,
  },
  /// App bar title (20/600/-0.45/25)
  headerAppbar: {
    fontSize: 20,
    fontWeight: 600,
    letterSpacing: -0.45,
    lineHeight: 25,
  },
  headerSecondary: {
    fontSize: 22,
    fontWeight: 600,
    letterSpacing: -0.35,
    lineHeight: 26,
  },
  headerTertiary: {
    fontSize: 22,
    fontWeight: 700,
    letterSpacing: -0.26,
    lineHeight: 28,
  },
  display: {
    fontSize: 65.76,
    fontWeight: 700,
    letterSpacing: -1.973,
    lineHeight: 72,
  },
  navBarLabel: {
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: 0,
    lineHeight: 12,
  },

  // ── Label (11px) ──
  labelRegular: {
    fontSize: 11,
    fontWeight: 400,
    letterSpacing: 0.06,
    lineHeight: 13,
  },
  labelEmphasized: {
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: 0.06,
    lineHeight: 13,
  },

  // ── Amount ──
  amountPrimary: {
    fontSize: 34,
    fontWeight: 700,
    letterSpacing: 34 * -0.004,
    lineHeight: 41,
  },
  amountSecondary: {
    fontSize: 22,
    fontWeight: 700,
    letterSpacing: -0.26,
    lineHeight: 28,
  },
  amountTertiary: {
    fontSize: 14,
    fontWeight: 600,
    letterSpacing: 0,
    lineHeight: 16,
  },

  // ── Section ──
  title1: {
    fontSize: 24,
    fontWeight: 700,
    letterSpacing: -0.45,
    lineHeight: 30,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 700,
    letterSpacing: -0.45,
    lineHeight: 25,
  },

  // ── Item ──
  itemPrimary: {
    fontSize: 15,
    fontWeight: 600,
    letterSpacing: -0.23,
    lineHeight: 20,
  },
  itemSecondary: {
    fontSize: 15,
    fontWeight: 400,
    letterSpacing: -0.23,
    lineHeight: 20,
  },
  itemSupporting: {
    fontSize: 14,
    fontWeight: 400,
    letterSpacing: -0.08,
    lineHeight: 18,
  },
  itemSupportingBd: {
    fontSize: 14,
    fontWeight: 600,
    letterSpacing: -0.08,
    lineHeight: 18,
  },

  // ── Body (17px) ──
  bodyRegular: {
    fontSize: 17,
    fontWeight: 400,
    letterSpacing: -0.43,
    lineHeight: 22,
  },
  bodyEmphasized: {
    fontSize: 17,
    fontWeight: 600,
    letterSpacing: -0.43,
    lineHeight: 22,
  },

  // ── Body SM (13px) ──
  bodySmRegular: {
    fontSize: 13,
    fontWeight: 400,
    letterSpacing: -0.08,
    lineHeight: 18,
  },
  bodySmEmphasized: {
    fontSize: 13,
    fontWeight: 600,
    letterSpacing: -0.08,
    lineHeight: 18,
  },

  // ── Button ──
  buttonEmphasized: {
    fontSize: 16,
    fontWeight: 600,
    letterSpacing: -0.31,
    lineHeight: 21,
  },
} as const satisfies Record<string, TypoToken>

/// Helpers React → CSS style object pour appliquer un token typo en JSX.
export function typoStyle(token: TypoToken): CSSProperties {
  return {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: `${token.fontSize}px`,
    fontWeight: token.fontWeight,
    lineHeight: `${token.lineHeight}px`,
    letterSpacing:
      token.letterSpacing !== undefined ? `${token.letterSpacing}px` : undefined,
    fontStyle: token.fontStyle ?? 'normal',
  }
}

/// Dimensions cibles "device frame" pour la preview (iPhone 13 mini).
export const deviceFrame = {
  width: 375,
  height: 812,
  /// Radius extérieur du device.
  radius: 44,
  /// Couleur du chassis (bezel).
  chassis: '#1C1C1E',
} as const

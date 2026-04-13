/**
 * Couleurs alignées sur le design system Flutter (`AppColors`).
 * Source : `services/arquantix/mobile/lib/design_system/atoms/app_colors.dart`
 *
 * Utilisation :
 * - TS : `FlutterAppColors.indigo`, `flutterColor('cyan')`
 * - CSS : `var(--flutter-indigo)`
 * - Tailwind : `bg-flutter-indigo`, `text-flutter-semantic-positive`, etc.
 */
export const FlutterAppColors = {
  // ── Palette designer (base) ──
  red: '#FF4245',
  mint: '#00DAC3',
  orange: '#FF9230',
  yellow: '#FFD600',
  green: '#30D158',
  teal: '#00D2E0',
  cyan: '#3CD3FE',
  blue: '#0091FF',
  indigo: '#6B5DFF',
  purple: '#DB34F2',
  pink: '#FF375F',
  brown: '#B78A66',

  // ── Échelle de gris (app) ──
  black: '#000000',
  gray: '#8E8E93',
  gray2: '#636366',
  gray3: '#48484A',
  gray4: '#3A3A3C',
  gray5: '#2C2C2E',
  gray6: '#1C1C1E',
  white: '#FFFFFF',

  // ── Sémantique (tokens Figma dans le DS Flutter) ──
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

  // ── Alias UI app ──
  accentLight: '#EFEEFE',
  pageBackground: '#F5F5F5',
  appBorder: '#E5E7EB',
  appTextPrimary: '#000000',
  appTextSecondary: '#64748B',
  appTextMuted: '#8E8E93',
} as const;

export type FlutterAppColorKey = keyof typeof FlutterAppColors;

export function flutterColor(key: FlutterAppColorKey): string {
  return FlutterAppColors[key];
}

/** Clés groupées pour la vitrine DS */
export const FlutterColorGroups = {
  designer: [
    'red',
    'mint',
    'orange',
    'yellow',
    'green',
    'teal',
    'cyan',
    'blue',
    'indigo',
    'purple',
    'pink',
    'brown',
  ] as const satisfies readonly FlutterAppColorKey[],

  grayScale: ['black', 'gray', 'gray2', 'gray3', 'gray4', 'gray5', 'gray6', 'white'] as const satisfies readonly FlutterAppColorKey[],

  semantic: [
    'semanticNeutral',
    'semanticActive',
    'semanticActiveLight',
    'semanticInfo',
    'semanticInfoLight',
    'semanticWarning',
    'semanticWarningLight',
    'semanticDanger',
    'semanticDangerLight',
    'semanticPositive',
    'semanticPositiveLight',
    'semanticNegative',
    'semanticNegativeLight',
  ] as const satisfies readonly FlutterAppColorKey[],

  ui: ['accentLight', 'pageBackground', 'appBorder', 'appTextPrimary', 'appTextSecondary', 'appTextMuted'] as const satisfies readonly FlutterAppColorKey[],
};

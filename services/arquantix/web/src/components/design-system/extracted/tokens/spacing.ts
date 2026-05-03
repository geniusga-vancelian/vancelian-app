import { ARQUANTIX_CONTENT_TEXT_MAX_PX } from '@/lib/design/contentMaxWidth'

export const figmaDsSpacing = {
  '0': '0',
  '1': '4px',
  '2': '8px',
  '3': '10px',
  '4': '12px',
  '5': '20px',
  '6': '24px',
  '7': '30px',
  '8': '32px',
  '10': '40px',
  '16': '64px',
  '24': '128px',
  gap: {
    xs: '8px',
    sm: '10px',
    md: '24px',
    lg: '30px',
    xl: '32px',
    '2xl': '40px',
    '3xl': '64px',
  },
  padding: {
    xs: '4px',
    sm: '12px',
    md: '20px',
    lg: '24px',
    xl: '30px',
    '2xl': '64px',
  },
  height: {
    menu: '64px',
    statCard: '76px',
    sectionImage: '400px',
    avatar: '48px',
  },
  width: {
    container: '1280px',
    content: '1152px',
    text: `${ARQUANTIX_CONTENT_TEXT_MAX_PX}px`,
    narrowText: '746px',
  },
} as const

export type FigmaDsSpacingToken = typeof figmaDsSpacing

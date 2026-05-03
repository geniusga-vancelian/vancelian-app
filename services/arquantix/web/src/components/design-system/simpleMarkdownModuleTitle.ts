import { figmaDsTypography } from '@/components/design-system/extracted/tokens/typography'

/**
 * Typographie DS — titre du module **SimpleMarkdownContentModule** (Vault Builder, site web).
 *
 * Figma : Avenir Heavy (800), 40px, line-height 110 %, letter-spacing −1 %, alignement horizontal center.
 *
 * Les valeurs numériques correspondent à `figmaDsTypography.fontSize.xl` (40px),
 * `lineHeight.tight` (1.1 = 110 %) et `letterSpacing.minus1PercentOfEm` (−1 %).
 * Classes Tailwind en littéraux pour compatibilité avec le scanner Tailwind.
 */
export const SIMPLE_MARKDOWN_MODULE_TITLE_TYPO =
  `${figmaDsTypography.fontFamily.heavy} text-[40px] leading-[1.1] tracking-[-0.01em] not-italic text-center text-black`

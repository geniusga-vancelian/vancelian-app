import { figmaDsTypography } from '@/components/design-system/extracted/tokens/typography'

/**
 * Texte d’introduction sous le titre des modules Vault (page détail offre) :
 * Avenir Roman, **18px** (`figmaDsTypography.fontSize.md`), interligne confort, gris.
 */
export const VAULT_MODULE_DESCRIPTION_TYPO =
  `${figmaDsTypography.fontFamily.roman} text-[18px] leading-relaxed text-neutral-600`

/**
 * Corps Markdown (SimpleMarkdownContentModule) : même corps 18px / Avenir Roman,
 * couleur plus contrastée pour la lecture longue.
 */
export const VAULT_MODULE_MARKDOWN_BODY_TYPO =
  `${figmaDsTypography.fontFamily.roman} text-[18px] leading-relaxed text-neutral-800`

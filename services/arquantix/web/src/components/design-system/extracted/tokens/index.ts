import { figmaDsColors } from './colors'
import { figmaDsTypography } from './typography'
import { figmaDsSpacing } from './spacing'
import { figmaDsBorderRadius } from './border-radius'

export { figmaDsColors, type FigmaDsColorToken } from './colors'
export {
  figmaDsPageCanvasHex,
  figmaDsPageCanvasBgClassName,
  figmaDsBodyRootClassName,
  figmaDsSiteShellLightClassName,
} from './surfaces'
export {
  figmaDsTypography,
  figmaDsButtonLabelClassName,
  figmaDsParagraphLargeBoldClassName,
  figmaDsFeaturedPostSidebarTitleClassName,
  figmaDsParagraphLargeClassName,
  figmaDsLinksClassName,
  figmaDsParagraphClassName,
  figmaDsParagraphStackGapClassName,
  figmaDsTagClassName,
  figmaDsCategoryPillContainerClassName,
  figmaDsLabelClassName,
  figmaDsLabelEmphasizedSmClassName,
  figmaDsHeavyOblique24ClassName,
  figmaDsArticleQuoteTextClassName,
  figmaDsArticleQuoteAuthorClassName,
  figmaDsArticleQuoteContainerClassName,
  figmaDsArticleQuoteIconClassName,
  type FigmaDsTypographyToken,
} from './typography'
export { figmaDsSpacing, type FigmaDsSpacingToken } from './spacing'
export { figmaDsBorderRadius, type FigmaDsBorderRadiusToken } from './border-radius'

export const figmaDsTokens = {
  colors: figmaDsColors,
  typography: figmaDsTypography,
  spacing: figmaDsSpacing,
  borderRadius: figmaDsBorderRadius,
  pageCanvasHex: figmaDsColors.background.light,
} as const

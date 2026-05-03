import { figmaDsTypography } from '@/components/design-system/extracted/tokens/typography'

/**
 * Module Funding — page détail offre (Figma redlines).
 *
 * - **Cartes Taux / Total** : padding 40×24px ; libellé « Paragraph Large », valeur « Title small » ; gap 16px.
 * - **Bloc chiffre (Financé)** : padding **40px** tout autour ; ligne Funded | % en « Title small » ; **16px** fixes puis barre
 *   ([Figma](https://www.figma.com/design/Biz0934nmynFPUuo5jysBb/Arquantix-Branding?node-id=319-4776)), barre en bas alignée aux valeurs Taux/Total.
 */

/** Figma « Paragraph Large » — libellés Rate / Total uniquement. Avenir Roman 400, 18px, interligne 160 %, tracking 0 %. */
export const OFFER_FUNDING_PARAGRAPH_LARGE_TYPO =
  `${figmaDsTypography.fontFamily.roman} text-[18px] font-normal leading-[1.6] tracking-normal text-black`

/** Figma « Title small » — valeurs Taux/Total, et **ligne entière** du bloc chiffre (Funded + %). Avenir Heavy 800, 24px, interligne 110 %, tracking −1 %. */
export const OFFER_FUNDING_TITLE_SMALL_TYPO =
  `${figmaDsTypography.fontFamily.heavy} text-[24px] font-extrabold leading-[1.1] tracking-[-0.01em] text-black`

/** Variante taille supérieure (même graisse / tracking relatif). */
export const OFFER_FUNDING_TITLE_LARGE_TYPO =
  `${figmaDsTypography.fontFamily.heavy} text-[32px] font-extrabold leading-[1.1] tracking-[-0.01em] text-black`

/** Padding cartes Taux / Total : 40px horizontal, 24px vertical. */
export const OFFER_FUNDING_CARD_PADDING_CLASS = 'px-10 py-6'

/** Padding bloc chiffre (Financé) : 40px de tous les côtés (Figma « Bloc chiffre »). */
export const OFFER_FUNDING_BLOC_CHIFFRE_PADDING_CLASS = 'p-10'

/** Espacement fixe 16px entre libellé et valeur (cartes Taux / Total) ; barre Financé utilise un séparateur `h-4` équivalent. */
export const OFFER_FUNDING_CARD_INNER_GAP_CLASS = 'gap-4'

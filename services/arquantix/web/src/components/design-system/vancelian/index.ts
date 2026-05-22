/**
 * Vancelian Design System — composants atomiques & molécules.
 *
 * Tous les composants `V*` ici sont des **implémentations canoniques** des
 * patterns Vancelian (voir `vancelian-design-system/project/components/`).
 *
 * Doctrine :
 * - Ne jamais introduire de couleur hardcoded en dehors des tokens `--v-*` /
 *   classes `v-*` ou des hex officiels du DS (#141208 final-cta, #8E867A
 *   eyebrow dark, #EDECEC body dark).
 * - Ne jamais réimplémenter ces atomes dans une section — toujours les
 *   composer depuis ce barrel.
 * - Garder l'API minimale et alignée sur la spec HTML/CSS du pack handoff.
 */

export { VEyebrow } from './VEyebrow'
export type { VEyebrowProps } from './VEyebrow'

export { VEditorialTitle } from './VEditorialTitle'
export type { VEditorialTitleProps, VEditorialTitleSize } from './VEditorialTitle'

export { VSectionHeader } from './VSectionHeader'
export type { VSectionHeaderProps } from './VSectionHeader'

export { VTcard } from './VTcard'
export type { VTcardProps } from './VTcard'

export { VProductCard } from './VProductCard'
export type { VProductCardProps, VProductCardFeature } from './VProductCard'

export { VFinalCta } from './VFinalCta'
export type { VFinalCtaProps, VFinalCtaButton } from './VFinalCta'

export { VProofStats } from './VProofStats'
export type { VProofStatsProps, VProofStat } from './VProofStats'

export { VHero } from './VHero'
export type { VHeroProps, VHeroCta } from './VHero'

export { VHeroTypewriter } from './VHeroTypewriter'
export type { VHeroTypewriterProps } from './VHeroTypewriter'

export { VProofPress } from './VProofPress'
export type { VProofPressProps, VProofPressItem } from './VProofPress'

export { VOfferCard } from './VOfferCard'
export type { VOfferCardProps } from './VOfferCard'

export { VJourney } from './VJourney'
export type { VJourneyProps, VJourneyCta } from './VJourney'

export { VIosNotif } from './VIosNotif'
export type { VIosNotifProps } from './VIosNotif'

export { VSecurity } from './VSecurity'
export type { VSecurityProps, VSecurityPoint, VSecurityLogo } from './VSecurity'

export { VCmsMedia } from './VCmsMedia'
export type { VCmsMediaProps } from './VCmsMedia'

// Tokens TS (déjà créés en Phase 1)
export {
  vancelianColors,
  vancelianFonts,
  vancelianWeights,
  vancelianSpacing,
  vancelianRadius,
  vancelianShadows,
  vancelianMotion,
} from './tokens'
export type {
  VancelianColorToken,
  VancelianSpacingToken,
  VancelianRadiusToken,
} from './tokens'

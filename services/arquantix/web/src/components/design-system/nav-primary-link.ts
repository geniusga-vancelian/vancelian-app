import { figmaDsLinksClassName } from '@/components/design-system/extracted/tokens/typography'

/**
 * Typographie DS — **Links** (barre de navigation principale).
 *
 * Figma : Avenir Heavy (800), 16px, line-height 100%, letter-spacing 0%.
 * Source unique : {@link figmaDsLinksClassName} (`extracted/tokens/typography`).
 */
export const NAV_PRIMARY_LINK_TYPO = figmaDsLinksClassName

/**
 * Titres des lignes du **méga-menu** (panneau blanc) : même spec **Links Heavy** que la barre primaire.
 * Couleur du texte : appliquer côté composant (ex. `text-[#272727]` ou `text-neutral-900`).
 */
export const MEGA_MENU_ITEM_TITLE_TYPO = NAV_PRIMARY_LINK_TYPO

/**
 * Cadre des entrées menu (Figma : frame « Link » auto-layout, ex. Home actif).
 * Padding 8px / 12px (`py-2` / `px-3`), rayon **10px** sur les quatre coins.
 */
export const NAV_MENU_LINK_FRAME =
  "inline-flex items-center justify-center rounded-[10px] px-3 py-2 transition-colors";

/** État actif : fond noir, texte blanc (spec Figma lien sélectionné). */
export const NAV_MENU_LINK_ACTIVE_SURFACE = "bg-black text-white";

/**
 * Taille du déclencheur rond (sélecteur de langue) : même hauteur que les boutons du rail
 * droit (`py-2` + typo 16px `leading-none` + bordure 1px des variantes outline).
 */
export const NAV_RAIL_CIRCLE_TRIGGER_CLASS =
  "h-[34px] w-[34px] min-h-[34px] min-w-[34px]";

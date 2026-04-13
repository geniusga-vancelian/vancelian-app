/**
 * Calibrage mockup iPhone (viewBox 478×1024).
 *
 * - `IPHONE_PRO_APP_FRAME_SPEC` : aligné sur `public/iphone-pro-app-frame.png` (mode `frameSrc` PNG).
 * - `IPHONE_PRO_DEVICE_VECTOR_SPEC` : cadre vectoriel fin + grande zone écran (slides Offering, vitrine DS).
 */
export interface IphoneProAppFrameSpec {
  assetWidth: number;
  assetHeight: number;
  /** Zone écran : même x, y, w, h, radius pour masque SVG et clip HTML (pixel-perfect). */
  screenRect: { x: number; y: number; w: number; h: number; radius: number };
  /** Coins du boîtier pour le masque SVG (mode vectoriel). */
  outerRx: number;
  /** Dynamic Island (masque + pastille noire). */
  dynamicIsland: { x: number; y: number; w: number; h: number; r: number };
}

export const IPHONE_PRO_APP_FRAME_SRC = '/iphone-pro-app-frame.png' as const;

/** Calibrage du PNG opaque (legacy `frameSrc`). */
export const IPHONE_PRO_APP_FRAME_SPEC: IphoneProAppFrameSpec = {
  assetWidth: 478,
  assetHeight: 1024,
  screenRect: {
    x: 20,
    y: 54,
    w: 438,
    h: 956,
    radius: 36,
  },
  outerRx: 56,
  dynamicIsland: { x: 171, y: 26, w: 136, h: 37, r: 18.5 },
};

/**
 * Référence visuelle type Pro : bordure fine, écran occupe presque tout l’intérieur.
 * Utilisé par défaut quand le cadre est dessiné en SVG (sans PNG).
 */
export const IPHONE_PRO_DEVICE_VECTOR_SPEC: IphoneProAppFrameSpec = {
  assetWidth: 478,
  assetHeight: 1024,
  /**
   * y = 0 : la zone pixels (clip + masque + `<image>`) va jusqu’au haut du verre — pas de bande noire
   * « vide » sous le bord supérieur. (Réduire y>0 rétrécit le trou du masque = faux bandeau noir en haut.)
   * Marge basse : 1024 − 1016 = 8.
   */
  screenRect: {
    x: 6,
    y: 0,
    w: 466,
    h: 1016,
    /** Aligné sur la courbure intérieure du boîtier (outerRx 48, inset ~6 → ~42–46 en pratique). */
    radius: 46,
  },
  outerRx: 48,
  dynamicIsland: { x: 175, y: 21, w: 128, h: 31, r: 15.5 },
};

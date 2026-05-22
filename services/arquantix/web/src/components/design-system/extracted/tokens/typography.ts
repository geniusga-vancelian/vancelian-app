export const figmaDsTypography = {
  fontFamily: {
    heavy: "font-ui font-semibold",
    /**
     * Citation (corps) : Avenir **Heavy** + **italique** (Bold 800 + Italic), pas de face « Heavy Oblique » nommée.
     */
    heavyOblique: "font-ui font-semibold italic",
    /** Figma — auteur de citation (blog article) : Avenir Medium Oblique. */
    mediumOblique: "font-ui font-medium italic",
    roman: "font-ui font-normal",
    book: "font-ui font-normal",
  },
  fontSize: {
    xs: '14px',
    sm: '16px',
    md: '18px',
    lg: '24px',
    /** Atome SectionTitle `title` (Figma **Title**). */
    title: '32px',
    xl: '40px',
    '2xl': '56px',
  },
  lineHeight: {
    none: '0',
    tight: '1.1',
    normal: '1.6',
  },
  letterSpacing: {
    tight: '-1.12px',
    normal: '-0.4px',
    snug: '-0.24px',
    default: '-0.18px',
    /** Figma −1 % → `tracking-[-0.01em]` (atome Section title `module`, stats, etc.). */
    minus1PercentOfEm: '-0.01em',
    /** Figma **Button** +0,5 % (interlettrage relatif à la taille du corps). */
    buttonHalfPercent: '0.005em',
  },
  /** Titre de module CMS — aligné atome `SectionTitle` size `module`. */
  sectionTitleModule: {
    fontSizePx: 40,
    lineHeight: '1.1',
    letterSpacingEm: '-0.01em',
    fontWeight: 800,
  },
  /** **Title** Figma — aligné atome `SectionTitle` size `title` (étapes How it works, etc.). */
  title: {
    fontSizePx: 32,
    lineHeight: '1.1',
    letterSpacingEm: '-0.01em',
    fontWeight: 800,
  },
  /**
   * **Title small** Figma : Avenir Heavy 800, 24px, interligne 110 %, interlettrage −1 %.
   * (Classes : `figmaDsTitleSmallClassName` / `SectionTitle` `size="small"`.)
   */
  titleSmall: {
    fontSizePx: 24,
    lineHeight: '1.1',
    letterSpacingEm: '-0.01em',
    fontWeight: 800,
  },
  /** Titre de page / hero secondary — atome `Titlepage` (56px, lh 1, tracking −2 %). */
  titlepage: {
    fontSizePx: 56,
    lineHeight: '1',
    letterSpacingEm: '-0.02em',
    fontWeight: 800,
  },
  /** Hero homepage — atome `Main title` (72px max, Avenir Medium 500, lh 1, tracking −2 %). */
  mainTitle: {
    fontSizePx: 72,
    lineHeight: '1',
    letterSpacingEm: '-0.02em',
    fontWeight: 500,
  },
  fontWeight: {
    book: 400,
    roman: 500,
    heavy: 800,
  },
  /**
   * Figma **Button** : Avenir Heavy 800, 12px, interligne 110 %, interlettrage +0,5 %, uppercase.
   * (Vertical trim « Cap height » côté Figma ; le interligne 110 % fixe la boîte de ligne côté web.)
   */
  buttonLabel: {
    fontSizePx: 12,
    lineHeight: '1.1',
    letterSpacingEm: '0.005em',
    fontWeight: 800,
  },
  /**
   * **Paragraph Large Bold** Figma : Avenir Heavy 800, 18px, interligne 160 %, tracking −1 %.
   * (Ex. nom sur carte témoignage.)
   */
  paragraphLargeBold: {
    fontSizePx: 18,
    lineHeight: '1.6',
    letterSpacingEm: '-0.01em',
    fontWeight: 800,
  },
  /**
   * Citation (module **Quote**, corps) : **gras 800** + **italique**, 24px, interligne 110 %, interlettrage −1 %.
   * (Avenir Heavy + `font-style: italic` — aligné *Bold* + *Italic* côté Figma, pas de police « Heavy Oblique » en une seule face.)
   */
  heavyOblique24: {
    fontSizePx: 24,
    lineHeight: '1.1',
    letterSpacingEm: '-0.01em',
    fontWeight: 800,
    fontStyle: 'italic' as const,
  },
  /**
   * **Paragraph Large** Figma : Avenir Roman 400, 18px, interligne 160 %, interlettrage 0 %.
   * (Ex. titres de colonnes footer — Platform, Company, Legal.)
   */
  paragraphLarge: {
    fontSizePx: 18,
    lineHeight: '1.6',
    letterSpacingEm: '0em',
    fontWeight: 400,
    paragraphSpacingPx: 16,
  },
  /**
   * **Links** Figma : Avenir Heavy 800, 16px, interligne 100 %, interlettrage 0 %.
   * (Footer, listes de liens, entrées actives du module « Dans cet article », etc.)
   */
  links: {
    fontSizePx: 16,
    lineHeight: '1',
    letterSpacingEm: '0em',
    fontWeight: 800,
  },
  /**
   * **Paragraph** Figma : Avenir **Book** (style), poids **350**, **14px**, **Vertical trim : Cap height**,
   * **Line height 160 %**, **Paragraph spacing 16px**, **Letter spacing 0 %**.
   * Côté web : `leading-[160%]` + `figmaDsParagraphStackGapClassName` (`space-y-4` = 16px) entre paragraphes successifs.
   */
  paragraph: {
    fontSizePx: 14,
    lineHeight: '1.6',
    letterSpacingEm: '0em',
    fontWeight: 350,
    paragraphSpacingPx: 16,
  },
  /**
   * Figma **(TAG)** : Avenir Heavy 800, 14px, interligne 100 %, interlettrage 0 %, uppercase.
   * Espacement paragraphe Figma : 16px. (Cartes offres — ligne d’info au-dessus du titre.)
   */
  tag: {
    fontSizePx: 14,
    lineHeight: '1',
    letterSpacingEm: '0em',
    fontWeight: 800,
    paragraphSpacingPx: 16,
  },
  /**
   * Figma **Label** : Avenir **Black** 900, 10px, interligne 100 %, interlettrage 0 %, uppercase.
   * (Vertical trim cap height ; alignement vertical « middle » via `items-center` sur le conteneur parent.)
   */
  label: {
    fontSizePx: 10,
    lineHeight: '1',
    letterSpacingEm: '0em',
    fontWeight: 900,
  },
} as const

export type FigmaDsTypographyToken = typeof figmaDsTypography

/**
 * Classes Tailwind du libellé **Button** (à combiner avec `text-white` / `text-black` selon le fond).
 * Chaîne figée pour le scanner Tailwind.
 */
export const figmaDsButtonLabelClassName =
  "font-ui font-semibold text-[12px] font-extrabold leading-[1.1] tracking-[0.005em] uppercase" as const

/**
 * Atome **Paragraph Large Bold** — à combiner avec une couleur texte (ex. `text-black` ou `style.color`).
 */
export const figmaDsParagraphLargeBoldClassName =
  "font-ui font-semibold text-[18px] font-extrabold leading-[1.6] tracking-[-0.01em]" as const

/**
 * Atome **Featured post sidebar title** :
 * Avenir Heavy 800, 18px, interligne 110 %, tracking -1 %.
 * (Utilisé pour les titres de la colonne droite du module blog featured.)
 */
export const figmaDsFeaturedPostSidebarTitleClassName =
  "font-ui font-semibold text-[18px] font-extrabold leading-[1.1] tracking-[-0.01em]" as const

/** Atome **Paragraph Large** — Roman 400, 18px, lh 160 %, tracking 0 %. */
export const figmaDsParagraphLargeClassName =
  "font-ui font-normal text-[18px] font-normal leading-[1.6] tracking-normal" as const

/** Atome **Links** — Avenir Heavy 800, 16px, lh 100 %, tracking 0 %. */
export const figmaDsLinksClassName =
  "font-ui font-semibold text-[16px] font-extrabold leading-none tracking-normal" as const

/**
 * Atome **Paragraph** — à combiner avec une couleur texte (ex. `text-black`, `#62656e` pour secondaire).
 */
export const figmaDsParagraphClassName =
  "font-ui font-normal text-[14px] font-[350] leading-[160%] tracking-[0em]" as const

/** Espacement vertical entre plusieurs blocs `Paragraph` (16px, aligné Figma paragraph spacing). */
export const figmaDsParagraphStackGapClassName = 'space-y-4' as const

/** Figma **(TAG)** — Heavy 14px, lh 100 %, tracking 0 %, uppercase (couleur via classe ou `style`). */
export const figmaDsTagClassName =
  "font-ui font-semibold text-[14px] font-extrabold leading-none tracking-normal uppercase" as const

/**
 * Conteneur **pill catégorie** (hero article / tags) — Figma :
 * padding 10px, coins 8px, fond blanc, pas de bordure ; point 7px + libellé **Label**, gap 6px entre les deux ;
 * espacement entre pills : 8px (`gap-2`) côté parent.
 */
export const figmaDsCategoryPillContainerClassName =
  'inline-flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-2.5' as const

/**
 * Atome **Label** (Figma) — Avenir Black 900, 10px, lh 100 %, tracking 0 %, uppercase.
 * Couleur : combiner avec `text-black` / `text-*` selon le fond.
 */
export const figmaDsLabelClassName =
  "font-ui font-bold text-[10px] font-black leading-none tracking-normal uppercase" as const

/**
 * **Emphasized SM** (legacy / modules timeline) : Avenir Heavy 800, 10px — distinct du **Label** Figma (Black 900).
 * Ex. pastille « EN COURS » : padding parent `px-1.5 py-1`.
 */
export const figmaDsLabelEmphasizedSmClassName =
  "font-ui font-semibold text-[10px] font-extrabold leading-[10px] tracking-normal text-black uppercase" as const

/**
 * Atome **citation 24** — `figmaDsTypography.heavyOblique24` (nom historique) :
 * Avenir Heavy **800** + **italique**, 24px, interligne 110 %, interlettrage −1 %.
 * (Couleur au choix du parent.)
 */
export const figmaDsHeavyOblique24ClassName =
  "font-ui font-semibold text-[24px] font-extrabold italic leading-[1.1] tracking-[-0.01em]" as const

/**
 * Citation (bloc blog / help) — corps : même atome que `figmaDsHeavyOblique24ClassName` + `text-black`.
 */
export const figmaDsArticleQuoteTextClassName = `${figmaDsHeavyOblique24ClassName} text-black` as const

/**
 * Auteur / source sous la citation — Figma : plus petit, gris clair, italique.
 */
export const figmaDsArticleQuoteAuthorClassName =
  "font-ui font-normal text-[14px] italic leading-[1.5] text-[#8893a0]" as const

/**
 * Conteneur du module citation : traits haut / bas uniquement, pas de fond ni bordure gauche,
 * padding vertical 40px (Figma).
 */
export const figmaDsArticleQuoteContainerClassName =
  'border-t border-b border-[#e5e8f0] bg-transparent py-10' as const

/**
 * Guillemet décoratif à gauche — dégradé corail / rose (Figma).
 */
export const figmaDsArticleQuoteIconClassName =
  "font-ui font-semibold shrink-0 select-none text-[2.75rem] leading-none not-italic md:text-[3rem] bg-gradient-to-t from-[#ea580c] via-[#f472b6] to-[#fce7f3] bg-clip-text text-transparent" as const

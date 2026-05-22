/**
 * Section Library - Definitions of available section types
 * Each section type defines its metadata, default data, and validation schema
 */

import { z } from 'zod'

export enum SectionCategory {
  LAYOUT = 'LAYOUT',
  CONTENT = 'CONTENT',
  BLOG = 'BLOG',
  PROJECTS = 'PROJECTS',
  HELP = 'HELP',
}

export interface SectionType {
  key: string
  label: string
  category: SectionCategory
  schemaVersion: string
  defaultData: any
  zodSchema: z.ZodType<any>
  allowedOnTemplates: string[]
  description?: string
  /**
   * Si `true` : le type reste défini pour ne pas invalider les sections existantes en base,
   * mais il est exclu de l'UI « Ajouter section » et du catalogue admin.
   * Voir `getSectionTypesForTemplate` / `getSectionTypesByCategory`.
   */
  deprecated?: boolean
}

/**
 * Gabarits sur lesquels les blocs CMS « marketing / contenu / blog » peuvent être ajoutés
 * (liste module + POST /sections/add). Inclut `vault_builder` pour les pages offre.
 * Les sections Help restent sur `['default']` seul (cf. filtres admin).
 */
export const CMS_COMPOSABLE_PAGE_TEMPLATES: string[] = [
  'homepage',
  'default',
  'blog',
  'project',
  'article',
  'exclusive_offer',
  'vault_builder',
]

// Zod schemas for each section type
const heroSchema = z.object({
  title: z.string().optional(),
  subtitle: z.string().optional(),
  eyebrow: z.string().optional(),
  /** Stats inline (séparées par un point au rendu). */
  inlineStats: z.array(z.string()).optional(),
  note: z.string().optional(),
  ctaText: z.string().optional(),
  ctaLink: z.string().optional(),
  secondaryCtaText: z.string().optional(),
  secondaryCtaHref: z.string().optional(),
  /** Mots animés sur la dernière ligne du titre (homepage Vancelian). */
  typewriterWords: z.array(z.string()).optional(),
  /** Média CMS (résolu en `backgroundMediaUrl` côté serveur). */
  backgroundMediaId: z.string().optional(),
  backgroundMediaUrl: z.string().optional(),
  /** Injecté au rendu depuis la médiathèque (détection image / vidéo). */
  backgroundMediaMimeType: z.string().optional(),
  backgroundMediaFilename: z.string().optional(),
  /** @deprecated Ignoré au rendu — utiliser uniquement le média CMS (`backgroundMediaId`). */
  backgroundImage: z.string().optional(),
  /** Opacité de l’image de fond seule (0 = invisible, 1 = plein). */
  backgroundImageOpacity: z.number().min(0).max(1).optional().default(1),
  sidebarText: z.string().optional(),
  /** Masque le bouton CTA du hero (ex. titre + sous-titre seuls, comme offre exclusive). */
  hideCta: z.boolean().optional(),
  /** Pastilles sous le titre — affichées uniquement en `hero_secondary`. */
  tags: z.array(z.string()).optional(),
})

const headerSchema = z.object({
  logoUrl: z.string().optional(),
  links: z.array(z.object({
    label: z.string(),
    href: z.string(),
  })).optional(),
})

const featureGridSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  items: z.array(z.object({
    title: z.string(),
    description: z.string(),
  })).optional(),
  /** Média médiathèque — résolu en `imageMediaUrl` côté API / page publique. */
  imageMediaId: z.string().optional(),
  /**
   * Champs lus par `mapDataToComponentProps` → `SectionAbout` mais absents du schéma
   * historique : sans eux, un `parse` Zod (modules communs) pouvait les supprimer.
   */
  imageMediaUrl: z.string().optional(),
  imageUrl: z.string().optional(),
  content: z.string().optional(),
  /** Non mappés vers `SectionAbout` — conservés pour ne pas perdre les données au parse. */
  ctaText: z.string().optional(),
  ctaLink: z.string().optional(),
})

const howItWorksStepSchema = z.object({
  number: z.string(),
  title: z.string(),
  description: z.string(),
  /** Image optionnelle entre le numéro et le titre — résolu en `imageMediaUrl` côté site. */
  imageMediaId: z.string().optional(),
  /** URL résolue côté serveur / preview — consommée telle quelle par `SectionHowItWorksCms`. */
  imageMediaUrl: z.string().optional(),
  /** Libellé du bouton d’étape — affiché seulement si `stepButtonHref` est aussi renseigné. */
  stepButtonLabel: z.string().optional(),
  stepButtonHref: z.string().optional(),
})

const howItWorksSchema = z.object({
  label: z.string().optional(),
  title: z.string().optional(),
  subtitle: z.string().optional(),
  /** Si true : masque les numéros d’étape sur le site (cartes titre + texte + CTA optionnel). */
  hideStepNumbering: z.boolean().optional().default(false),
  steps: z.array(howItWorksStepSchema).optional(),
  primaryCtaText: z.string().optional(),
  primaryCtaHref: z.string().optional(),
  secondaryCtaText: z.string().optional(),
  secondaryCtaHref: z.string().optional(),
  surface: z.enum(['light', 'dark']).optional().default('light'),
})

const ctaSchema = z.object({
  /** Surtitre au-dessus du titre (petites caps ; filets gauche/droite gérés par le rendu) */
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  /** Texte riche Markdown (paragraphes, liens, listes, etc.) */
  description: z.string().optional(),
  primaryButtonText: z.string().optional(),
  primaryButtonHref: z.string().optional(),
  secondaryButtonText: z.string().optional(),
  secondaryButtonHref: z.string().optional(),
  /** Afficher le bouton principal (rempli) */
  showPrimaryButton: z.boolean().optional().default(true),
  /** Afficher le bouton secondaire (contour) */
  showSecondaryButton: z.boolean().optional().default(true),
  /** Centré (défaut) ou justifié pour la description ; titre et surtitre restent centrés */
  contentTextAlign: z.enum(['center', 'justify']).optional().default('center'),
  backgroundMediaId: z.string().optional(),
  /** Couleur de fond (plein) sous l’image */
  backgroundColor: z.string().optional().default('#141208'),
  /** Opacité de l’image de fond sur la couleur (0 = invisible, 1 = opaque) */
  backgroundImageOpacity: z.number().min(0).max(1).optional().default(1),
  /** Teinte colorée additionnelle par-dessus l’image (0 = aucune) */
  overlayOpacity: z.number().min(0).max(1).optional().default(0.55),
  /** URL résolue depuis `backgroundMediaId` — nécessaire pour ne pas la perdre au `parse` Zod. */
  backgroundMediaUrl: z.string().optional(),
  backgroundMediaMimeType: z.string().optional(),
  backgroundMediaFilename: z.string().optional(),
  /** Alias legacy — coalescé vers les boutons principaux dans `mapDataToComponentProps`. */
  ctaText: z.string().optional(),
  ctaLink: z.string().optional(),
})

/** Référence vers un module commun global (`GlobalSettings.commonModulesJson`). */
export const commonModuleRefSchema = z.object({
  /** Vide tant que non choisi en admin ; doit être un UUID valide pour résolution runtime. */
  commonModuleId: z.string().default(''),
})

export type CommonModuleRefData = z.infer<typeof commonModuleRefSchema>

/** Plateformes reconnues pour les icônes du footer (réseaux sociaux). */
export const footerSocialPlatformSchema = z.enum([
  'youtube',
  'instagram',
  'facebook',
  'x',
  'linkedin',
  'other',
])

export const footerSchema = z.object({
  copyright: z.string().optional(),
  /** Tagline sous le logo (baseline Home.html). */
  description: z.string().optional(),
  /** Coordonnées / mentions courtes sous la tagline (multiligne). */
  companyAddress: z.string().optional(),
  /** Note secondaire en bas à droite (ex. « Made in Sophia Antipolis… »). */
  secondaryNote: z.string().optional(),
  links: z
    .array(
      z.object({
        label: z.string(),
        href: z.string(),
        category: z.string().optional(),
      }),
    )
    .optional(),
  /** Couleur de fond du pied de page (hex ou valeur CSS courte, ex. #0a0a0a). */
  backgroundColor: z.string().max(80).optional(),
  /** Logo au-dessus de la tagline (médiathèque — id Prisma / CUID). */
  logoMediaId: z.string().nullable().optional(),
  /**
   * Affichage clair sur fond sombre : applique le filtre DS navbar
   * (`brightness(0) invert(1)`) sur le média logo — même principe que la topnav.
   */
  logoMediaInvert: z.boolean().optional(),
  /** Afficher le bloc newsletter en tête de footer. */
  newsletterVisible: z.boolean().optional(),
  newsletterTitle: z.string().optional(),
  newsletterPlaceholder: z.string().optional(),
  /** Libellé du bouton (ex. subscribe / s’inscrire). */
  newsletterButtonLabel: z.string().optional(),
  /** Paragraphes de texte légal sous le copyright. */
  legalTexts: z.array(z.string()).optional(),
  socialLinks: z
    .array(
      z.object({
        platform: footerSocialPlatformSchema,
        href: z.string().min(1),
      }),
    )
    .optional(),
})

/** `global_settings.footer_json` version 2 : plusieurs langues sans migration DB. */
export const footerJsonV2Schema = z.object({
  version: z.literal(2),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  locales: z.object({
    fr: footerSchema.optional(),
    en: footerSchema.optional(),
    it: footerSchema.optional(),
  }),
})

export type FooterJsonInput = z.infer<typeof footerSchema>
export type FooterJsonV2 = z.infer<typeof footerJsonV2Schema>
export type FooterSocialPlatform = z.infer<typeof footerSocialPlatformSchema>

const projectGridSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  limit: z.number().int().min(1).max(20).optional().default(3),
  /**
   * Si true : ignore la sélection manuelle ; le site affiche les offres exclusives publiées
   * (les plus récentes d’abord), en respectant `limit`.
   */
  showAllExclusiveOffers: z.boolean().optional().default(false),
  /** Offres exclusives (UUID packaged_products) — source canonique pour le site. */
  selectedPackagedProductIds: z.array(z.string()).optional(),
  /** @deprecated Anciens projets CMS ; utilisé seulement si selectedPackagedProductIds vide. */
  selectedProjectIds: z.array(z.string()).optional(),
  /**
   * Libellé du bouton « voir toutes les offres » sous la grille (rendu par `SectionProjects`).
   * Si vide, fallback `siteCommonCta(locale, 'view_all_offers')`.
   */
  viewAllButtonText: z.string().optional(),
  /**
   * @deprecated Champ historique non câblé : `SectionProjects` n'a pas de mode carousel
   * et force le rendu en grille. Conservé pour ne pas invalider les données existantes.
   * À retirer dans une future migration si aucune réactivation n'est planifiée.
   */
  layout: z.enum(['grid', 'carousel']).optional().default('grid'),
  // Legacy: items array for backward compatibility
  items: z.array(z.object({
    title: z.string(),
    location: z.string().optional(),
    tags: z.array(z.string()).optional(),
    description: z.string().optional(),
    mediaId: z.string().optional(),
    mediaUrl: z.string().optional(),
    /** Alias lu par le mapping (`mediaUrl || backgroundImage`). */
    backgroundImage: z.string().optional(),
  })).optional(),
  /**
   * Injecté au rendu (offres résolues) — peut être présent dans des exports / previews ;
   * le conserver évite une perte si le JSON transite par `zodSchema.parse`.
   */
  resolvedProjects: z.array(z.record(z.string(), z.unknown())).optional(),
})

const proofPressItemSchema = z.object({
  label: z.string(),
  variant: z.enum(['bfm', 'tribune', 'echos', 'finyear', 'text']).optional(),
})

const proofPressSchema = z.object({
  eyebrow: z.string().optional(),
  items: z.array(proofPressItemSchema).optional(),
})

const offerCardItemSchema = z.object({
  href: z.string().optional(),
  ariaLabel: z.string().optional(),
  centerText: z.string().optional(),
  barTitle: z.string().optional(),
  barSubtitle: z.string().optional(),
  barRate: z.string().optional(),
  coverMediaId: z.string().optional(),
  coverMediaUrl: z.string().optional(),
  hoverVideoMediaId: z.string().optional(),
  hoverVideoMediaUrl: z.string().optional(),
})

const offerCardsSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  viewAllButtonText: z.string().optional(),
  viewAllButtonHref: z.string().optional(),
  items: z.array(offerCardItemSchema).optional(),
})

const productEcosystemItemSchema = z.object({
  iconName: z.string().optional(),
  title: z.string(),
  description: z.string().optional(),
  features: z
    .array(
      z.object({
        text: z.string(),
        iconName: z.string().optional(),
      }),
    )
    .optional(),
  linkText: z.string().optional(),
  linkHref: z.string().optional(),
})

const productEcosystemSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  items: z.array(productEcosystemItemSchema).optional(),
})

const journeyCtaSchema = z.object({
  label: z.string(),
  href: z.string().optional(),
  variant: z.enum(['primary', 'secondary']).optional(),
})

const journeySchema = z.object({
  pill: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  backgroundMediaId: z.string().optional(),
  backgroundMediaUrl: z.string().optional(),
  backgroundMediaMimeType: z.string().optional(),
  backgroundMediaFilename: z.string().optional(),
  notificationMessage: z.string().optional(),
  ctas: z.array(journeyCtaSchema).optional(),
})

const securitySchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  points: z.array(z.object({ text: z.string() })).optional(),
  linkText: z.string().optional(),
  linkHref: z.string().optional(),
  logos: z
    .array(
      z.object({
        label: z.string(),
        caption: z.string().optional(),
      }),
    )
    .optional(),
})

const blogListSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  items: z.array(z.object({
    title: z.string(),
    excerpt: z.string().optional(),
    publishedAt: z.string().optional(),
    slug: z.string().optional(),
    mediaId: z.string().optional(),
  })).optional(),
})

// Blog section schemas
const blogHeroSchema = z.object({
  eyebrow: z.string().optional(),
  showEyebrow: z.boolean().optional().default(true),
  showStandfirst: z.boolean().optional().default(true),
  showMeta: z.boolean().optional().default(true),
})

const blogCategoryNavSchema = z.object({
  title: z.string().optional(),
  showTitle: z.boolean().optional().default(false),
  allLabel: z.string().optional().default('All'),
})

const blogMosaicSchema = z.object({
  title: z.string().optional(),
  ctaLabel: z.string().optional(),
  showTitle: z.boolean().optional().default(true),
  /** Rendu : normalisé en multiple de 3 (0 → 3, 4 → 6, etc.). */
  limit: z.number().int().min(0).max(99).optional().default(3),
  /** Libellés pagination (traduisibles). Repli : `siteCommonCta` previous / next. */
  paginationPrevLabel: z.string().optional(),
  paginationNextLabel: z.string().optional(),
})

const blogFeedSchema = z.object({
  title: z.string().optional(),
  showTitle: z.boolean().optional().default(true),
  pageSize: z.number().int().min(1).max(50).optional().default(10),
  loadMoreLabel: z.string().optional().default('Load more'),
  emptyStateTitle: z.string().optional(),
  emptyStateBody: z.string().optional(),
})

/** Hero « article » 100 % CMS — réutilisable hors lecteur Prisma. */
const blogArticleHeroSchema = z.object({
  showBreadcrumb: z.boolean().optional().default(false),
  blogLabel: z.string().optional(),
  breadcrumbCurrentText: z.string().optional(),
  title: z.string().min(1),
  standfirst: z.string().optional(),
  categoryPillLabels: z.array(z.string()).optional().default([]),
  editorialPillLabel: z.string().optional(),
  authorName: z.string().optional(),
  authorRole: z.string().optional(),
  showAuthorByPrefix: z.boolean().optional().default(false),
  showReadingTime: z.boolean().optional().default(true),
  readingTimeText: z.string().optional(),
  showDate: z.boolean().optional().default(true),
  publishedAtIso: z.string().optional(),
  showUpdatedDate: z.boolean().optional().default(false),
  updatedAtIso: z.string().optional(),
  coverTitle: z.string().optional(),
  imageMediaId: z.string().optional(),
  /** URL couverture résolue — mappée vers `coverUrl` côté renderer. */
  imageMediaUrl: z.string().optional(),
  videoUrl: z.string().optional(),
  coverCredit: z.string().optional(),
  coverSource: z.string().optional(),
})

/** Gabarit page détail article : en-tête + corps + blocs issus de l’article (Prisma). */
const blogArticleReaderSchema = z.object({
  blogLabel: z.string().optional(),
  /** Titre du sommaire (colonne gauche), ex. « Dans cet article ». Vide = libellé site (i18n). */
  tocTitle: z.string().optional(),
  showToc: z.boolean().optional().default(true),
  tocMinHeadings: z.number().int().min(1).max(20).optional().default(3),
  showDocuments: z.boolean().optional().default(true),
  documentsTitle: z.string().optional(),
  /**
   * Durée de lecture : modèle entièrement localisable, avec `{{minutes}}` (ou `{{count}}`) pour le nombre.
   * Ex. « {{minutes}} min de lecture ». Vide = concaténation système (nombre + clé i18n minRead).
   */
  readingTimeLabel: z.string().optional(),
  /** Si true, préfixe type « Par » devant l’auteur. Défaut false = nom d’auteur seul. */
  showAuthorByPrefix: z.boolean().optional().default(false),
  /**
   * Préfixe personnalisé devant l’auteur (ex. « Par », « By »). Vide = libellé
   * site (i18n via `siteCommonCta('article_by_author')`). N’a d’effet que si
   * `showAuthorByPrefix` est `true`. Traduisible (cf. `sectionI18nPolicy`).
   */
  authorPrefixLabel: z.string().optional(),
  /** Si true, affiche la date de mise à jour en plus de la parution. Défaut false. */
  showUpdatedDate: z.boolean().optional().default(false),
  /**
   * Fil d’Ariane (Blog › titre). Défaut true — page article gabarit.
   * Désactiver pour réutiliser le hero sans chemin (landing, autre contexte).
   */
  showBreadcrumb: z.boolean().optional().default(true),
  /** Donnée de démo preview admin — ne pas supprimer au parse. */
  __demoBlogArticle: z.unknown().optional(),
})

const shareSmItemSchema = z.object({
  id: z.string().optional(),
  platform: z
    .enum(['facebook', 'x', 'linkedin', 'instagram', 'youtube', 'link'])
    .optional()
    .default('link'),
  label: z.string(),
  href: z.string(),
})

/** Partage réseaux sociaux (shareSM) — titre + liens éditables / traduisibles. */
const shareSmSchema = z.object({
  title: z.string().optional().default(''),
  items: z.array(shareSmItemSchema).optional().default([]),
})

const blogArticleRelatedSchema = z.object({
  title: z.string().optional(),
  ctaLabel: z.string().optional(),
  ctaHref: z.string().optional(),
  limit: z.number().int().min(1).max(8).optional().default(4),
  emptyTitle: z.string().optional(),
})

/** Gabarit offre exclusive : corps Vault Builder injecté au rendu (aucun champ éditable ici). */
const exclusiveOfferVaultSchema = z.object({})

const faqSchema = z.object({
  /** Surtitre / pastille au-dessus du grand titre — traduisible (cf. policy). */
  eyebrow: z.string().optional().default(''),
  /**
   * Titre canonique du module FAQ (anciennement écrit dans `subtitle`).
   * Le mapping renderer lit `title || subtitle` (compat douce), mais l'admin
   * écrit désormais ici (cf. SectionEditor.faq) et le pipeline i18n cible
   * `title` comme champ principal.
   */
  title: z.string().optional().default(''),
  /**
   * Description optionnelle affichée sous le titre (chapô).
   * Aligné sur la convention Surtitre / Titre / Description des autres modules.
   */
  description: z.string().optional().default(''),
  /**
   * @deprecated Champ legacy : ancien emplacement du grand titre.
   * Conservé en lecture seule pour ne pas perdre les contenus existants
   * (le mapping `SectionRenderer` retombe sur `subtitle` si `title` est vide).
   * L'admin n'expose plus ce champ — la donnée existante reste intacte.
   */
  subtitle: z.string().optional().default(''),
  items: z.array(
    z.object({
      id: z.string(),
      question: z.string(),
      answerMarkdown: z.string(),
    })
  ).optional().default([]),
  support: z.object({
    title: z.string().optional().default(''),
    description: z.string().optional().default(''),
    ctaLabel: z.string().optional().default(''),
    ctaHref: z.string().optional().default(''),
    secondaryLinkLabel: z.string().optional().default(''),
    secondaryLinkHref: z.string().optional().default(''),
  }).optional(),
  ui: z.object({
    expandAllLabel: z.string().optional(),
    collapseAllLabel: z.string().optional(),
  }).optional(),
})

/** Blocs texte « About » Figma (sans média) — voir `design-system/extracted`. */
const figmaSimpleHeroSchema = z.object({
  title: z.string().optional().default(''),
  description: z.string().optional().default(''),
  backgroundColor: z.string().optional().default('#ffffff'),
  textColor: z.string().optional().default('#000000'),
})

const figmaStatItemSchema = z.object({
  value: z.string(),
  label: z.string(),
})

const figmaStatsGridSchema = z
  .object({
    eyebrow: z.string().optional(),
    title: z.string().optional(),
    description: z.string().optional(),
    stats: z.array(figmaStatItemSchema).max(8).optional().default([]),
    columns: z
      .union([z.literal(3), z.literal(4), z.literal(6)])
      .optional()
      .default(3),
  })
  .superRefine((val, ctx) => {
    const cols = val.columns ?? 3
    const maxStats = cols === 4 ? 8 : 6
    const n = val.stats?.length ?? 0
    if (n > maxStats) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `Au plus ${maxStats} indicateur(s) pour ce nombre de colonnes.`,
        path: ['stats'],
      })
    }
  })

/** Carte monde / visuel central en arrière-plan, titre + corps (DS). */
const companyMapSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  backgroundMediaId: z.string().optional(),
  backgroundMediaUrl: z.string().optional(),
  backgroundMediaMimeType: z.string().optional(),
  backgroundMediaFilename: z.string().optional(),
  backgroundMediaAlt: z.string().optional(),
  /** Texte sous la carte — Markdown (paragraphes, listes, liens). */
  bodyContent: z.string().optional(),
})

/** Bloc deux colonnes : texte + image, fond blanc pleine largeur (DS). */
const mediaTextSchema = z.object({
  /** Surtitre / pastille au-dessus du titre — traduisible (cf. policy). */
  eyebrow: z.string().optional().default(''),
  title: z.string().optional(),
  description: z.string().optional(),
  imageMediaId: z.string().optional(),
  imageMediaUrl: z.string().optional(),
  imageMediaMimeType: z.string().optional(),
  imageMediaFilename: z.string().optional(),
  imageMediaAlt: z.string().optional(),
  /** Si true : image à droite, texte à gauche. Si false : image à gauche, texte à droite. */
  mediaRight: z.boolean().optional().default(false),
})

/** Chiffres clés sur fond sombre (grille 3×2, séparateurs, image optionnelle). */
const keyFiguresSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  stats: z.array(figmaStatItemSchema).max(6).optional().default([]),
  backgroundMediaId: z.string().optional(),
  backgroundMediaUrl: z.string().optional(),
  backgroundMediaMimeType: z.string().optional(),
  backgroundMediaFilename: z.string().optional(),
  backgroundColor: z.string().optional().default('#141208'),
  backgroundImageOpacity: z.number().min(0).max(1).optional().default(1),
  overlayOpacity: z.number().min(0).max(1).optional().default(0),
})

const figmaTestimonialCardsSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  /** 1 = une carte par ligne (centrée, max largeur texte) ; 2 = deux cartes côte à côte (≥ md). */
  cardsPerRow: z.union([z.literal(1), z.literal(2)]).optional().default(1),
  items: z
    .array(
      z.object({
        author: z.string(),
        role: z.string(),
        content: z.string(),
        /** @deprecated Préférer avatarMediaId — conservé pour contenus anciens */
        avatar: z.string().optional(),
        /** Média CMS pour la photo (résolu en avatarMediaUrl au rendu) */
        avatarMediaId: z.string().optional(),
        /** URL déjà résolue (aperçu démo / pipeline CMS) — ne pas saisir à la main en prod si vous utilisez la médiathèque */
        avatarMediaUrl: z.string().optional(),
        backgroundColor: z.string().optional(),
      })
    )
    .optional()
    .default([]),
})

/** Témoignages : cartes grises (`Testimonial`), fond de section blanc. */
const testimonialsItemSchema = z.object({
  name: z.string().optional().default(''),
  text: z.string().optional().default(''),
  rating: z.coerce.number().min(0).max(5).optional().default(5),
  title: z.string().optional(),
  /** Photo depuis la médiathèque (`avatarMediaUrl` injecté au rendu). */
  avatarMediaId: z.string().optional(),
  /** URL avatar résolue — peut être présente après résolution CMS. */
  avatarMediaUrl: z.string().optional(),
  /** @deprecated URL directe — préférer `avatarMediaId` */
  avatar: z.string().optional(),
})

const testimonialsSchema = z.object({
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  items: z.array(testimonialsItemSchema).optional().default([]),
})

// Help Center section schemas
const helpHeroV1Schema = z.object({
  kicker: z.string().optional(),
  title: z.string().optional(),
  subtitle: z.string().optional(),
  placeholderSearch: z.string().optional(),
  helperText: z.string().optional(),
  backgroundStyle: z.enum(['purple', 'dark', 'light']).optional().default('purple'),
  /** Contexte optionnel (fil d’Ariane / titres) — voir `mapDataToComponentProps` → `SectionHelpHero`. */
  collectionSlug: z.string().optional(),
  collectionTitle: z.string().optional(),
  categorySlug: z.string().optional(),
  categoryTitle: z.string().optional(),
  showBreadcrumbs: z.boolean().optional(),
  breadcrumbsRootLabel: z.string().optional(),
  breadcrumbsSeparator: z.string().optional(),
})

const helpSearchV1Schema = z.object({
  placeholder: z.string().optional(),
  hint: z.string().optional(),
  clearLabel: z.string().optional(),
  noResultsTitle: z.string().optional(),
  noResultsSubtitle: z.string().optional(),
})

const helpCollectionsGridV1Schema = z.object({
  sectionTitle: z.string().optional(),
  sectionSubtitle: z.string().optional(),
  cardCtaLabel: z.string().optional(),
  articlesCountLabel: z.string().optional(),
  emptyTitle: z.string().optional(),
  emptySubtitle: z.string().optional(),
})

const helpCategoriesGridV1Schema = z.object({
  sectionTitle: z.string().optional(),
  sectionSubtitle: z.string().optional(),
  articlesCountLabel: z.string().optional(),
  emptyTitle: z.string().optional(),
  emptySubtitle: z.string().optional(),
})

const helpCollectionBodyV1Schema = z.object({
  emptyCategoriesTitle: z.string().optional(),
  emptyCategoriesSubtitle: z.string().optional(),
  emptyArticlesTitle: z.string().optional(),
  emptyArticlesSubtitle: z.string().optional(),
})

const helpBreadcrumbsV1Schema = z.object({
  rootLabel: z.string().optional(),
  separator: z.string().optional(),
  collectionTitle: z.string().optional(),
  categoryTitle: z.string().optional(),
  articleTitle: z.string().optional(),
})

const helpSearchResultsV1Schema = z.object({
  resultsTitle: z.string().optional(),
  resultsCountLabel: z.string().optional(),
  emptyTitle: z.string().optional(),
  emptySubtitle: z.string().optional(),
})

const helpArticleReaderV1Schema = z.object({
  updatedLabel: z.string().optional(),
  byLabel: z.string().optional(),
  readingTimeLabel: z.string().optional(),
  relatedTitle: z.string().optional(),
})

const helpSidebarTocV1Schema = z.object({
  tocTitle: z.string().optional(),
  articleId: z.string().optional(),
})

// Section type definitions
export const SECTION_TYPES: SectionType[] = [
  {
    key: 'header',
    label: 'En-tête et menu (obsolète)',
    category: SectionCategory.LAYOUT,
    schemaVersion: 'v1',
    defaultData: {
      logoUrl: '/images/logo.svg',
      links: [
        { label: 'Home', href: '/' },
        { label: 'About', href: '/about' },
        { label: 'Projects', href: '/projects' },
      ],
    },
    zodSchema: headerSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog', 'project', 'article', 'exclusive_offer'],
    description:
      'Deprecated: la navigation publique est gérée via le menu primaire (admin → Menu & Pages), pas via cette section.',
    deprecated: true,
  },
  {
    key: 'hero',
    label: 'Hero d’accueil',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Welcome',
      subtitle: 'Your subtitle here',
      ctaText: 'Get Started',
      ctaLink: '/contact',
      backgroundImageOpacity: 1,
    },
    zodSchema: heroSchema,
    allowedOnTemplates: ['homepage', 'default', 'vault_builder'],
    description:
      'Hero d’accueil : titre 2 lignes (1re noire, 2e dégradé rose → or), image de fond avec opacité réglable.',
  },
  {
    key: 'hero_secondary',
    label: 'Hero de page intérieure',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Page title,\nSecond line',
      subtitle: 'Your subtitle here',
      ctaText: 'Get Started',
      ctaLink: '/contact',
      backgroundImageOpacity: 1,
      hideCta: false,
    },
    zodSchema: heroSchema,
    allowedOnTemplates: [
      'default',
      'blog',
      'project',
      'article',
      'exclusive_offer',
      'vault_builder',
    ],
    description:
      'Hero principal des pages intérieures (gabarits default, blog, article, offre exclusive, etc.) : même design system que l’offre exclusive (espacements / typo). Avec image : texte en contraste sur la photo ; CTA et pastilles optionnels. Distinct du module `hero`, utilisé uniquement sur la page d’accueil.',
  },
  {
    key: 'feature_grid',
    label: 'Grille de points forts',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Features',
      description: 'Our key features',
      items: [
        { title: 'Feature 1', description: 'Description 1' },
        { title: 'Feature 2', description: 'Description 2' },
        { title: 'Feature 3', description: 'Description 3' },
      ],
    },
    zodSchema: featureGridSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Grid of feature items with title and description',
  },
  {
    key: 'how_it_works',
    label: 'Parcours étape par étape',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      label: 'HOW IT WORKS',
      title: '',
      subtitle: '',
      hideStepNumbering: false,
      surface: 'light',
      steps: [
        {
          number: '01',
          title: 'Access the platform',
          description:
            'Create an account or connect a wallet. A simple, secure onboarding. In a few guided steps, you\'re in.',
        },
        {
          number: '02',
          title: 'Explore the Projects',
          description:
            'Browse curated real estate projects with full documentation: location, expected return, maturity, risk profile. Everything you need to decide with confidence.',
        },
        {
          number: '03',
          title: 'Deposit and Start Earning',
          description:
            'Choose a project, deposit in one click, and start earning immediately. Your returns are backed by real assets.',
        },
      ],
      primaryCtaText: 'START EARNING',
      primaryCtaHref: '#projects',
    },
    zodSchema: howItWorksSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Étapes Figma : numérotation masquable, image optionnelle par étape (120px, cover), bouton + lien par étape, CTAs globaux optionnels.',
  },
  {
    key: 'cta',
    label: 'Bloc d’appel à l’action',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Ready to Earn on Premium Real Assets?',
      description:
        'Create an account or connect a wallet, explore our projects, and start earning yield backed by premium real estate. In minutes.',
      primaryButtonText: 'Get started',
      primaryButtonHref: '/signup',
      secondaryButtonText: 'Explore vaults',
      secondaryButtonHref: '/vaults',
      showPrimaryButton: true,
      showSecondaryButton: true,
      contentTextAlign: 'center',
      backgroundColor: '#141208',
      backgroundImageOpacity: 1,
      overlayOpacity: 0.55,
    },
    zodSchema: ctaSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Call-to-action section with buttons',
  },
  {
    key: 'footer',
    label: 'Pied de page global (obsolète)',
    category: SectionCategory.LAYOUT,
    schemaVersion: 'v1',
    defaultData: {
      copyright: `© ${new Date().getFullYear()} Your Company. All rights reserved.`,
      description: 'Company description',
      links: [
        { label: 'About', href: '/about', category: 'company' },
        { label: 'Privacy', href: '/privacy', category: 'legal' },
        { label: 'Contact', href: '/contact', category: 'contact' },
      ],
    },
    zodSchema: footerSchema,
    /** Géré globalement via /admin/pages → Footer ; plus d’ajout par page. */
    allowedOnTemplates: [],
    description: 'Deprecated: use global footer (Admin → Menu & Pages → Footer)',
    deprecated: true,
  },
  {
    key: 'project_grid',
    label: 'Grille d’offres et de projets',
    category: SectionCategory.PROJECTS,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: '',
      title: 'Our Projects',
      description: 'Discover our portfolio',
      showAllExclusiveOffers: false,
      selectedPackagedProductIds: [],
      items: [],
    },
    zodSchema: projectGridSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Grid of project items (will connect to Projects DB in Phase B)',
  },
  {
    key: 'proof_press',
    label: 'Bandeau presse (proof bar)',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: 'Ils parlent de nous',
      items: [
        { label: 'BFM BUSINESS', variant: 'bfm' },
        { label: 'La Tribune', variant: 'tribune' },
        { label: 'Les Échos', variant: 'echos' },
        { label: 'FINYEAR', variant: 'finyear' },
      ],
    },
    zodSchema: proofPressSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Logos presse monochrome (BFM, La Tribune, Les Échos, Finyear).',
  },
  {
    key: 'offer_cards',
    label: 'Offres exclusives (cartes éditoriales)',
    category: SectionCategory.PROJECTS,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: 'Offres exclusives',
      title: "L'immobilier premium,\nfragment par fragment.",
      description: 'Investissez dans des projets immobiliers haut de gamme tokenisés.',
      viewAllButtonText: 'Voir toutes les offres',
      viewAllButtonHref: '/offres-exclusives',
      items: [],
    },
    zodSchema: offerCardsSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Grille 3 cartes offer-card DS avec vidéo au survol.',
  },
  {
    key: 'product_ecosystem',
    label: 'Écosystème produit',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: "Au-delà de l'immobilier.",
      description: 'Épargne flexible, cryptomonnaies et carte de paiement dans une seule application.',
      items: [],
    },
    zodSchema: productEcosystemSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Grille 3 product-cards (icône Kalai, features, lien terracotta).',
  },
  {
    key: 'journey',
    label: 'Storytelling journey (fullbleed)',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      pill: 'Étape 01',
      title: "Nous choisissons l'actif.",
      description: '',
      notificationMessage: '',
      ctas: [],
    },
    zodSchema: journeySchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Section storytelling vidéo plein écran avec pill, notification iOS et CTAs.',
  },
  {
    key: 'security',
    label: 'Sécurité & régulation',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Régulé, audité,\ntransparent.',
      description: '',
      points: [],
      logos: [],
    },
    zodSchema: securitySchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Split texte + grille logos régulateurs (AMF, Modulr, VISA, Audit).',
  },
  {
    key: 'blog_list',
    label: 'Blog — liste simple (obsolète)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Latest Articles',
      description: 'Read our latest blog posts',
      items: [],
    },
    zodSchema: blogListSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog'],
    description:
      'Deprecated: aucun rendu réel (placeholder admin). Utiliser `blog_feed` / `blog_mosaic` / `blog_hero` pour la liste blog publique.',
    deprecated: true,
  },
  {
    key: 'blog_hero',
    label: 'Blog — article à la une',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: 'À la une',
      showEyebrow: true,
      showStandfirst: true,
      showMeta: true,
    },
    zodSchema: blogHeroSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Hero section displaying the featured article',
  },
  {
    key: 'blog_article_hero',
    label: 'Blog — en-tête type article (CMS)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      showBreadcrumb: false,
      blogLabel: 'Blog',
      title: 'Titre du hero',
      standfirst: 'Chapô ou sous-titre (texte CMS, sans article Prisma).',
      categoryPillLabels: [],
      editorialPillLabel: '',
      authorName: '',
      authorRole: '',
      showAuthorByPrefix: false,
      showReadingTime: true,
      readingTimeText: '4 min de lecture',
      showDate: true,
      publishedAtIso: '',
      showUpdatedDate: false,
      updatedAtIso: '',
      coverTitle: '',
      videoUrl: '',
      coverCredit: '',
      coverSource: '',
    },
    zodSchema: blogArticleHeroSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Bandeau type page article (fond gris, titre, méta, visuel) entièrement piloté par le CMS — réutilisable sur toute page. Pour le contenu d’article réel (Prisma + corps), utiliser le module « Blog — article complet (lecture) » sur le gabarit article.',
  },
  {
    key: 'blog_article_reader',
    label: 'Blog — article complet (lecture)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      blogLabel: 'Blog',
      tocTitle: 'Dans cet article',
      showToc: true,
      tocMinHeadings: 3,
      showDocuments: true,
      documentsTitle: 'Documents',
      readingTimeLabel: '{{minutes}} min de lecture',
      showAuthorByPrefix: true,
      authorPrefixLabel: 'Par',
      showUpdatedDate: false,
      showBreadcrumb: true,
    },
    zodSchema: blogArticleReaderSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Page détail article : en-tête lié à l’article Prisma (titre, blocs, médias), puis corps, sommaire, documents. Réservé au gabarit « article ». Réglages enveloppe : fil d’Ariane, sommaire, documents, durée de lecture (`{{minutes}}`), partage via le module « Blog — partage sur les réseaux ». Pour un bandeau article 100 % CMS sur une autre page, utiliser « Blog — en-tête type article (CMS) ».',
  },
  {
    key: 'blog_category_nav',
    label: 'Blog — filtres par catégorie (obsolète)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Explorer',
      showTitle: false,
      allLabel: 'Tous',
    },
    zodSchema: blogCategoryNavSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Obsolète : plus rendu sur la liste blog CMS (`BlogTemplatePageView`). Conservé en catalogue pour compat données / Prisma.',
    deprecated: true,
  },
  {
    key: 'blog_mosaic',
    label: 'Blog — mosaïque d’articles',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'À ne pas manquer',
      ctaLabel: 'Voir tous les articles',
      showTitle: true,
      limit: 3,
    },
    zodSchema: blogMosaicSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Mosaic grid of highlighted articles',
  },
  {
    key: 'blog_feed',
    label: 'Blog — liste des articles',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Derniers articles',
      showTitle: true,
      pageSize: 10,
      loadMoreLabel: 'Voir plus',
      emptyStateTitle: 'Aucun article',
      emptyStateBody: 'Il n\'y a pas encore d\'articles publiés.',
    },
    zodSchema: blogFeedSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Paginated feed of latest articles with load more',
  },
  {
    key: 'share_sm',
    label: 'Blog — partage sur les réseaux',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Partager',
      items: [
        {
          id: 'sm-fb',
          platform: 'facebook' as const,
          label: 'Facebook',
          href: 'https://www.facebook.com/sharer/sharer.php?u={{encodedUrl}}',
        },
        {
          id: 'sm-x',
          platform: 'x' as const,
          label: 'X',
          href: 'https://twitter.com/intent/tweet?url={{encodedUrl}}&text={{encodedTitle}}',
        },
        {
          id: 'sm-li',
          platform: 'linkedin' as const,
          label: 'LinkedIn',
          href: 'https://www.linkedin.com/sharing/share-offsite/?url={{encodedUrl}}',
        },
        {
          id: 'sm-th',
          platform: 'instagram' as const,
          label: 'Threads',
          href: 'https://www.threads.net/intent/post?text={{encodedShareText}}',
        },
      ],
    },
    zodSchema: shareSmSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Module partage : titre + liste de réseaux (pictogramme, libellé accessibilité, URL ou modèle avec {{url}}, {{encodedUrl}}, {{title}}, {{encodedTitle}}, {{encodedShareText}}). Traduisible. Sur la page article, affiché dans la colonne du lecteur si une section « Article (lecture) » est présente. Sur le gabarit offre exclusive, l’URL et le titre cibles sont ceux de la page projet courante.',
  },
  {
    key: 'blog_article_related',
    label: 'Blog — articles suggérés',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Vous aimerez aussi',
      ctaLabel: 'Voir tous les articles',
      ctaHref: '',
      limit: 4,
      emptyTitle: 'Aucun article suggéré pour le moment.',
    },
    zodSchema: blogArticleRelatedSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'Grille 2×2 d’articles récents (hors l’article courant), style cartes blog.',
  },
  {
    key: 'exclusive_offer_vault',
    label: 'Offre — contenu Vault (obsolète)',
    category: SectionCategory.PROJECTS,
    schemaVersion: 'v1',
    defaultData: {},
    zodSchema: exclusiveOfferVaultSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Emplacement du contenu Vault Builder pour chaque offre. Édition du détail : Admin → Exclusive Offers / Vault Builder.',
    deprecated: true,
  },
  {
    key: 'faq',
    label: 'Questions fréquentes (FAQ)',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: '',
      title: '',
      description: '',
      // `subtitle` (legacy) — non rempli par défaut. Conservé en lecture seule
      // dans le mapping renderer pour les contenus existants.
      subtitle: '',
      items: [],
      support: {
        title: '',
        description: '',
        ctaLabel: '',
        ctaHref: '',
        secondaryLinkLabel: '',
        secondaryLinkHref: '',
      },
    },
    zodSchema: faqSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description: 'FAQ accordion section with questions and answers',
  },
  {
    key: 'testimonials',
    label: 'Témoignages avec notes',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: '',
      title: '',
      description: '',
      items: [],
    },
    zodSchema: testimonialsSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Grille de témoignages (étoiles + cartes grises). Surtitre, titre, description, liste de cartes.',
  },
  // Help Center sections
  {
    key: 'help_hero_v1',
    label: 'Aide — bandeau d’accueil',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      kicker: 'HELP CENTER',
      title: 'Conseils et réponses de l\'équipe Arquantix',
      subtitle: 'Trouvez rapidement les réponses à vos questions',
      placeholderSearch: 'Rechercher un article…',
      helperText: 'Recherchez par mot-clé, question, sujet…',
      backgroundStyle: 'purple',
    },
    zodSchema: helpHeroV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Hero section for Help Center with purple background',
  },
  {
    key: 'help_search_v1',
    label: 'Aide — recherche (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      placeholder: 'Rechercher un article…',
      hint: 'Recherchez par mot-clé, question, sujet…',
      clearLabel: 'Effacer',
      noResultsTitle: 'Aucun résultat',
      noResultsSubtitle: 'Essayez un autre mot-clé.',
    },
    zodSchema: helpSearchV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Search bar for Help Center articles',
    deprecated: true,
  },
  {
    key: 'help_collections_grid_v1',
    label: 'Aide — grille des collections (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      sectionTitle: 'Collections',
      sectionSubtitle: 'Parcourir par thème',
      cardCtaLabel: 'Voir',
      articlesCountLabel: 'articles',
      emptyTitle: 'Aucune collection',
      emptySubtitle: 'Créez votre première collection dans l\'admin.',
    },
    zodSchema: helpCollectionsGridV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Grid of Help Center collections',
    deprecated: true,
  },
  {
    key: 'help_categories_grid_v1',
    label: 'Aide — grille des catégories (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      sectionTitle: 'Catégories',
      sectionSubtitle: '',
      articlesCountLabel: 'articles',
      emptyTitle: 'Aucune catégorie',
      emptySubtitle: '',
    },
    zodSchema: helpCategoriesGridV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Grid of Help Center categories',
    deprecated: true,
  },
  {
    key: 'help_collection_body_v1',
    label: 'Aide — contenu de collection (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      emptyCategoriesTitle: 'Aucune catégorie',
      emptyCategoriesSubtitle: 'Aucune catégorie disponible dans cette collection.',
      emptyArticlesTitle: 'Aucun article',
      emptyArticlesSubtitle: 'Aucun article disponible dans cette catégorie.',
    },
    zodSchema: helpCollectionBodyV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Collection page body with categories and article lists (Shares-style)',
    deprecated: true,
  },
  {
    key: 'help_breadcrumbs_v1',
    label: 'Aide — fil d’Ariane (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      rootLabel: 'Toutes les collections',
      separator: '›',
    },
    zodSchema: helpBreadcrumbsV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Breadcrumb navigation for Help Center',
    deprecated: true,
  },
  {
    key: 'help_search_results_v1',
    label: 'Aide — résultats de recherche (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      resultsTitle: 'Résultats',
      resultsCountLabel: 'résultats',
      emptyTitle: 'Aucun article trouvé',
      emptySubtitle: 'Essayez une autre recherche.',
    },
    zodSchema: helpSearchResultsV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Search results list for Help Center',
    deprecated: true,
  },
  {
    key: 'help_article_reader_v1',
    label: 'Aide — lecture d’article (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      updatedLabel: 'Mis à jour',
      byLabel: 'Par',
      readingTimeLabel: 'min de lecture',
      relatedTitle: 'Articles associés',
    },
    zodSchema: helpArticleReaderV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Article reader view for Help Center',
    deprecated: true,
  },
  {
    key: 'help_sidebar_toc_v1',
    label: 'Aide — sommaire latéral (obsolète)',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      tocTitle: 'Sur cette page',
    },
    zodSchema: helpSidebarTocV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Table of contents sidebar for Help Center articles',
    deprecated: true,
  },
  {
    key: 'figma_simple_hero',
    label: 'Hero texte seul (obsolète)',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Titre',
      description: 'Paragraphe d’introduction (module About Figma, sans image).',
      backgroundColor: '#ffffff',
      textColor: '#000000',
    },
    zodSchema: figmaSimpleHeroSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Hero titre + texte uniquement (export Figma). Distinct du hero image CMS (`hero` / `hero_secondary`).',
    deprecated: true,
  },
  {
    key: 'figma_stats_grid',
    label: 'Grille de statistiques',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: '',
      title: '',
      description: '',
      columns: 3,
      stats: [
        { value: '35+', label: 'Projets' },
        { value: '€60M+', label: 'Investi' },
        { value: '5', label: 'Pays' },
      ],
    },
    zodSchema: figmaStatsGridSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Jusqu’à 6 indicateurs (3 ou 6 colonnes) ou 8 en 2×4 (4 colonnes). Cartes style Figma.',
  },
  {
    key: 'key_figures',
    label: 'Statistiques sur fond sombre (obsolète)',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: 'STORY',
      title: '',
      stats: [
        { value: '35+', label: 'Projects completed internationally' },
        { value: '€60M+', label: 'Total amount invested' },
        { value: '5', label: 'Countries in which we operate' },
        { value: '30%', label: 'Average gross margin of projects *' },
        { value: 'DEC 2021', label: 'Year of launch' },
        { value: '24 months', label: 'Average duration of operations' },
      ],
      backgroundColor: '#141208',
      backgroundImageOpacity: 0.22,
      overlayOpacity: 0,
    },
    zodSchema: keyFiguresSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Grille 3×2 de chiffres (valeur + libellé), fond sombre, image optionnelle, surtitre.',
    deprecated: true,
  },
  {
    key: 'figma_testimonial_cards',
    label: 'Citations clients en cartes',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: '',
      title: '',
      description: '',
      cardsPerRow: 1,
      items: [
        {
          author: 'Marie Dubois',
          role: 'Investisseur',
          content: 'Exemple de témoignage au format carte Figma (auteur, rôle, texte).',
          backgroundColor: '#f4f4f4',
          avatarMediaUrl:
            'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=256&q=80',
        },
      ],
    },
    zodSchema: figmaTestimonialCardsSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Cartes témoignage Figma : 1 ou 2 par ligne. Distinct de `testimonials` (étoiles).',
  },
  {
    key: 'media_text',
    label: 'Texte & Image - Gauche / Droite',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: '',
      title: 'Titre',
      description:
        'Description du bloc : deux colonnes sur fond blanc, image arrondie et texte (Avenir).',
      mediaRight: false,
    },
    zodSchema: mediaTextSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Bloc titre + description + image (médiathèque), fond blanc pleine largeur. 2ᵉ instance : clé `media_text_2`, etc. (comme les autres types du catalogue).',
  },
  {
    key: 'company_map',
    label: 'Carte monde et texte',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: 'PRÉSENCE INTERNATIONALE',
      title: 'Une présence mondiale',
      description:
        'Arquantix accompagne les investisseurs sur plusieurs zones géographiques stratégiques.',
      bodyContent:
        'Contenu détaillé au **Markdown** : listes, liens, paragraphes. La carte reste en arrière-plan entre le titre et ce bloc.',
    },
    zodSchema: companyMapSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Surtitre, titre, description, image de fond (carte) et corps texte. La carte chevauche le titre et le corps sur fond blanc ; le rendu atténue le bleu des océans vers un blanc cassé pour rester lisible avec le texte.',
  },
  {
    key: 'common_module_ref',
    label: 'Module défini dans la structure du site',
    category: SectionCategory.LAYOUT,
    schemaVersion: 'v1',
    defaultData: {
      commonModuleId: '',
    },
    zodSchema: commonModuleRefSchema,
    allowedOnTemplates: CMS_COMPOSABLE_PAGE_TEMPLATES,
    description:
      'Insère un bloc défini dans Structure du site → Zone 2. Le contenu multilingue s’édite sur la fiche du module commun.',
  },
]

/**
 * Ramène une clé d’instance CMS (`cta_2`, `media_text_3`, `project_grid_2`, …) vers la clé
 * canonique du type (`cta`, `media_text`, `project_grid`). `projects` → `project_grid`.
 */
export function resolveCanonicalSectionKey(key: string): string | null {
  if (key === 'projects') {
    return 'project_grid'
  }
  const sorted = [...SECTION_TYPES].sort((a, b) => b.key.length - a.key.length)
  for (const t of sorted) {
    const tk = t.key
    if (key === tk) return tk
    if (key.startsWith(`${tk}_`)) {
      const rest = key.slice(tk.length + 1)
      if (/^\d+$/.test(rest)) return tk
    }
  }
  return null
}

/**
 * Get section type by key
 */
export function getSectionType(key: string): SectionType | undefined {
  if (key === 'projects') {
    return SECTION_TYPES.find((type) => type.key === 'project_grid')
  }
  const canonical = resolveCanonicalSectionKey(key)
  if (canonical) {
    return SECTION_TYPES.find((type) => type.key === canonical)
  }
  return SECTION_TYPES.find((type) => type.key === key)
}

/**
 * Get section types by category. Exclut par défaut les types `deprecated`
 * (utiliser `{ includeDeprecated: true }` pour l'admin debug).
 */
export function getSectionTypesByCategory(
  category: SectionCategory,
  options?: { includeDeprecated?: boolean },
): SectionType[] {
  const includeDeprecated = options?.includeDeprecated === true
  return SECTION_TYPES.filter(
    (type) => type.category === category && (includeDeprecated || !type.deprecated),
  )
}

/**
 * Get section types allowed on template. Exclut par défaut les types `deprecated`.
 */
export function getSectionTypesForTemplate(
  template: string,
  options?: { includeDeprecated?: boolean },
): SectionType[] {
  const includeDeprecated = options?.includeDeprecated === true
  return SECTION_TYPES.filter(
    (type) =>
      (type.allowedOnTemplates.includes(template) ||
        type.allowedOnTemplates.includes('default')) &&
      (includeDeprecated || !type.deprecated),
  )
}

/** Gabarits pages / articles / offre (exclut help-only, etc.) — éligibilité « module commun ». */
const COMMON_MODULE_TEMPLATE_ALLOWLIST = new Set([
  'homepage',
  'default',
  'blog',
  'project',
  'article',
  'exclusive_offer',
  'vault_builder',
])

const COMMON_MODULE_FORBIDDEN_KEYS = new Set(['footer', 'header', 'common_module_ref'])

/**
 * Types de sections qu’on peut instancier comme module commun global (Zone 2).
 * Aligné sur le catalogue CMS (`SECTION_TYPES`), hors types dépréciés / navigation / auto-référence.
 */
export function getSectionTypesEligibleAsCommonModule(): SectionType[] {
  return SECTION_TYPES.filter(
    (type) =>
      !type.deprecated &&
      !COMMON_MODULE_FORBIDDEN_KEYS.has(type.key) &&
      type.allowedOnTemplates.some((t) => COMMON_MODULE_TEMPLATE_ALLOWLIST.has(t)),
  )
}

/**
 * Validate section data against its schema
 */
export function validateSectionData(key: string, data: any): { valid: boolean; error?: string } {
  const sectionType = getSectionType(key)
  if (!sectionType) {
    return { valid: false, error: `Unknown section type: ${key}` }
  }

  try {
    sectionType.zodSchema.parse(data)
    return { valid: true }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { valid: false, error: error.issues.map((e) => `${e.path.join('.')}: ${e.message}`).join(', ') }
    }
    return { valid: false, error: 'Validation failed' }
  }
}

/**
 * Politiques i18n des sections (chemins traduits vs non traduits) — Lot 5.
 * Toute nouvelle section dans `SECTION_REGISTRY` doit y être déclarée ; test de couverture associé.
 */
export {
  resolveSectionI18nPolicy,
  SECTION_I18N_POLICIES,
  type SectionI18nPolicyDefinition,
  type ResolvedSectionI18n,
} from './sectionI18nPolicy'


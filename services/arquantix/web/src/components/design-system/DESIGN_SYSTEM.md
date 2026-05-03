# Design system (site web Arquantix)

Source : exports Figma / React (modules fusionnés). Usage principal : page `/design` et composition des pages marketing.

## Typographie navigation (atomes)

| Rôle | Paramètres | Fichier |
|------|------------|---------|
| **Links** (atome typographie Figma) | Avenir Heavy 800, 16px, line-height 100%, letter-spacing 0% | Composant `extracted/atoms/links.tsx` → `Links` ; jeton `figmaDsLinksClassName` + `figmaDsTypography.links` |
| **Links** (menu top) | Identique | `nav-primary-link.ts` → `NAV_PRIMARY_LINK_TYPO` (= `figmaDsLinksClassName`) |
| **Links** (titres des entrées du méga-menu blanc) | Identique **Links** ci-dessus | `MEGA_MENU_ITEM_TITLE_TYPO` (= alias) ; module `mega-menu/figma/FigmaNavSubmenu.tsx` |
| **Paragraph** (libellés de colonne + descriptions sous les titres du méga-menu) | Avenir Book 350, 14px, vertical trim cap height, line-height 160%, paragraph spacing 16px, letter-spacing 0% | Composant `extracted/atoms/paragraph.tsx` → `Paragraph` ; `figmaDsParagraphClassName` + `figmaDsTypography.paragraph` ; couleur `figmaDsColors.text.secondary` dans `FigmaNavSubmenu.tsx` |
| **Titre** SimpleMarkdownContentModule (Vault / offres) | Avenir Heavy 800, 40px, line-height 110%, letter-spacing −1%, center | `simpleMarkdownModuleTitle.ts` → `SIMPLE_MARKDOWN_MODULE_TITLE_TYPO` ; jetons `figmaDsTypography.fontSize.xl`, `lineHeight.tight`, `letterSpacing.minus1PercentOfEm` |
| **Lien menu (cadre)** | Padding 8 / 12px, `border-radius` 10px ; actif : fond noir + texte blanc | `NAV_MENU_LINK_FRAME`, `NAV_MENU_LINK_ACTIVE_SURFACE` |

## Modules

| Module | Fichier |
|--------|---------|
| Marketing block (gradient / image) | `marketing-block.tsx` |
| How it works | `HowItWorks.tsx` |
| Bloc gauche / droite | `BlockLeftAndRight.tsx`, `DecorativeOverlay.tsx` |
| Galerie projets | `ProjetGallery/ProjetGallery.tsx`, `ProjetGalleryDemo.tsx` |
| Témoignage | `Testimonial.tsx` |
| FAQ | `FAQ.tsx` |
| Pied de page | `Footer.tsx` |
| Page « tous les projets » | `ProjetGalleryPage.tsx` |

## Assets

Imports SVG / PNG : `imports/` (dossiers `Footer`, `Arguments`, `ExclusiveOffers`, `PageDeToutLesProjets`).

## Couche Figma extraite (zip « Extraire composants pour Design Systeme »)

Emplacement : `extracted/` (atomes, molécules, organismes, tokens préfixés `figmaDs*`).

| Rôle | Composants |
|------|------------|
| Texte / titres | `FigmaBodyText`, `FigmaSectionTitle`, `FigmaEyebrowLabel`, `PillActionButton` |
| Blocs | `FigmaStatCard`, `FigmaSectionHeading`, `FigmaTestimonialCard` |
| Sections | `FigmaSimpleHero`, `FigmaStatsGrid` |
| Démo | `ExtractedDesignDemo` (section en tête de `/design`) |
| Tokens | `figmaDsColors`, `figmaDsTypography`, `figmaDsSpacing`, `figmaDsBorderRadius`, `figmaDsTokens` |
| Canevas page (fond blanc init) | `figmaDsColors.background.light` / `pageCanvas`, classes `figmaDsBodyRootClassName`, `figmaDsSiteShellLightClassName` (`extracted/tokens/surfaces.ts`) — pas de `bg-neutral-100` sur body / coque |

**CMS** : sections enregistrées `figma_simple_hero`, `figma_stats_grid`, `figma_testimonial_cards` (voir `lib/sections/library.ts`). Elles composent les organismes ci-dessus sans remplacer `hero`, `testimonials`, etc.

**UI shadcn** : le zip contenait aussi `calendar` / `chart` ; ils n’ont pas été copiés ici (incompatibilités de types avec `react-day-picker` v9 et `recharts` v3). Le dossier `components/ui/` existant est inchangé.

## Flutter

Le design system mobile Flutter n’est pas défini ici ; ne pas confondre avec ces fichiers.

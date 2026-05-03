# Export Figma Make — méga-menu

Source : archive « Extraire module React Navbar.zip » (Figma Make).

## Fichiers repris

- **`FigmaNavSubmenu.tsx`** — dérivé de `src/app/components/arquantix/NavSubmenu.tsx` du ZIP (structure colonne / catégorie / item, classes utilitaires, typo Avenir).
- **`/public/mega-menu-default-icon.png`** — image placeholder du ZIP (`Frame60/42f27831d2837f01bb009e380b97eb22f4371c23.png`).

## Non importé tel quel

- Tout le dossier `ui/` shadcn du ZIP (sidebar, chart, etc.) : déjà couvert par le design system Arquantix.
- `Frame60.tsx` statique : remplacé par les données CMS (`buildMegaMenuColumns` + `getPrimaryMenu`).

## Typographie (DS)

- Titres des lignes (nom de page) : **`MEGA_MENU_ITEM_TITLE_TYPO`** (`nav-primary-link.ts`) = **Links Heavy** (16px, `leading-none`), aligné sur la barre de navigation primaire.

## Adaptations par rapport au Figma

- Liens : balise `<a href>` avec chemins publics localisés.
- Icônes : URL pré-signée (médiathèque) ou PNG par défaut ci-dessus.
- Conteneur : ombre + `border` + `rounded-[24px]` + `max-w` pour coller au rendu cible.
- Grille : `flex-wrap` pour plusieurs colonnes sur petits écrans desktop étroits.

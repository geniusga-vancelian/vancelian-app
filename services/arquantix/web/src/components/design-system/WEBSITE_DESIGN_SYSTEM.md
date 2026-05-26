# Design System — Site web (marketing / CMS)

> Le portail client `/app/*` utilise un DS **séparé** : voir `APP_DESIGN_SYSTEM.md`.

Source de vérité **figée** pour le website :

- **CSS** : `src/styles/vancelian-tokens.css` (`:root`, `data-v-ds="website"`)
- **Thème shadcn** : `src/styles/design-system-theme.css`
- **Composants** : `src/components/design-system/vancelian/*`, sections CMS, `extracted/`

Ne pas importer les styles `src/styles/app/*` dans les pages marketing.

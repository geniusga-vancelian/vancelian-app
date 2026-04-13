# Design system — présentations Vancelian

Projet Vite + React + Tailwind v4 dérivé du fichier Figma [Créer un Design System](https://www.figma.com/design/n45dEKfM60OyqBKcLcpHKi/Cr%C3%A9er-un-Design-System). Il sert de **showcase** et de **bibliothèque de composants** pour vos futurs decks (titres, cartes, mise en page slide, palette, etc.).

## Démarrage

```bash
npm install
npm run dev
```

Build production : `npm run build` — prévisualisation : `npm run preview`.

## Structure utile pour les slides

- `src/app/components/design-system/` — composants métier (export central dans `index.ts`) : typographie, `Logo`, `SlideLayout`, `SlideHeader`, `SlideFooter`, cartes, citations, etc.
- `src/styles/theme.css` — tokens (couleurs, rayons, typo).
- `src/app/App.tsx` — page de documentation / vitrine des composants.
- `src/imports/` — restes d’export Figma Make (`figma:asset/*`) : **non utilisés** par l’app actuelle ; ignorés par `tsc` pour garder un typage propre.

## Prochaines étapes possibles

Composer de vraies slides (routes ou story par slide), exporter des captures PDF, ou publier les composants en package interne — selon votre flux (Pitch, Google Slides, etc.).

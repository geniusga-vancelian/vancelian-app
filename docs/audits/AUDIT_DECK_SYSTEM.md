# Audit technique — système slides / decks / design system

**Périmètre** : application `presentation-design-system/` (Vite + React) et absence de persistance côté API Arquantix au moment de l’audit initial.

**Date** : 2026-03-30

---

## 1. Cartographie des fichiers et dossiers

### 1.1 Design system « deck »

| Zone | Chemin | Rôle |
|------|--------|------|
| Tokens / typo / layout | `presentation-design-system/src/app/components/design-system/` | `Typography`, `SlideLayout`, `SlideHeader`, `SlideFooter`, `Card`, `Quote`, `Divider`, `Colors`, `ContentBlock`, `Arrow`, `Logo` |
| Showcase | `presentation-design-system/src/app/DesignSystemShowcase.tsx` | Démonstration des briques, route `/design-system` |
| Spécifiques device | `presentation-design-system/src/app/design-tokens/iphoneProAppFrame.ts` | Constantes pour frames iPhone (Offering slide) |

**Constat** : le design system est **centralisé** dans `components/design-system/` et réutilisé par les templates. Les couleurs / typo sont cohérentes au sein de ces composants.

### 1.2 Templates de slides

| Fichier / dossier | Rôle |
|-------------------|------|
| `src/app/components/slide-templates/index.ts` | Barrel export de tous les templates React |
| `TitleSlide.tsx`, `TwoColumnSlide.tsx`, `TeamSlide.tsx`, `MetricsSlide.tsx`, `TimelineSlide.tsx`, `ComparisonSlide.tsx`, `CenteredContentSlide.tsx`, etc. | **Composants React** : structure + props typées en TypeScript |
| `keyElementsSlideShared.tsx`, `advancedStaffOrgChartDemo.ts` | Partages / données de démo |

**Forme des templates** : exclusivement **composants React avec props** (pas de JSON de contenu générique côté repo pour la galerie complète). Chaque template impose son propre contrat de props (hétérogène entre slides).

### 1.3 Galerie / registre UI des templates

| Fichier | Rôle |
|---------|------|
| `src/app/templates/SlideTemplatesGallery.tsx` | Liste ~18 entrées ; type union `SlideType` ; métadonnées `name`, `description`, `useCase` **en dur** ; rendu preview par switch sur `id` |

**Identifiant template** : existe côté front sous forme de **littéraux string** (`'title'`, `'two-column'`, …) — **pas d’UUID**, pas de table BDD.

### 1.4 Deck « métier » exemple (Registration)

| Fichier | Rôle |
|---------|------|
| `src/app/deck/registrationDeckContent.ts` | Tableau `registrationSlides: RegistrationSlideData[]` — **données typées** (section, intro, items, sidebar…) |
| `src/app/deck/RegistrationDeckSlide.tsx` | Rendu d’une slide registration (layout dédié) |
| `src/app/deck/RegistrationDeck.tsx` | Navigation carousel entre slides registration |

**Constat** : le deck registration est un **cas vertical** : schéma `RegistrationSlideData` **différent** du schéma des templates marketing (Title, KPI, etc.). **Pas de couche commune** « slide générique + template_key » dans les données.

### 1.5 Routes SPA

Définies dans `src/app/App.tsx` :

| Route | Composant |
|-------|-----------|
| `/` | `RegistrationDeck` |
| `/templates` | `SlideTemplatesGallery` |
| `/design-system` | `DesignSystemShowcase` |

### 1.6 Preview / export

| Fichier | Rôle |
|---------|------|
| `src/app/templates/exportSlideToPdf.ts` | Export PDF via canvas + `jspdf` (utilisé par la galerie) |

### 1.7 Persistance existante

- **Aucune** API ou base de données dans le périmètre Arquantix pour les templates deck ou les présentations avant l’implémentation décrite dans `docs/architecture/DECK_PERSISTENCE_AND_VERSIONING.md`.
- Le backend `services/arquantix/api` expose de nombreux domaines (portfolio, registration, lending, …) ; **aucun** modèle SQLAlchemy « presentation » ou « slide template » dans `database.py` avant extension.

---

## 2. Cartographie API / services (état initial)

- **Pas de routes** `/api/presentation-*` ni équivalent.
- **Pas de modèles** Prisma/SQLAlchemy pour decks dans ce domaine.

---

## 3. Modèles de données (front uniquement)

- **SlideTemplatesGallery** : interface locale `SlideTemplate { id: SlideType; name; description; useCase }`.
- **registrationDeckContent** : type `RegistrationSlideData` + tableau constant.

---

## 4. Points positifs

1. **Design system réutilisable** et visuellement aligné (headers, footers, typo).
2. **Bibliothèque de templates riche** et extensible par ajout de composants + export dans `index.ts`.
3. **Galerie** offre preview et export PDF pour itération design.
4. **Séparation** approximative : design-system vs slide-templates vs deck registration (dossiers distincts).

---

## 5. Problèmes / fragilités

1. **Duplication de vérité** : la liste des templates existe à la fois comme **composants** et comme **tableau `slideTemplates`** dans `SlideTemplatesGallery.tsx` (risque de dérive).
2. **Schéma de contenu non homogène** : chaque template a des props différentes ; pas de **schéma JSON** unique pour édition / validation côté serveur.
3. **Couplage rendu / contenu** : le contenu « métier » des decks est soit **TS constant** (registration), soit **démo inline** dans la galerie ; pas de modèle « slide instance » neutre.
4. **Pas de versionning** : aucune notion de V1/V2, draft/validé/archivé.
5. **Pas d’industrialisation** : pas de CRUD admin, pas de sauvegarde, pas d’audit snapshot.

---

## 6. Manques pour sauvegarde et versionning

- Tables PostgreSQL (templates, decks, versions, slides).
- API REST (CRUD + lifecycle).
- **Mapping** `template_key` (string stable) ↔ composant React (registre front).
- **schema_json** par template pour validation du `content_json`.
- **Snapshot** immuable à la validation (audit + replay).
- UI : listes, éditeur, actions Save / Save as version / Validate / Archive.

---

## 7. Code mort / incohérences signalés

- La galerie maintient un **large switch** sur `SlideType` pour le preview : tout nouveau template doit y être ajouté **manuellement** (oublis possibles).
- Le deck registration **ne réutilise pas** les templates de la galerie (deux mondes parallèles).

---

## 8. Recommandation (résumé)

- Introduire une **couche persistance** (PostgreSQL + FastAPI) avec modèle **hybride** : lignes relationnelles pour l’édition + `snapshot_json` figé à la validation.
- Standardiser une **slide document** : `template_key` + `content_json` + métadonnées, validés par `schema_json` du template.
- Conserver les **composants React** comme moteur de rendu ; le serveur stocke des **données**, pas du JSX.

*Le détail d’implémentation (tables, endpoints, règles métier) est décrit dans `docs/architecture/DECK_PERSISTENCE_AND_VERSIONING.md`.*

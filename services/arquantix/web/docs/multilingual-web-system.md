# Système multilingue — site web Arquantix (`services/arquantix/web`)

Document de référence technique interne. Il décrit **l’implémentation actuelle** telle qu’elle existe dans le dépôt, sans spécifier de feuille de route sauf section « dette / évolutions possibles ».

### TL;DR (lecture rapide)

- **Locale publique (layout)** : **`resolveLayoutLocale`** — segment `/{fr|en|it}` (header `x-arq-locale`) **>** cookie **>** défaut ; plus de primauté cookie sur l’URL pour `html lang` / menu sur ces routes.
- **Racine `/`** : redirection vers `/{locale}` (ordre : `?locale=` valide > cookie > `Accept-Language` > défaut) — voir `middleware.ts`, `rootLocaleRedirect.ts`.
- **Home indexable** : `/fr`, `/en`, `/it` — `app/[locale]/page.tsx` ; metadata via `page_i18n` + fallback legacy.
- **Pages CMS publiques** : `/fr/[slug]`, `/en/[slug]`, `/it/[slug]` — `app/[locale]/[slug]/page.tsx`. Ancienne URL `/slug` → redirection **308** vers `/fr/slug` (sauf routes listées dans `legacyUnprefixedPaths.ts`).
- **hreflang (phase 2C)** : `alternates.languages` **uniquement** pour les locales « qualifiées » (contenu section publié + critère SEO — voir `cmsPageHreflang.ts` et §8). URLs **absolues** via `getSiteOrigin()` ; **pas** d’hreflang sans origine (`NEXT_PUBLIC_SITE_URL` / `VERCEL_URL`).
- **Footer** : `global_settings.footer_json` — **legacy** (objet plat) ou **v2** `{ version: 2, defaultLocale, locales: { fr?, en?, it? } }`.
- **Nouvelle section CMS** dans `SECTION_REGISTRY` : entrée obligatoire dans **`sectionI18nPolicy.ts`** (+ test de couverture).
- **Canonical SEO** : chemin public **stable**, **sans** `?locale=` (voir §8).

### Flux simplifié (pipeline)

```text
Requête HTTP
    ↓
resolvePublicLocale (cookie > ?locale > défaut)
    ├─→ layout.tsx ………… html lang, getPrimaryMenu(locale), nav shell
    ├─→ page.tsx / [slug] / preview ………… generateMetadata (locale avec searchParams si présent)
    │       └─→ buildPublicCmsPageMetadata (canonical sans query)
    ├─→ getPageSections(slug, locale, mode) ………… SectionRenderer (données par locale + fallbacks)
    └─→ SiteFooter ………… getSiteFooterData(locale) [layout sans query sur le footer]
```

**Phase 2B** : sur tout chemin commençant par `/fr/`, `/en/`, `/it/` (y compris la home), le middleware envoie `x-arq-locale` — le layout et le footer utilisent `resolveLayoutLocale` (URL > cookie). Le détail des exceptions (blog, projects, preview, etc.) est en §4, §6 et §7.

---

## 1. Objectif et périmètre

### Ce que couvre cette documentation

- Comportement **runtime** du site Next.js (`services/arquantix/web`) concernant les **locales** (`fr`, `en`, `it`).
- Résolution de locale sur les **pages publiques** et **preview CMS**.
- Contenu **CMS** par page : sections, `SectionContent`, fallbacks.
- **Menu primaire** : résolution des libellés.
- **Footer global** : stockage `global_settings.footer_json`, formats legacy / v2, admin, runtime.
- **Metadata / SEO** : `html lang`, titres/descriptions, canonical, Open Graph, absence de hreflang — tel que codé.
- **Gouvernance i18n des sections** : `sectionI18nPolicy.ts`, traduction automatique des données de section.
- **Conventions** pour les évolutions du code dans ce périmètre.

### Ce qu’elle ne couvre pas

- Application **mobile** Flutter ou autres services du monorepo.
- **Prisma** en détail (schéma complet, migrations) — seulement les concepts nécessaires (Page, Section, SectionContent, Menu, `global_settings`).
- **Back-office** hors footer global et hors flux déjà cités (ex. traduction d’articles) sauf mention lorsque le même code est partagé.

### Contexte

Le multilingue repose sur :

- des **locales** enumérées dans `src/config/locales.ts` ;
- une **préférence** utilisateur portée par un **cookie** et/ou un paramètre de **query** `locale` sur certaines pages ;
- du contenu **par locale** en base pour les sections (`section_contents`) et le menu (`menu_items` + i18n) ;
- un footer global stocké en **JSON** dans `global_settings.footer_json` (legacy plat ou **v2** multilingue) ;
- des **politiques explicites** par type de section pour la traduction automatique (`sectionI18nPolicy.ts`).

---

## 2. Vue d’ensemble de l’architecture multilingue

| Domaine | Rôle | Source de vérité principale |
|--------|------|-----------------------------|
| **Locales supportées** | `fr`, `en`, `it` | `src/config/locales.ts` |
| **Résolution locale publique** | Cookie `arquantix-locale` > `?locale=` valide > défaut `fr` | `resolvePublicLocale` dans `src/lib/i18n/resolvePublicLocale.ts` |
| **Pages CMS** | Contenu par `Page` + `Section` + `SectionContent` (par `locale`) | Prisma ; chargement via `getPageSections` dans `src/lib/cms/content.ts` |
| **Sections (données)** | JSON par section + locale + statut (published/draft) | `section_contents` ; fallback documenté dans `getPageSections` |
| **Menu** | Libellés via `resolveLabelWithFallback` + lignes i18n menu item | `src/lib/menu/getPrimaryMenu.ts`, `src/lib/i18n/resolveLabel.ts` |
| **Footer** | JSON global `footer_json` | `src/lib/cms/footerStorage.ts`, `src/lib/cms/site-footer.ts` |
| **Metadata / SEO** | Title/description Page + canonical + OG/Twitter + hreflang CMS | `buildPublicCmsPageMetadata`, `cmsPageHreflang.ts`, `siteOrigin.ts`, `app/[locale]/page.tsx`, `app/[locale]/[slug]/page.tsx`, `app/layout.tsx` |
| **Traduction auto des sections** | Chemins par type de section | `src/lib/sections/sectionI18nPolicy.ts` + `translateSectionData` |

**Fallback** : chaînes différentes selon le domaine (voir section 10).

---

## 3. Locales supportées

- **Valeurs** : `fr` (défaut), `en`, `it`.
- **Source de vérité** : `supportedLocales`, `defaultLocale`, `isValidLocale`, `getLocaleOrDefault` dans `src/config/locales.ts`.
- **Format** : codes ISO 639-1 courts, pas de variante régionale dans le type `Locale` (ex. pas de `fr-FR` dans le type — les balises OG utilisent une autre map, voir section 8).

---

## 4. Résolution de locale

### Helper principal

**`resolvePublicLocale`** — `src/lib/i18n/resolvePublicLocale.ts`

```text
Priorité :
1. Cookie `arquantix-locale` (nom : `ARQUANTIX_LOCALE_COOKIE` dans `src/lib/i18n/locale-server.ts`) si valeur ∈ locales supportées
2. Sinon `searchParams.locale` (string ou premier élément si tableau) si valide
3. Sinon `defaultLocale` (`fr`)
```

### Cookie

- Nom exact : **`arquantix-locale`** (`ARQUANTIX_LOCALE_COOKIE`).
- Lu côté serveur via `cookies()` de Next.js là où le composant/route l’utilise.

### Query `?locale=`

- Utilisée **uniquement** si le code passe `searchParams` à `resolvePublicLocale`.
- **Exemples** :
  - **`app/page.tsx`** (home) : `resolvePublicLocale({ cookieStore, searchParams })` — query prise en compte si pas de cookie valide.
  - **`app/[slug]/page.tsx`** : idem.
  - **`app/preview/[slug]/page.tsx`** : idem (preview CMS).
  - **`app/layout.tsx`** : `resolvePublicLocale({ cookieStore, searchParams: undefined })` — **pas de query** au layout racine : le layout ne reçoit pas `searchParams`.

### Conséquences

| Contexte | Cookie | `?locale=` | html `lang` (voir §8) |
|----------|--------|------------|------------------------|
| Home avec `?locale=en` sans cookie | — | `en` pour le **contenu** de la page | Layout : **cookie seulement** → souvent `fr` si pas de cookie |
| Home avec cookie `en` | `en` | ignoré si cookie valide | `en` |

> **Attention — cookie vs `?locale=` vs `<html lang>`**  
> Le paramètre **`?locale=`** peut influencer le **contenu** et les **metadata** des pages qui passent `searchParams` à `resolvePublicLocale` (ex. home, `[slug]`, preview). En revanche, **`<html lang>`** est défini dans le **layout racine** avec `searchParams: undefined` : seuls le **cookie** et le **défaut** `fr` comptent.  
> **Conséquence** : un lien du type `…?locale=en` **sans** cookie peut afficher du contenu (et des balises meta de la réponse) cohérents avec `en`, **tandis que** l’attribut du document reste souvent `lang="fr"`. Ce n’est pas un bug de routing : c’est un **écart connu et assumé** entre négociation de contenu par query et attribut de langue du document (contrainte App Router sur le layout). Pour un alignement cookie / document, il faut **poser le cookie** (ou n’utiliser que le défaut).

### SEO / indexation

- La **canonical** des pages CMS publiques est le **chemin sans query** (voir section 8). `?locale=` ne doit pas apparaître dans la canonical.

---

## 5. Pages CMS et contenus localisés

### Modèle (rappel fonctionnel)

Sans entrer dans tout le schéma Prisma :

- **`Page`** : une page logique (`slug`, `urlPath`, `title`, `description` au niveau page — champs **mono-locale** côté modèle actuel pour le SEO de base).
- **`Section`** : instances de blocs sur une page (`key`, `order`, etc.).
- **`SectionContent`** : données JSON d’une section pour une **`locale`** et un **`status`** (ex. `PUBLISHED` / `DRAFT`).

### Chargement : `getPageSections`

**Fichier** : `src/lib/cms/content.ts` — fonction **`getPageSections(slug, locale, mode)`**.

1. Chargement de la `Page` par `slug` avec sections ordonnées et `contents` **filtrés par la locale demandée** (`getLocaleOrDefault(locale)`).
2. Pour chaque section, sélection d’un contenu selon `mode` (`published` vs `draft`) avec enchaînement de **fallbacks** :
   - brouillon vs publié selon le mode ;
   - si toujours rien et locale ≠ `fr` : requête explicite vers la **`defaultLocale`** (`fr`) pour la même section (publié puis brouillon selon les branches du code).

Si aucun contenu exploitable : la section peut être absente du tableau retourné (comportement à vérifier section par section côté rendu).

### Ce qui est localisé

- Le **JSON** dans `SectionContent.data` est la vérité par langue pour le rendu des sections.
- Les champs **`Page.title` / `Page.description`** servent aux **metadata** ; ils ne sont pas multi-lignes par langue dans le modèle actuel (un seul titre/description par page en base).

### Rendu React

`SectionRenderer` reçoit les sections enrichies (médias résolus, etc.) après `getPageSections`. La **locale** du contenu affiché correspond à la résolution ci-dessus, pas à un second mécanisme par composant.

---

## 6. Menu / navigation

### Source de vérité

- Menu Prisma clé **`primary`** avec `menu_items` (activés, ordonnés), liés aux pages le cas échéant.
- **Fichier** : `src/lib/menu/getPrimaryMenu.ts`.

### Libellés

- Chaque item a un **`label`** de base et des lignes **`i18n`** (couples locale / label).
- Résolution : **`resolveLabelWithFallback`** (`src/lib/i18n/resolveLabel.ts`) :
  1. locale demandée (`getLocaleOrDefault` du paramètre passé à `getPrimaryMenu`) ;
  2. sinon locale par défaut **`fr`** (`DEFAULT_LOCALE` dans ce fichier) ;
  3. sinon **`baseLabel`**.

### Ce qui n’est pas « traduit » par ce pipeline

- Les **URLs** (`urlPath`, liens externes pour boutons) ne passent pas par ce helper de libellé.
- Le menu est chargé dans le **layout** avec la locale issue de **`resolvePublicLocale` sans `searchParams`** → aligné **cookie / défaut**, pas la query seule sur la première paint du layout.

---

## 7. Footer multilingue

### 7.1 Runtime public

**Lecture** : `getSiteFooterData(locale?)` — `src/lib/cms/site-footer.ts`.

- `locale` : typiquement issue de `getLocaleOrDefault` ; **`SiteFooter`** appelle `resolvePublicLocale` **sans** `searchParams`, puis `getSiteFooterData(locale)` — donc **cookie / défaut**, comme le layout pour le pied de page.

**Stockage** : champ JSON **`global_settings.footer_json`** (Prisma).

**Formats** (parsés par `parseFooterStorage` — `src/lib/cms/footerStorage.ts`) :

1. **Legacy** : un objet plat validé par **`footerSchema`** (`src/lib/sections/library.ts`).
2. **v2** : `{ version: 2, defaultLocale, locales: { fr?, en?, it? } }` — **`footerJsonV2Schema`**.

**Fallback runtime** — `resolveFooterPayloadForLocale(parsed, requestedLocale)` :

- **Legacy** : toujours le **même** objet pour toute locale.
- **v2** : ordre — locale demandée → `defaultLocale` du document → `fr` (`defaultLocale` config) → autres locales supportées ; premier bloc **défini** (clé présente dans `locales`, y compris objet vide `{}`) ; sinon `{}` puis fusion avec valeurs par défaut applicatives dans `buildSiteFooterDataFromPayload`.

**`defaultLocale` (v2)** : méta du document indiquant la langue de secours pour le runtime lorsqu’une locale n’a pas de bloc.

### 7.2 Admin footer

**API** : `src/app/api/admin/site-footer/route.ts`

- **GET** : `getAdminFooterLoadPayload` — renvoie `formatVersion`, `isLegacyStorage`, `defaultLocale`, `locales` (toujours `fr` / `en` / `it` en structure).
- **PUT** :
  - **`mode: "locale"`** (recommandé) : corps `{ locale, defaultLocale, block }` — fusion via **`buildFooterJsonV2AfterLocaleEdit`** sans écraser les autres langues.
  - **Corps plat** (legacy) : fusion dans la locale par défaut du document si stockage déjà v2 ; sinon écriture plat.
  - **`version: 2`** : document v2 complet (remplacement).

**UI** : `src/components/admin/SiteFooterEditor.tsx` — sélecteur de langue éditée, `defaultLocale`, sauvegarde par langue, bandeau legacy, copie depuis la langue de secours.

**Migration legacy → v2** : à la première sauvegarde en mode locale, le serveur produit un document v2 ; le legacy est mappé côté admin dans **`locales.fr`** pour l’affichage initial.

### 7.3 Compatibilité et risques

- **PUT legacy** sur stockage **v2** : fusion dans le bloc de la **locale par défaut** du document, pas effacement des autres langues (voir route).
- **Risque** : deux onglets admin qui sauvent en parallèle — dernière écriture gagne.
- **Runtime** : inchangé pour les consommateurs autre que lecture JSON — pas de double footer.

---

## 8. Metadata / SEO multilingue

### `html lang`

- **`app/layout.tsx`** : `<html lang={locale}>` avec `locale = resolvePublicLocale({ cookieStore, searchParams: undefined })` — **pas** de query.

### Home `/{locale}` et pages CMS `/{locale}/[slug]`

- **`buildPublicCmsPageMetadata`** — `src/lib/metadata/cmsPageMetadata.ts` — utilisé par `generateMetadata` dans `app/[locale]/page.tsx` et `app/[locale]/[slug]/page.tsx`.
- **Locale** pour title/description/OG : segment d’URL + `PageI18n` via `resolvePageSeoFields` (phase 2A/2B).
- **`Page.title` / `Page.description`** : champs legacy ; le SEO par langue passe par **`PageI18n`** pour les locales non défaut (voir `resolvePageI18nMetadata`).

### Canonical

- Chemin **stable sans** `?locale=` : `/{locale}` pour la home CMS, `/{locale}/{slug}` pour une page CMS, `/projects/${slug}` si template vault (redirection serveur depuis la route localisée — voir `app/[locale]/[slug]/page.tsx`).

### hreflang (phase 2C)

- Émis **seulement** si `getSiteOrigin()` est défini (sinon pas d’`alternates.languages` — évite des URLs relatives ou invalides).
- **Règle stricte** (`getLocalesQualifiedForHreflang` dans `src/lib/cms/cmsPageHreflang.ts`) :
  1. Au moins une ligne `SectionContent` **PUBLISHED** pour la page et la locale.
  2. **Et** signal SEO : pour la locale par défaut (`fr`), `PageI18n` titre/description **ou** legacy `Page.title` / `description` ; pour les autres locales, **`PageI18n`** avec titre **ou** description non vide (pas de variante annoncée avec métadonnées vides).
- **Self-canonical** : l’URL courante ; les entrées `alternates.languages` pointent vers les **chemins localisés** (`/fr/...`, `/en/...`), jamais vers `?locale=`.
- **`x-default`** : ajouté vers l’URL de la **locale par défaut** lorsque celle-ci est qualifiée.
- Pages **vault** (template builder) : **pas** de hreflang sur la route CMS (redirection vers `/projects/...` ; canonical projet).

### Origine du site (`metadataBase`, `og:url`)

- **`getSiteOrigin` / `getSiteMetadataBase`** — `src/lib/metadata/siteOrigin.ts` :
  - `NEXT_PUBLIC_SITE_URL` (URL absolue du site public) ;
  - sinon `VERCEL_URL` (préfixe `https://`).
- **`layout`** : fusion de `metadataBase` si défini.
- Sans origine : URLs absolues OG optionnelles non générées (comportement acceptable en dev).

### Open Graph / Twitter

- OG : `title`, `description`, `type: website`, `siteName`, `locale` (ex. `fr_FR`), `url` si origine connue.
- Twitter : `card: summary`, `title`, `description`.
- **Pas** d’`og:image` global imposé par ce module sans asset dédié.

---

## 9. Gouvernance i18n des sections

### Fichier central

**`src/lib/sections/sectionI18nPolicy.ts`**

- Table **`SECTION_I18N_POLICIES`** : par clé (ou alias stable), soit :
  - **`translatable`** + liste de **chemins** (champs ou chemins avec `[]` pour tableaux) ;
  - **`notTranslatable`** + **raison** textuelle (ex. `header`).

### Résolution pour une clé d’instance

**`resolveSectionI18nPolicy(sectionKey, canonicalKey)`** — le **canon** est calculé **à l’extérieur** (pas d’import circulaire depuis `library.ts`) :

- Dans **`translateSectionData`** : `resolveCanonicalSectionKey(sectionKey)` (`src/lib/sections/library.ts`) puis appel avec `(sectionKey, canonicalKey)`.

### Statuts effectifs

| Résultat | Comportement dans `translateSectionData` |
|----------|----------------------------------------|
| `translatable` | Traduction des chemins listés (texte ou markdown selon règles dans le fichier). |
| `notTranslatable` | Données inchangées, **sans** avertissement « chemins manquants ». |
| `missingPolicy` | Données inchangées ; **`console.warn` en dev** invitant à ajouter une politique. |

### Garde-fou

**`src/lib/sections/sectionI18nPolicy.test.ts`** : toute clé présente dans **`SECTION_REGISTRY`** (`src/lib/sections/registry.tsx`) doit résoudre une politique **autre que** `missingPolicy`.

### Ajout d’une nouvelle section

1. Enregistrer le composant dans **`SECTION_REGISTRY`**.
2. Ajouter une entrée dans **`SECTION_I18N_POLICIES`** (ou réutiliser une clé canonique déjà couverte).
3. Faire passer le test de registre.
4. Pour la traduction automatique : les chemins doivent correspondre aux champs **éditoriaux** réels du JSON de section.

---

## 10. Fallbacks — tableau récapitulatif

| Domaine | Ordre / logique courte |
|--------|-------------------------|
| **Locale publique** (`resolvePublicLocale`) | Cookie valide → `?locale=` valide → `fr` |
| **Locale avec défaut** (`getLocaleOrDefault`) | Valeur valide → sinon `fr` |
| **Sections CMS** (`getPageSections`) | Contenu demandé locale + mode → fallbacks publié/brouillon → puis **`fr`** si autre locale sans contenu |
| **Menu** (`resolveLabelWithFallback`) | i18n ligne locale demandée → i18n `fr` → `baseLabel` |
| **Footer v2** (`resolveFooterPayloadForLocale`) | Locale demandée → `defaultLocale` doc → `fr` → autres clés ; legacy : un seul bloc |
| **Footer données manquantes** (`getSiteFooterData`) | JSON absent/invalide → **`getDefaultSiteFooterData`** |
| **Metadata titre/description** | Champs Page si présents → fallback **`CMS_PAGE_METADATA_FALLBACK`** |
| **`html lang`** | Cookie / défaut au layout (**sans** query) |

---

## 11. Limites connues et choix assumés

- **Routes hors préfixe** : blog, projects, help, etc. restent hors schéma `/{locale}/…` (voir `legacyUnprefixedPaths.ts` / middleware).
- **hreflang** : couverture **CMS public principal** sous `/{locale}` ; pas d’équivalents déclarés pour les routes non migrées.
- **`Page.title` / `description`** : pas de colonnes par locale ; le SEO de base est **monolingue au niveau DB** pour ces champs.
- **Décalage possible** : même phénomène que l’encart **Attention** (§4) — query sans cookie vs `lang` du document.
- **Sections** : chemins traduisibles **maintenus à la main** dans `sectionI18nPolicy.ts` (pas de génération automatique depuis Zod).
- **Footer** : édition multilingue en admin, mais pas de « traduction auto » du footer dans ce document (hors périmètre du pipeline section).

---

## 12. Guide de contribution (développeurs)

### Nouvelle page publique (App Router)

- Si elle doit respecter la locale : utiliser **`cookies()`** + **`resolvePublicLocale`** avec **`searchParams`** si la route en expose (cohérence avec home / `[slug]`).
- Pour le SEO : réutiliser **`buildPublicCmsPageMetadata`** ou le même pattern (canonical sans query, pas de hreflang artificiel).
- Documenter si la page **n’a pas** `searchParams` (même limitation que le layout pour `lang`).

### Nouvelle section CMS

1. Schéma Zod + entrée dans **`SECTION_TYPES`** (`library.ts`) si la section est une entrée de bibliothèque.
2. Composant + **`SECTION_REGISTRY`**.
3. **`sectionI18nPolicy.ts`** + test registre vert.
4. Prévoir les **`SectionContent`** par locale en base selon le produit.

### Nouveaux champs texte dans une section

- Mettre à jour le schéma Zod et les données par défaut si besoin.
- Ajouter les chemins dans la politique **`translatable`** si la traduction automatique doit les couvrir ; sinon documenter **`notTranslatable`** avec raison.

### Toucher au footer

- Préférer l’API **`mode: "locale"`** pour ne pas écraser les autres langues.
- Après changement du schéma commun (`footerSchema` / v2), valider **runtime** + **admin**.

### Toucher au SEO

- Ne pas ajouter **`?locale=`** à la canonical ni aux **`alternates.languages`**.
- Définir **`NEXT_PUBLIC_SITE_URL`** en production pour `metadataBase`, OG absolus et **hreflang** (sinon pas d’alternates langues).
- N’émettre du hreflang que via **`getLocalesQualifiedForHreflang`** (pas de variantes « vides »).

### Nouveau composant « traduisible » (données section)

- Ce n’est pas le composant React qui est traduit, c’est le **JSON** via **`translateSectionData`** : ajouter / ajuster **`sectionI18nPolicy.ts`**.

---

## 13. Fichiers clés

| Thème | Fichiers |
|--------|----------|
| **Locale** | `src/config/locales.ts`, `src/lib/i18n/resolvePublicLocale.ts`, `src/lib/i18n/locale-server.ts`, `src/lib/i18n/resolveLabel.ts` |
| **Pages / layout** | `src/app/layout.tsx`, `src/app/page.tsx` (redirect `/` → `/{locale}`), `src/app/[locale]/page.tsx`, `src/app/[locale]/[slug]/page.tsx`, `src/app/preview/[slug]/page.tsx` |
| **Contenu CMS** | `src/lib/cms/content.ts`, `src/lib/cms/resolveHomePageCmsSlug.ts` |
| **Menu** | `src/lib/menu/getPrimaryMenu.ts`, `src/lib/menu/computeUrlPath.ts` (URLs) |
| **Footer** | `src/lib/cms/footerStorage.ts`, `src/lib/cms/site-footer.ts`, `src/components/site/SiteFooter.tsx`, `src/lib/sections/library.ts` (`footerSchema`, `footerJsonV2Schema`) |
| **Admin footer** | `src/app/api/admin/site-footer/route.ts`, `src/components/admin/SiteFooterEditor.tsx` |
| **Sections (registre / canon)** | `src/lib/sections/registry.tsx`, `src/lib/sections/library.ts` (`resolveCanonicalSectionKey`, `SECTION_TYPES`) |
| **i18n policy / traduction** | `src/lib/sections/sectionI18nPolicy.ts`, `src/lib/translate/translateSectionData.ts`, `src/app/api/admin/translate/section/route.ts` |
| **SEO / metadata** | `src/lib/metadata/cmsPageMetadata.ts`, `src/lib/metadata/siteOrigin.ts`, `src/lib/cms/cmsPageHreflang.ts`, `src/lib/i18n/localizedPath.ts` |
| **Tests** | `src/lib/i18n/resolvePublicLocale.test.ts`, `src/lib/cms/footerStorage.test.ts`, `src/lib/sections/sectionI18nPolicy.test.ts`, `src/lib/metadata/cmsPageMetadata.test.ts`, `src/lib/metadata/siteOrigin.test.ts` |

---

## 14. Scénarios de validation manuelle (QA)

- **Changement de langue** : définir le cookie `arquantix-locale` (ou UI qui le pose) ; vérifier menu + sections + footer (si contenus différents par locale).
- **Home** : `/?locale=en` sans cookie → contenu / metadata de la requête ; vérifier `<html lang>` si besoin (limitation connue).
- **Page CMS** : même chose sur `/[slug]?locale=…`.
- **Footer** : cookie `fr` / `en` ; vérifier texte du pied de page ; comparer avec admin (v2).
- **Fallback section** : page avec contenu seulement en `fr`, visite en `en` → repli attendu vers `fr` selon `getPageSections`.
- **Admin footer** : éditer une langue, sauver, recharger ; vérifier l’autre langue intacte.
- **SEO** : `View Source` — canonical sans `?locale=` ; présence OG/Twitter si origine configurée ; **hreflang** (CMS) si `NEXT_PUBLIC_SITE_URL` ou `VERCEL_URL` : uniquement des URLs absolues propres, sans `?locale=`.
- **E2E automatisé (noyau)** : suite Playwright ciblée multilingue — `npm run test:e2e` depuis `services/arquantix/web` (prérequis : DB + seed incluant `e2e-smoke`, voir `e2e/README.md`).

---

## 15. Dette technique / évolutions possibles (non réalisées)

- **SEO** : extension **hreflang** au-delà du périmètre CMS principal (blog, help, projects, etc.) ; harmonisation exhaustive des liens secondaires.
- **Automatisation** : alignement **Zod ↔ chemins** `sectionI18nPolicy` (génération ou tests de cohérence).
- **Layout** : exposition cohérente de `searchParams` pour `html lang` (ex. middleware ou segment dédié) — trade-off complexité / bénéfice.
- **OG image** : stratégie globale ou par page si assets disponibles.

---

*Document généré pour refléter le code dans `services/arquantix/web` au moment de sa rédaction. En cas d’écart, le code fait foi.*

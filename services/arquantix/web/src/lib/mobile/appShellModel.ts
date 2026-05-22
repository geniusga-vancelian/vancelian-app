/**
 * Modèle de données pour le **shell de l'app Flutter** (tabs principaux + menu « More »),
 * piloté en CMS via `Menu`/`MenuItem`/`MenuItemI18n` (labels par locale) + un
 * `Page` système associé à un `SectionContent` qui porte les **cibles mobiles**
 * et **icônes** (non localisées).
 *
 * Conformément à la décision produit (cf. plan « App administration »), on
 * réutilise les tables existantes — **aucune migration Prisma**.
 *
 * Clés stables (à respecter dans le seed et les requêtes) :
 * - `Menu.key = 'app_main_tabs'` : tab bar principale.
 * - `Page.slug = 'app:main-tabs'`, `Page.template = 'app_menu'`,
 *   `isSystemPage = true`, `pageRole = STANDARD`.
 * - `Section.key = 'app_menu_v1'`, `schemaVersion = 'v1'`.
 *
 * Le `SectionContent.data` (par locale, status PUBLISHED) contient :
 * `{ items: [{ menuItemId, target: AppMobileTarget, icon: AppMobileIconKey }] }`.
 *
 * Les `target`/`icon` ne sont **pas localisées** (techniques) : pour cohérence
 * de schéma et compatibilité avec le résolveur i18n existant, on les duplique
 * néanmoins dans une row `SectionContent` par locale activée.
 */

import { z } from 'zod'

export const APP_MAIN_TABS_MENU_KEY = 'app_main_tabs'
export const APP_MAIN_TABS_PAGE_SLUG = 'app:main-tabs'
export const APP_MENU_TEMPLATE = 'app_menu'
export const APP_MENU_SECTION_KEY = 'app_menu_v1'
export const APP_MENU_SCHEMA_VERSION = 'v1'

/// Catalogue des cibles natives connues du shell Flutter (mapping côté Dart).
/// On garde une enum stricte : tout `native_tab` non listé sera ignoré côté app
/// (fallback graceful vers le mapping compilé).
export const APP_NATIVE_TABS = [
  'home',
  'offers',
  'markets',
  'design_system',
  'search',
  'more',
] as const
export type AppNativeTabKey = (typeof APP_NATIVE_TABS)[number]

const nativeTabSchema = z.object({
  kind: z.literal('native_tab'),
  value: z.enum(APP_NATIVE_TABS),
})

const cmsPageSchema = z.object({
  kind: z.literal('cms_page'),
  /// Slug d'une page CMS Flutter (jalon 3 : pages d'app pilotées CMS).
  /// Tant que le runtime Dart ne sait pas router une cms_page, l'item est
  /// ignoré côté tab bar (mais l'admin peut déjà la déclarer).
  slug: z.string().min(1),
})

const externalUrlSchema = z.object({
  kind: z.literal('external_url'),
  value: z.string().url(),
})

export const appMobileTargetSchema = z.discriminatedUnion('kind', [
  nativeTabSchema,
  cmsPageSchema,
  externalUrlSchema,
])

export type AppMobileTarget = z.infer<typeof appMobileTargetSchema>

/// Catalogue d'icônes Material/Kalai consommables par le shell Flutter.
/// Ajouter ici une icône suppose qu'elle existe dans le mapping Dart
/// (`AppShellService.iconFor()`).
export const APP_MOBILE_ICON_KEYS = [
  'home_rounded',
  'trending_up_rounded',
  'currency_bitcoin',
  'radio_rounded',
  'search_rounded',
  'more_horiz_rounded',
] as const
export type AppMobileIconKey = (typeof APP_MOBILE_ICON_KEYS)[number]

const appMobileIconSchema = z.enum(APP_MOBILE_ICON_KEYS)

export const appMenuItemDataSchema = z.object({
  /// Id du `MenuItem` Prisma (lien fort entre la structure i18n et la cible).
  menuItemId: z.string().min(1),
  target: appMobileTargetSchema,
  icon: appMobileIconSchema,
})

export const appMenuSectionDataSchema = z.object({
  items: z.array(appMenuItemDataSchema).default([]),
})

export type AppMenuSectionData = z.infer<typeof appMenuSectionDataSchema>
export type AppMenuItemData = z.infer<typeof appMenuItemDataSchema>

/// Forme de sortie pour le contrat public (mobile) — labels localisés résolus.
export type AppShellTabPayload = {
  id: string
  order: number
  enabled: boolean
  label: string
  icon: AppMobileIconKey
  target: AppMobileTarget
}

export type AppShellPayload = {
  tabs: AppShellTabPayload[]
}

/// Set par défaut compilé : utilisé par le seed et comme **filet de secours**
/// côté Flutter en cas d'API indisponible. Doit refléter à 1:1 les 4 tabs
/// historiques de `MainShellScreen` (Home/Invest/Markets/Design).
///
/// Le bouton « Search » du shell reste un **action button** distinct côté
/// Flutter (pas dans la tab bar) — il sera intégré via une autre clé CMS dans
/// un sprint ultérieur si besoin.
export const DEFAULT_APP_MAIN_TABS: Array<{
  key: string
  order: number
  icon: AppMobileIconKey
  target: AppMobileTarget
  labels: Record<string, string>
}> = [
  {
    key: 'home',
    order: 0,
    icon: 'home_rounded',
    target: { kind: 'native_tab', value: 'home' },
    labels: { en: 'Home', fr: 'Accueil', it: 'Home' },
  },
  {
    key: 'offers',
    order: 1,
    icon: 'trending_up_rounded',
    target: { kind: 'native_tab', value: 'offers' },
    labels: { en: 'Invest', fr: 'Investir', it: 'Investi' },
  },
  {
    key: 'markets',
    order: 2,
    icon: 'currency_bitcoin',
    target: { kind: 'native_tab', value: 'markets' },
    labels: { en: 'Markets', fr: 'Markets', it: 'Mercati' },
  },
  {
    key: 'design_system',
    order: 3,
    icon: 'radio_rounded',
    target: { kind: 'native_tab', value: 'design_system' },
    labels: { en: 'Design', fr: 'Design', it: 'Design' },
  },
]

/**
 * Adaptateur « Vérifier la langue » du menu de navigation.
 *
 * Menu = tables `Menu` / `MenuItem` + traductions `MenuI18n` / `MenuItemI18n`
 * (locale-by-locale). Pas de notion DRAFT/PUBLISHED.
 *
 * Champs scannés (visibles côté navigation) :
 *   - `Menu.name` (résolu via `MenuI18n[locale].name` avec fallback `Menu.name`)
 *   - `MenuItem.label` (résolu via `MenuItemI18n[locale].label` avec
 *     fallback `MenuItem.label`)
 *
 * Volontairement exclus :
 *   - URLs, `buttonStyle`, `buttonAction`, `externalUrl` : ne sont pas du
 *     contenu textuel affiché à l'utilisateur en tant que copy.
 *   - Items `enabled: false` : non visibles côté site → on ne dépense pas
 *     d'OpenAI dessus.
 *   - Items vides après résolution.
 *
 * Le module ne persiste rien : il fournit l'extraction + un plan d'upserts
 * que la route API exécute (`{ menuI18nPatch?, itemI18nPatches[] }`).
 */

import type { Locale } from '@/config/locales'

import {
  applyFieldsLanguageFixes,
  buildLanguageHintsFromGenericScan,
  scanFieldsLanguageDeep,
  type GenericApplyResult,
  type GenericFieldInput,
  type GenericScanResult,
} from '@/lib/admin/i18n/genericLanguageCheck'
import type { BatchLanguageRefiner } from '@/lib/i18n/llm/batchClassifyLanguages'

const DOMAIN = 'menu'

const HINT_KEY_MENU_NAME = 'menu.name'
const ITEM_HINT_PREFIX = 'item:'

function makeItemHintKey(itemId: string): string {
  return `${ITEM_HINT_PREFIX}${itemId}.label`
}

function makeItemPath(index: number): string {
  return `items[${index}].label`
}

/* -------------------------------------------------------------------------- */
/* Types d'entrée                                                              */
/* -------------------------------------------------------------------------- */

export type MenuInputForScan = {
  id: string
  name: string
  /** Lignes `MenuI18n` de la base. */
  i18n: Array<{ locale: string; name: string }>
}

export type MenuItemInputForScan = {
  id: string
  /** Index d'ordre stable (sert de groupLabel UI). */
  index: number
  enabled: boolean
  baseLabel: string
  /** Lignes `MenuItemI18n` de la base. */
  i18n: Array<{ locale: string; label: string }>
}

/* -------------------------------------------------------------------------- */
/* Extraction                                                                  */
/* -------------------------------------------------------------------------- */

/**
 * Construit la liste plate de champs à scanner pour un menu et ses items
 * pour la `targetLocale`.
 *
 * Pour chaque champ : on prend la valeur localisée si elle existe (depuis
 * `MenuI18n` / `MenuItemI18n` pour la locale cible), sinon on tombe sur le
 * label/name de base. C'est exactement ce que voit l'utilisateur final via
 * `resolveLabelWithFallback` dans `getPrimaryMenu`.
 */
export function extractMenuFields(
  menu: MenuInputForScan,
  items: MenuItemInputForScan[],
  targetLocale: Locale,
): GenericFieldInput[] {
  const fields: GenericFieldInput[] = []

  const menuI18n = menu.i18n.find((r) => r.locale === targetLocale)
  const menuValue = (menuI18n?.name ?? menu.name ?? '').trim()
  if (menuValue) {
    fields.push({
      hintKey: HINT_KEY_MENU_NAME,
      path: 'menu.name',
      value: menuValue,
      kind: 'plain',
      domain: DOMAIN,
      groupId: 'menu',
      groupLabel: 'Menu',
      // `menu.name` est par nature un en-tête court traductible (pas un nom
      // propre comme `data.author.name`) → on bypasse `isShortHeaderPath`
      // qui ne reconnaît que `eyebrow|label|kicker|title|subtitle$`.
      isShortHeader: true,
    })
  }

  for (const item of items) {
    if (!item.enabled) continue
    const i18n = item.i18n.find((r) => r.locale === targetLocale)
    const value = (i18n?.label ?? item.baseLabel ?? '').trim()
    if (!value) continue
    fields.push({
      hintKey: makeItemHintKey(item.id),
      path: makeItemPath(item.index),
      value,
      kind: 'plain',
      domain: DOMAIN,
      groupId: `item:${item.id}`,
      groupLabel: `Item #${item.index + 1}`,
      // Cohérence : un label de menu est lui aussi par essence un short
      // header. `items[i].label` matche déjà la regex via `label$`, mais on
      // marque explicitement pour ne pas dépendre du naming du path.
      isShortHeader: true,
    })
  }

  return fields
}

/* -------------------------------------------------------------------------- */
/* Projection apply → plan d'upserts                                          */
/* -------------------------------------------------------------------------- */

export type MenuI18nUpsertPlan = {
  /** Nouveau `MenuI18n.name` (si modifié). */
  menuI18nName?: string
  /** Map `menuItemId` → nouveau `MenuItemI18n.label`. */
  itemI18nLabelByItemId: Map<string, string>
}

/**
 * Re-projette la sortie générique d'apply en un plan d'upserts spécifique
 * au domain menu : `MenuI18n.name` + `MenuItemI18n.label` par `menuItemId`.
 */
export function buildMenuUpsertPlanFromFixed(
  fixedByHintKey: Map<string, string>,
): MenuI18nUpsertPlan {
  const plan: MenuI18nUpsertPlan = {
    itemI18nLabelByItemId: new Map(),
  }
  for (const [hintKey, newValue] of fixedByHintKey.entries()) {
    if (hintKey === HINT_KEY_MENU_NAME) {
      plan.menuI18nName = newValue
      continue
    }
    if (hintKey.startsWith(ITEM_HINT_PREFIX)) {
      // `item:<id>.label`
      const after = hintKey.slice(ITEM_HINT_PREFIX.length)
      const dotIdx = after.lastIndexOf('.')
      if (dotIdx <= 0) continue
      const itemId = after.slice(0, dotIdx)
      plan.itemI18nLabelByItemId.set(itemId, newValue)
    }
  }
  return plan
}

/* -------------------------------------------------------------------------- */
/* Façades scan / apply                                                        */
/* -------------------------------------------------------------------------- */

export async function scanMenuLanguageDeep(
  menu: MenuInputForScan,
  items: MenuItemInputForScan[],
  targetLocale: Locale,
  options?: { refiner?: BatchLanguageRefiner },
): Promise<GenericScanResult> {
  const fields = extractMenuFields(menu, items, targetLocale)
  return scanFieldsLanguageDeep(fields, targetLocale, options)
}

export async function applyMenuLanguageFixes(
  menu: MenuInputForScan,
  items: MenuItemInputForScan[],
  targetLocale: Locale,
  options?: {
    refiner?: BatchLanguageRefiner
    scan?: GenericScanResult
  },
): Promise<{
  upsertPlan: MenuI18nUpsertPlan
  apply: GenericApplyResult
  scan: GenericScanResult
}> {
  const fields = extractMenuFields(menu, items, targetLocale)
  const scan =
    options?.scan ?? (await scanFieldsLanguageDeep(fields, targetLocale, options))
  const languageHints = buildLanguageHintsFromGenericScan(scan)
  const apply = await applyFieldsLanguageFixes(fields, targetLocale, { languageHints })
  const upsertPlan = buildMenuUpsertPlanFromFixed(apply.fixedByHintKey)
  return { upsertPlan, apply, scan }
}

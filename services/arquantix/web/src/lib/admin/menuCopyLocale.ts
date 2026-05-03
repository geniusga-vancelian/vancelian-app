/**
 * Copie « FR (ou autre source) → locale cible » du menu de navigation.
 *
 * Aligné sur le standard Pages (`/api/admin/pages/[slug]/copy-locale-content`)
 * et Footer (`SiteFooterEditor.handleCopyFromDefault`) :
 *   - Étape 1 du workflow utilisateur (« copier le contenu FR vers EN/IT »)
 *     qui matérialise les rangées `MenuI18n[targetLocale]` /
 *     `MenuItemI18n[targetLocale]` à partir du nom et des labels source
 *     (résolution par fallback `i18n[sourceLocale]?.label ?? baseLabel`).
 *   - Sert de base au scan + correction IA qui suit (« Vérifier la langue »
 *     puis « Corriger la langue »).
 *
 * Module **pur** (aucune dépendance Prisma) : prend en entrée la même forme
 * lue par `menuCheckLanguage.ts` (`MenuInputForScan`/`MenuItemInputForScan`)
 * et produit un plan d'upserts que la route API persiste.
 *
 * Garanties :
 *   - jamais de mutation in-place sur les inputs ;
 *   - filtrage des items `enabled: false` (pas visibles côté site) ;
 *   - skip silencieux des libellés source vides après trim ;
 *   - mode `'missing'` par défaut (n'écrase pas une traduction existante) ;
 *   - `sourceLocale === targetLocale` rejeté en amont par la route.
 */

import type { Locale } from '@/config/locales'
import type {
  MenuInputForScan,
  MenuItemInputForScan,
} from '@/lib/admin/menuCheckLanguage'

/** Mode de copie aligné sur `translate/menu` : ne pas écraser les traductions existantes par défaut. */
export type MenuCopyMode = 'missing' | 'overwrite'

export type MenuCopyPlan = {
  /** Nouveau `MenuI18n.name` à upserter pour `targetLocale`, ou `undefined` si rien à copier. */
  menuI18nName?: string
  /**
   * Map `menuItemId` → nouveau `MenuItemI18n.label` à upserter pour `targetLocale`.
   * Les items absents de la map ne doivent **pas** être touchés.
   */
  itemI18nLabelByItemId: Map<string, string>
  /** Diagnostics utiles pour la modale UI / réponse API. */
  diagnostics: {
    /** L'item a été ajouté au plan. */
    copied: string[]
    /** L'item avait déjà une traduction → préservée (mode `'missing'`). */
    skippedExisting: string[]
    /** Source vide après trim → rien à copier. */
    skippedEmptySource: string[]
    /** Item `enabled: false` → ignoré. */
    skippedDisabled: string[]
    /** Le menu lui-même : statut. */
    menuName: 'copied' | 'skippedExisting' | 'skippedEmptySource'
  }
}

/**
 * Résout la valeur source d'un libellé pour `sourceLocale` selon la même règle
 * que `extractMenuFields` du scan : `i18n[sourceLocale]?.label ?? baseLabel`.
 *
 * Cette homogénéité est essentielle pour que :
 *   1. ce que l'opérateur copie correspond à ce qu'il voit dans l'éditeur en
 *      langue source ;
 *   2. le scan (qui utilise la même règle) raisonne sur la même donnée que la
 *      copie matérialisée ensuite.
 */
function resolveSourceLabel(
  i18nRows: Array<{ locale: string; label: string }>,
  baseLabel: string,
  sourceLocale: Locale,
): string {
  const sourceRow = i18nRows.find((r) => r.locale === sourceLocale)
  return (sourceRow?.label ?? baseLabel ?? '').trim()
}

function resolveSourceMenuName(
  menu: MenuInputForScan,
  sourceLocale: Locale,
): string {
  const row = menu.i18n.find((r) => r.locale === sourceLocale)
  return (row?.name ?? menu.name ?? '').trim()
}

/**
 * Calcule le plan de copie (sans persister).
 *
 * @param menu  données menu déjà chargées (mêmes types que pour le scan).
 * @param items items du menu, dans l'ordre.
 * @param sourceLocale  locale source (typiquement `defaultLocale`).
 * @param targetLocale  locale cible (différente de `sourceLocale`).
 * @param mode  `'missing'` (défaut) ne touche pas aux libellés cible déjà
 *   présents et non vides ; `'overwrite'` écrase tout.
 *
 * @throws si `sourceLocale === targetLocale` (à valider en amont par la route).
 */
export function buildMenuCopyPlan(
  menu: MenuInputForScan,
  items: MenuItemInputForScan[],
  sourceLocale: Locale,
  targetLocale: Locale,
  mode: MenuCopyMode = 'missing',
): MenuCopyPlan {
  if (sourceLocale === targetLocale) {
    throw new Error(
      'buildMenuCopyPlan: sourceLocale et targetLocale doivent différer',
    )
  }

  const plan: MenuCopyPlan = {
    itemI18nLabelByItemId: new Map(),
    diagnostics: {
      copied: [],
      skippedExisting: [],
      skippedEmptySource: [],
      skippedDisabled: [],
      menuName: 'skippedEmptySource',
    },
  }

  const sourceMenuName = resolveSourceMenuName(menu, sourceLocale)
  if (sourceMenuName) {
    const existingTargetMenuName = menu.i18n
      .find((r) => r.locale === targetLocale)
      ?.name?.trim()
    if (mode === 'missing' && existingTargetMenuName) {
      plan.diagnostics.menuName = 'skippedExisting'
    } else {
      plan.menuI18nName = sourceMenuName
      plan.diagnostics.menuName = 'copied'
    }
  } else {
    plan.diagnostics.menuName = 'skippedEmptySource'
  }

  for (const item of items) {
    if (!item.enabled) {
      plan.diagnostics.skippedDisabled.push(item.id)
      continue
    }

    const sourceValue = resolveSourceLabel(item.i18n, item.baseLabel, sourceLocale)
    if (!sourceValue) {
      plan.diagnostics.skippedEmptySource.push(item.id)
      continue
    }

    const existingTarget = item.i18n
      .find((r) => r.locale === targetLocale)
      ?.label?.trim()
    if (mode === 'missing' && existingTarget) {
      plan.diagnostics.skippedExisting.push(item.id)
      continue
    }

    plan.itemI18nLabelByItemId.set(item.id, sourceValue)
    plan.diagnostics.copied.push(item.id)
  }

  return plan
}

/**
 * Plan « Tout enregistrer pour cette locale » du menu admin
 * (alignement strict avec le bouton « Enregistrer » du SiteFooterEditor).
 *
 * Sémantique :
 *   - regroupe en une seule transaction toutes les éditions inline en mémoire
 *     pour la locale active (input « Menu Name » + accordéons « Localized
 *     Names » et « Localized Labels » par item) ;
 *   - persiste avec `translationStatus: ORIGINAL` (= « édition humaine
 *     validée », distinct de `MACHINE` posé par la correction IA) ;
 *   - ignore silencieusement les valeurs vides (pas d'écrasement par chaîne
 *     vide, qui produirait un libellé vide côté navigation publique) ;
 *   - sur la locale par défaut, met aussi à jour `Menu.name` (base partagée
 *     entre toutes les locales) car c'est la source résolue par défaut ;
 *   - hors locale par défaut, ne touche **jamais** à `Menu.name` ni à
 *     `MenuItem.label` (= structure, verrouillée par `menuEditorPolicy`).
 *
 * Cette fonction est pure : aucune dépendance Prisma ni IO. Elle est
 * réutilisée par la route `POST /api/admin/menus/[key]/save-locale` ainsi
 * que par les tests unitaires (anti-régression sur le périmètre de save).
 */

import { defaultLocale, type Locale } from '@/config/locales'

export type MenuSaveLocaleInput = {
  /** Locale courante éditée par l'opérateur (= `activeLocale`). */
  activeLocale: Locale
  /**
   * Locale par défaut du site (= `defaultLocale`). Si `activeLocale ===
   * defaultLocale`, on autorise l'écriture de `Menu.name` (base).
   */
  defaultLocale: Locale
  /**
   * Valeur de l'input « Menu Name » du formulaire admin. Pris en compte
   * uniquement si `activeLocale === defaultLocale`. Sinon : ignoré (la
   * structure est verrouillée hors locale par défaut).
   */
  menuNameInput?: string
  /**
   * Valeur de l'accordéon « Localized Names » pour `activeLocale`. Si non
   * vide, sera upserté dans `MenuI18n[activeLocale].name`.
   */
  menuI18nName?: string
  /**
   * Pour chaque `menuItemId`, libellé saisi (ou rechargé) dans l'accordéon
   * « Localized Labels » pour `activeLocale`. Les valeurs vides sont
   * ignorées (pas d'écrasement). Les items absents de la map ne sont pas
   * touchés.
   */
  itemLabels?: Record<string, string>
}

export type MenuSaveLocalePlan = {
  /** À écrire dans `Menu.name` (uniquement quand activeLocale = défaut). */
  menuNameToWrite?: string
  /** À upsert dans `MenuI18n[activeLocale].name` (statut ORIGINAL). */
  menuI18nNameToWrite?: string
  /** Map `menuItemId → label` à upsert dans `MenuItemI18n[activeLocale]`. */
  itemLabelsToWrite: Map<string, string>
  diagnostics: {
    /** Items effectivement à écrire. */
    itemsWritten: string[]
    /** Items présents dans l'input mais avec une valeur vide → ignorés. */
    itemsSkippedEmpty: string[]
    /** True si on va aussi update Menu.name (base FR). */
    didWriteMenuNameBase: boolean
    /** True si on va upsert MenuI18n. */
    didWriteMenuI18nName: boolean
  }
}

function isNonEmpty(s: string | undefined | null): s is string {
  return typeof s === 'string' && s.trim().length > 0
}

export function buildMenuSaveLocalePlan(
  input: MenuSaveLocaleInput,
): MenuSaveLocalePlan {
  const { activeLocale, menuNameInput, menuI18nName, itemLabels } = input
  const isDefaultLocale = activeLocale === input.defaultLocale

  const itemLabelsToWrite = new Map<string, string>()
  const itemsWritten: string[] = []
  const itemsSkippedEmpty: string[] = []

  if (itemLabels) {
    for (const [itemId, raw] of Object.entries(itemLabels)) {
      if (!isNonEmpty(raw)) {
        itemsSkippedEmpty.push(itemId)
        continue
      }
      const trimmed = raw.trim()
      itemLabelsToWrite.set(itemId, trimmed)
      itemsWritten.push(itemId)
    }
  }

  const menuI18nNameToWrite = isNonEmpty(menuI18nName)
    ? menuI18nName.trim()
    : undefined

  // `Menu.name` (base) : seulement quand activeLocale = defaultLocale.
  // C'est la source de vérité résolue par `getPrimaryMenu` quand aucune
  // traduction n'est trouvée.
  const menuNameToWrite =
    isDefaultLocale && isNonEmpty(menuNameInput) ? menuNameInput.trim() : undefined

  return {
    menuNameToWrite,
    menuI18nNameToWrite,
    itemLabelsToWrite,
    diagnostics: {
      itemsWritten,
      itemsSkippedEmpty,
      didWriteMenuNameBase: menuNameToWrite !== undefined,
      didWriteMenuI18nName: menuI18nNameToWrite !== undefined,
    },
  }
}

/**
 * Helper utilisé par les pages admin pour assembler le payload qu'elles
 * envoient à `/api/admin/menus/[key]/save-locale`. Garde le couplage
 * client/serveur fort et testable d'un seul côté.
 *
 * Conventions :
 *   - `i18nLabels` : state `Record<itemId, Record<locale, label>>` du form
 *     admin (à filtrer pour `activeLocale`) ;
 *   - `menuI18nNames` : state `Record<locale, name>` du form admin.
 */
export function selectActiveLocaleEditsForSave(args: {
  activeLocale: Locale
  i18nLabels: Record<string, Record<string, string>>
  menuI18nNames: Record<string, string>
}): { itemLabels: Record<string, string>; menuI18nName?: string } {
  const itemLabels: Record<string, string> = {}
  for (const [itemId, byLocale] of Object.entries(args.i18nLabels)) {
    const v = byLocale?.[args.activeLocale]
    if (typeof v === 'string') {
      itemLabels[itemId] = v
    }
  }
  const menuI18nName = args.menuI18nNames?.[args.activeLocale]
  return {
    itemLabels,
    menuI18nName: typeof menuI18nName === 'string' ? menuI18nName : undefined,
  }
}

// Réexport pratique pour les consommateurs.
export { defaultLocale }

/**
 * Politique pure (sans React) qui matérialise le contrat d'alignement UX
 * Footer ↔ Menu pour la page admin du menu primary :
 *
 *   - `activeLocale` est l'unique concept de locale active : il pilote
 *     simultanément l'éditeur (libellés résolus), le bouton « Copier
 *     depuis FR », et le bandeau « Contrôle linguistique » (scan+apply).
 *   - Quand `activeLocale === defaultLocale`, la structure (items, ordre,
 *     type, page cible, externalUrl, enabled, nom du menu, copyright, etc.)
 *     est éditable. Sinon elle est verrouillée — seuls les libellés
 *     localisés (MenuI18n / MenuItemI18n) sont modifiables, via le panneau
 *     « Localized Labels » par item, le bouton « Copier depuis FR », ou le
 *     contrôle linguistique IA.
 *   - L'option « Copier depuis FR » est inutile/désactivée tant que
 *     `activeLocale === defaultLocale`.
 *
 * Cette politique est extraite et testée en pur pour garantir un garde-fou
 * anti-régression : tout changement futur du composant React doit continuer
 * à respecter ces invariants. Une réécriture du JSX doit consommer ces
 * helpers (ou être ajustée pour rester équivalente).
 */

import type { Locale } from '@/config/locales'

export type MenuEditorPolicy = {
  /** La locale en cours d'édition, source de vérité unique pour l'UI. */
  activeLocale: Locale
  /** Locale considérée comme « source de structure » (typiquement `defaultLocale`). */
  defaultLocale: Locale
  /**
   * `true` quand on édite une locale ≠ defaultLocale : la structure du
   * menu est partagée entre toutes les locales par design (relationnel),
   * donc on ne l'édite qu'une seule fois, depuis la locale par défaut.
   */
  isStructureLocked: boolean
  /** Le bouton « Copier depuis FR » est-il pertinent (≠ defaultLocale) ? */
  canCopyFromDefault: boolean
  /**
   * Locale ciblée par le bouton « Copier depuis FR » lorsqu'il est cliqué.
   * Toujours = activeLocale (alignement Footer : pas de sélecteur cible
   * indépendant).
   */
  copyTarget: Locale
  /**
   * Locale utilisée par `LanguageCheckActions` pour le scan + apply.
   * Toujours = activeLocale (alignement Footer : un seul concept).
   */
  languageCheckLocale: Locale
}

/**
 * Construit la politique d'édition selon la locale active et la locale par
 * défaut. C'est la fonction qui doit rester en cohérence avec tous les
 * `disabled={...}`, `readOnly={...}` et props `activeLocale={...}` dans le
 * composant React.
 */
export function computeMenuEditorPolicy(
  activeLocale: Locale,
  defaultLocale: Locale,
): MenuEditorPolicy {
  const isStructureLocked = activeLocale !== defaultLocale
  return {
    activeLocale,
    defaultLocale,
    isStructureLocked,
    canCopyFromDefault: isStructureLocked,
    copyTarget: activeLocale,
    languageCheckLocale: activeLocale,
  }
}

/**
 * Sélectionne la valeur affichée pour `Menu.name` dans l'input éditeur, en
 * fonction de la locale active :
 *   - locale par défaut → on édite le `nameBase` (= `Menu.name` de la base) ;
 *   - autre locale → on affiche la valeur résolue (`MenuI18n[locale].name`
 *     ou fallback) en lecture seule.
 *
 * Cette dérivation reproduit la règle exacte de
 * `services/arquantix/web/src/app/admin/pages/menu/page.tsx:fetchMenu`.
 */
export function selectMenuNameToDisplay(args: {
  activeLocale: Locale
  defaultLocale: Locale
  /** `Menu.name` de la base (toujours présent côté serveur). */
  nameBase: string
  /**
   * Nom résolu par le serveur pour `activeLocale` via
   * `resolveLabelWithFallback` (= `MenuI18n[activeLocale].name` ou
   * fallback `defaultLocale` ou `nameBase`).
   */
  resolvedName: string
}): string {
  return args.activeLocale === args.defaultLocale
    ? args.nameBase || args.resolvedName
    : args.resolvedName
}

/**
 * Garde-fou i18n du Vault public.
 *
 * Détecte les chaînes user-facing hardcodées dans le périmètre
 * `services/arquantix/web/src/components/exclusive-offer/**`.
 *
 * Convention rappelée :
 *   - Contenu spécifique au module → prop CMS traduisible (ex. `moduleTitle`, `ctaLabel`).
 *   - Libellé générique d'UI       → `vaultCommonCta(locale, key)` (mutualisé FR / EN / IT).
 *   - Aucun texte user-facing hardcodé dans le rendu JSX du périmètre.
 *
 * La logique de scan (regex, heuristiques, allowlist) est mutualisée dans
 * `i18nHardcodedStringsScanner.ts` pour rester alignée avec le scanner du site
 * public (`siteHardcodedStringsScanner.ts`). Ce module reste l'API publique
 * historique : ses exports doivent rester stables pour `vaultHardcodedStringsScanner.test.ts`.
 */

import { scanScopes, type HardcodedFinding } from '@/lib/i18n/i18nHardcodedStringsScanner'

export {
  scanFileForHardcodedStrings,
  formatFindingsForReport,
  type HardcodedFinding,
} from '@/lib/i18n/i18nHardcodedStringsScanner'

export function scanVaultExclusiveOfferDirectory(rootDir: string): HardcodedFinding[] {
  return scanScopes([{ rootDir }])
}

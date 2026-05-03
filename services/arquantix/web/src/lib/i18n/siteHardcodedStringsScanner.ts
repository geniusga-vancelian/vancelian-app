/**
 * Garde-fou i18n du site public Arquantix.
 *
 * Détecte les chaînes user-facing hardcodées dans les composants rendus en
 * front public hors Vault :
 *   - `components/sections/**` (header / footer / sections de pages)
 *   - `components/site/**`     (chrome global, footer wrapper)
 *   - `components/layout/**`   (LanguageSwitcher, layouts publics)
 *   - `components/cms/**`      (SectionRenderer, CmsDatabaseUnavailable)
 *
 * Convention rappelée :
 *   - Contenu spécifique à une page / section → prop CMS traduisible.
 *   - Libellé générique d'UI                  → `siteCommonCta(locale, key)`.
 *   - Aucun texte user-facing hardcodé dans le rendu JSX du périmètre.
 *
 * Exclusions :
 *   - `components/sections/SectionAlternate.tsx` et `SectionHowItWorks.tsx` :
 *     showcases dev rendus uniquement dans `/figma`, marqués `@deprecated` et
 *     allowlistés via `// i18n-allow-file` (cf. Lot E).
 *   - `components/cms/CmsDatabaseUnavailable.tsx` : message admin/debug.
 *
 * La logique de scan est mutualisée dans `i18nHardcodedStringsScanner.ts`
 * (alignement avec le scanner Vault).
 *
 * Allowlist :
 *   - `// i18n-allow-next-line: <raison>`              (commentaire JS)
 *   - `{/* i18n-allow-next-line: <raison> *\u002F}`    (commentaire JSX)
 *   - `// i18n-allow-file: <raison>`                   (fichier entier)
 */

import path from 'node:path'

import {
  scanScopes,
  type HardcodedFinding,
} from '@/lib/i18n/i18nHardcodedStringsScanner'

export {
  scanFileForHardcodedStrings,
  formatFindingsForReport,
  type HardcodedFinding,
} from '@/lib/i18n/i18nHardcodedStringsScanner'

/**
 * Configuration du périmètre site public.
 * Les chemins sont relatifs au dossier `services/arquantix/web/src`.
 */
export const SITE_SCAN_DIRS_RELATIVE = [
  'components/sections',
  'components/site',
  'components/layout',
  'components/cms',
] as const

/** Sous-dossiers à exclure (relatifs à `src/`). */
export const SITE_SCAN_EXCLUDE_DIRS_RELATIVE: readonly string[] = []

/**
 * Fichiers exclus (chemins relatifs à `src/`).
 *
 * - `components/cms/CmsDatabaseUnavailable.tsx` : message admin/debug visible
 *   uniquement quand la base est injoignable (DX dev), pas un cas user-facing
 *   normal en production.
 *
 * Les composants showcase (`SectionAlternate`, `SectionHowItWorks`) sont
 * exemptés via `// i18n-allow-file` directement dans leur source (Lot E).
 */
export const SITE_SCAN_EXCLUDE_FILES_RELATIVE: readonly string[] = [
  'components/cms/CmsDatabaseUnavailable.tsx',
]

/**
 * Scanne le périmètre site public à partir du dossier `src/` du repo web.
 */
export function scanSitePublicScopes(srcDir: string): HardcodedFinding[] {
  return scanScopes(
    SITE_SCAN_DIRS_RELATIVE.map((rel) => ({
      rootDir: path.join(srcDir, rel),
      excludeFiles: SITE_SCAN_EXCLUDE_FILES_RELATIVE.map((f) =>
        path.join(srcDir, f),
      ),
      excludeDirs: SITE_SCAN_EXCLUDE_DIRS_RELATIVE.map((d) =>
        path.join(srcDir, d),
      ),
    })),
  )
}

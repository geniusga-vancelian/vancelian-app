import { promises as fs } from 'node:fs'
import path from 'node:path'

/**
 * Parser ARB (Application Resource Bundle, format Flutter).
 *
 * Spec : https://github.com/google/app-resource-bundle/wiki/ApplicationResourceBundleSpecification
 *
 * Forme attendue :
 * ```
 * {
 *   "@@locale": "en",
 *   "exclusiveOfferInvestCtaDefault": "Invest",
 *   "@exclusiveOfferInvestCtaDefault": {
 *     "description": "CTA on the exclusive offer card.",
 *     "placeholders": { "amount": { "type": "double" } }
 *   }
 * }
 * ```
 *
 * Le parser ignore tout `@@*` (metadata top-level) et associe les `@<key>`
 * aux entrées correspondantes.
 *
 * **Note key naming** : les keys ARB historiques Flutter sont en `camelCase`
 * (ex. `exclusiveOfferInvestCtaDefault`). Nos overrides CMS visent une
 * taxonomie plus structurée (`module.exclusive_offer.cta.invest`), mais le
 * pont entre les deux n'est pas obligatoire à l'extraction : on conserve la
 * key ARB telle quelle (=> namespace `misc` par défaut) et l'admin peut
 * ensuite renommer (Stratégie 2). Le mapping ARB→namespace structuré est
 * fait dans le mapping de migration des 3 strings de démo (`legacyArbKeyMap`).
 */
export type ArbEntry = {
  key: string
  value: string
  description?: string
  /// JSON ICU des placeholders (ex. `{ "count": { "type": "int" } }`).
  placeholders?: Record<string, unknown>
}

export type ArbFile = {
  locale: string
  entries: ArbEntry[]
  rawPath: string
}

/// Lit un fichier ARB et renvoie ses entrées normalisées.
export async function readArbFile(filePath: string): Promise<ArbFile> {
  const raw = await fs.readFile(filePath, 'utf8')
  const json = JSON.parse(raw) as Record<string, unknown>
  const locale = (typeof json['@@locale'] === 'string' && json['@@locale']) || ''
  if (!locale) {
    throw new Error(`ARB file ${filePath} is missing @@locale.`)
  }

  const entries: ArbEntry[] = []
  for (const [key, value] of Object.entries(json)) {
    if (key.startsWith('@')) continue
    if (typeof value !== 'string') continue
    const meta = json[`@${key}`]
    let description: string | undefined
    let placeholders: Record<string, unknown> | undefined
    if (meta && typeof meta === 'object') {
      const m = meta as Record<string, unknown>
      if (typeof m.description === 'string') description = m.description
      if (m.placeholders && typeof m.placeholders === 'object') {
        placeholders = m.placeholders as Record<string, unknown>
      }
    }
    entries.push({ key, value, description, placeholders })
  }

  return { locale, entries, rawPath: filePath }
}

/**
 * Lit tous les fichiers ARB d'un dossier (`app_<locale>.arb`).
 *
 * Convention Flutter : un fichier par locale, le `template-arb-file`
 * (`app_en.arb` pour Arquantix) sert de source canonique.
 */
export async function readArbDirectory(arbDir: string): Promise<ArbFile[]> {
  const files = await fs.readdir(arbDir)
  const arbs = files.filter((f) => f.startsWith('app_') && f.endsWith('.arb'))
  const out: ArbFile[] = []
  for (const f of arbs) {
    out.push(await readArbFile(path.join(arbDir, f)))
  }
  return out.sort((a, b) => a.locale.localeCompare(b.locale))
}

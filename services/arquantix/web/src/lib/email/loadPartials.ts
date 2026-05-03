import { promises as fs } from 'node:fs'
import path from 'node:path'
import { MJML_PATHS } from './mjmlRender'

/**
 * Charge tous les fragments MJML sous `emails/mjml/partials/` et `components/`
 * pour les rendre disponibles comme partials Mustache (`{{> head}}`,
 * `{{> Button}}`, …). La clé est le **basename sans extension**, donc
 * `components/Button.mjml` → `Button`.
 *
 * Cache simple en mémoire : les partials sont chargés une fois par process,
 * suffisant pour les rendus serveur. Pour le hot-reload en dev, redémarrer
 * `npm run emails:preview`.
 */
let cached: Record<string, string> | null = null

export async function loadEmailPartials(force = false): Promise<Record<string, string>> {
  if (cached && !force) return cached
  const partials: Record<string, string> = {}
  for (const dir of [MJML_PATHS.partials, MJML_PATHS.components]) {
    await collectInto(dir, partials)
  }
  cached = partials
  return partials
}

async function collectInto(dir: string, target: Record<string, string>): Promise<void> {
  let entries: Array<{ name: string; isFile: boolean }> = []
  try {
    const raw = await fs.readdir(dir, { withFileTypes: true })
    entries = raw.map((e) => ({ name: e.name, isFile: e.isFile() }))
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') return
    throw e
  }
  for (const entry of entries) {
    if (!entry.isFile) continue
    if (!entry.name.endsWith('.mjml')) continue
    const key = entry.name.replace(/\.mjml$/, '')
    if (key.startsWith('_')) continue
    const source = await fs.readFile(path.join(dir, entry.name), 'utf8')
    target[key] = source
  }
}

/** Réinitialise le cache (utile pour les tests). */
export function resetEmailPartialsCache(): void {
  cached = null
}

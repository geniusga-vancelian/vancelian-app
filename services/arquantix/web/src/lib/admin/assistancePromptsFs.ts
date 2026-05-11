/**
 * Lecture des fichiers Markdown de prompts assistance (côté API Next).
 *
 * Source : `services/arquantix/api/services/assistance/prompts/`
 *
 * Définir `ASSISTANCE_PROMPTS_ROOT` en prod si la racine monorepo n'est pas disponible.
 */
import fs from 'fs/promises'
import path from 'path'

export function getAssistancePromptsRoot(): string {
  const env = process.env.ASSISTANCE_PROMPTS_ROOT
  if (env?.trim()) {
    return path.resolve(env.trim())
  }
  return path.resolve(
    process.cwd(),
    '..',
    'api',
    'services',
    'assistance',
    'prompts'
  )
}

function isInsideRoot(root: string, target: string): boolean {
  const rel = path.relative(root, target)
  return rel !== '' && !rel.startsWith('..') && !path.isAbsolute(rel)
}

/** Résout un chemin `.md` sûr sous la racine prompts (pas de `..`). */
export function resolveSafePromptFile(
  root: string,
  relativePath: string
): string | null {
  const normalized = relativePath.replace(/\\/g, '/').replace(/^\/+/, '').trim()
  if (!normalized || normalized.includes('..')) return null
  if (!normalized.endsWith('.md')) return null
  const full = path.resolve(root, normalized)
  if (!isInsideRoot(root, full)) return null
  return full
}

export async function assistancePromptsRootExists(): Promise<boolean> {
  try {
    await fs.access(getAssistancePromptsRoot(), fs.constants.R_OK)
    return true
  } catch {
    return false
  }
}

export async function listPromptMarkdownFiles(): Promise<string[]> {
  const root = getAssistancePromptsRoot()
  const out: string[] = []

  async function walk(dir: string, rel: string) {
    let entries: { name: string; isFile: () => boolean; isDirectory: () => boolean }[]
    try {
      entries = await fs.readdir(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (e.name.startsWith('.')) continue
      const r = rel ? `${rel}/${e.name}` : e.name
      const full = path.join(dir, e.name)
      if (e.isDirectory()) {
        await walk(full, r)
      } else if (e.isFile() && e.name.endsWith('.md')) {
        out.push(r.replace(/\\/g, '/'))
      }
    }
  }

  await walk(root, '')
  return out
}

export async function readPromptFile(relativePath: string): Promise<{
  content: string
  resolvedPath: string
} | null> {
  const root = getAssistancePromptsRoot()
  const full = resolveSafePromptFile(root, relativePath)
  if (!full) return null
  try {
    const content = await fs.readFile(full, 'utf-8')
    return { content, resolvedPath: full }
  } catch {
    return null
  }
}

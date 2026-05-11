/**
 * Lecture / écriture du wiki markdown assistance (Phase 2 produit).
 * Source de vérité filesystem : `api/services/assistance/data/wiki/`
 * (cf. `services/assistance/agents/repositories/wiki_repo.py`).
 *
 * En production hors monorepo, définir `WIKI_MARKDOWN_ROOT` vers ce dossier.
 */

import fs from 'fs/promises'
import type { Dirent } from 'fs'
import path from 'path'

import {
  WIKI_FAQ_CATEGORIES,
  WIKI_NON_FAQ_DIRS,
  type WikiTreeNode,
} from '@/lib/admin/assistanceWikiShared'

export type { WikiTreeNode }
export { WIKI_FAQ_CATEGORIES, WIKI_NON_FAQ_DIRS }

export function getWikiRoot(): string {
  const env = process.env.WIKI_MARKDOWN_ROOT
  if (env && env.trim()) {
    return path.resolve(env.trim())
  }
  return path.resolve(process.cwd(), '..', 'api', 'services', 'assistance', 'data', 'wiki')
}

function isInsideRoot(root: string, target: string): boolean {
  const rel = path.relative(root, target)
  return rel !== '' && !rel.startsWith('..') && !path.isAbsolute(rel)
}

/** Résout un chemin relatif sûr sous la racine wiki ; uniquement fichiers `.md`. */
export function resolveSafeWikiFile(wikiRoot: string, relativePath: string): string | null {
  const normalized = relativePath.replace(/\\/g, '/').replace(/^\/+/, '').trim()
  if (!normalized || normalized.includes('..')) return null
  if (!normalized.endsWith('.md')) return null
  const full = path.resolve(wikiRoot, normalized)
  if (!isInsideRoot(wikiRoot, full)) return null
  return full
}

export async function wikiRootExists(): Promise<boolean> {
  try {
    await fs.access(getWikiRoot(), fs.constants.R_OK)
    return true
  } catch {
    return false
  }
}

async function buildTree(dir: string, baseRel: string): Promise<WikiTreeNode[]> {
  let entries: Dirent[]
  try {
    entries = await fs.readdir(dir, { withFileTypes: true })
  } catch {
    return []
  }

  const nodes: WikiTreeNode[] = []
  for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (e.name.startsWith('.')) continue
    const rel = baseRel ? `${baseRel}/${e.name}` : e.name
    const full = path.join(dir, e.name)
    if (e.isDirectory()) {
      const children = await buildTree(full, rel)
      if (children.length > 0) {
        nodes.push({ name: e.name, path: rel, type: 'dir', children })
      }
    } else if (e.isFile() && e.name.endsWith('.md')) {
      nodes.push({ name: e.name, path: rel, type: 'file' })
    }
  }
  return nodes
}

export async function listWikiTree(): Promise<{ root: string; nodes: WikiTreeNode[] }> {
  const root = getWikiRoot()
  const nodes = await buildTree(root, '')
  return { root, nodes }
}

export async function readWikiFile(relativePath: string): Promise<{ content: string } | { error: string }> {
  const wikiRoot = getWikiRoot()
  const full = resolveSafeWikiFile(wikiRoot, relativePath)
  if (!full) return { error: 'invalid_path' }
  try {
    const content = await fs.readFile(full, 'utf8')
    return { content }
  } catch {
    return { error: 'not_found' }
  }
}

export async function writeWikiFile(
  relativePath: string,
  content: string
): Promise<{ ok: true } | { error: string }> {
  const wikiRoot = getWikiRoot()
  const full = resolveSafeWikiFile(wikiRoot, relativePath)
  if (!full) return { error: 'invalid_path' }
  try {
    await fs.mkdir(path.dirname(full), { recursive: true })
    await fs.writeFile(full, content, 'utf8')
    return { ok: true }
  } catch {
    return { error: 'write_failed' }
  }
}

/**
 * Crée un nouveau fichier ; le répertoire parent doit déjà exister
 * (sauf parents auto pour `faq/<cat>/` — on crée la catégorie si besoin).
 */
export async function createWikiFile(
  relativePath: string,
  content: string
): Promise<{ ok: true } | { error: string }> {
  const wikiRoot = getWikiRoot()
  const full = resolveSafeWikiFile(wikiRoot, relativePath)
  if (!full) return { error: 'invalid_path' }
  try {
    await fs.access(full)
    return { error: 'already_exists' }
  } catch {
    // absent — OK
  }

  const parts = relativePath.replace(/\\/g, '/').split('/').filter(Boolean)
  const validation = validateNewWikiPath(parts)
  if (!validation.ok) return { error: validation.error }

  try {
    await fs.mkdir(path.dirname(full), { recursive: true })
    await fs.writeFile(full, content, 'utf8')
    return { ok: true }
  } catch {
    return { error: 'write_failed' }
  }
}

function validateNewWikiPath(parts: string[]): { ok: true } | { ok: false; error: string } {
  if (parts.length < 1) return { ok: false, error: 'invalid_path' }
  const last = parts[parts.length - 1]
  if (!last.endsWith('.md')) return { ok: false, error: 'invalid_path' }

  if (parts.length === 1) {
    return { ok: true }
  }

  if (parts[0] === 'faq' && parts.length >= 3) {
    const cat = parts[1]
    if (!WIKI_FAQ_CATEGORIES.includes(cat as (typeof WIKI_FAQ_CATEGORIES)[number])) {
      return { ok: false, error: 'invalid_faq_category' }
    }
    return { ok: true }
  }

  if (parts.length === 2 && WIKI_NON_FAQ_DIRS.includes(parts[0] as (typeof WIKI_NON_FAQ_DIRS)[number])) {
    return { ok: true }
  }

  if (parts[0] === 'faq') {
    return { ok: false, error: 'invalid_faq_path' }
  }

  return { ok: false, error: 'invalid_path' }
}

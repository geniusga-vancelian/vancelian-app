/**
 * Lecture de valeurs texte aux chemins Lot 1 (alignés auditVaultDraft / auditCmsSectionDraft).
 * Domaine CMS : les findings utilisent le préfixe `data.` — on navigue depuis la racine du JSON `SectionContent.data`.
 */

import type { IntegrityDomain } from '@/lib/i18n/integrity/types'

/** Découpe `modules[2].content.title` ou `keyStats[0].label` en segments. */
export function tokenizeLot1Path(path: string): Array<string | number> {
  const tokens: Array<string | number> = []
  let i = 0
  const s = path.trim()
  while (i < s.length) {
    if (s[i] === '.') {
      i++
      continue
    }
    if (/[a-zA-Z_]/.test(s[i]!)) {
      let j = i
      while (j < s.length && /[a-zA-Z0-9_]/.test(s[j]!)) j++
      tokens.push(s.slice(i, j))
      i = j
      continue
    }
    if (s[i] === '[') {
      const end = s.indexOf(']', i)
      if (end === -1) return tokens
      const n = Number(s.slice(i + 1, end))
      if (!Number.isNaN(n)) tokens.push(n)
      i = end + 1
      continue
    }
    i++
  }
  return tokens
}

function walk(obj: unknown, tokens: Array<string | number>): unknown {
  let cur: unknown = obj
  for (const t of tokens) {
    if (cur == null) return undefined
    if (typeof t === 'number') {
      cur = Array.isArray(cur) ? cur[t] : undefined
    } else {
      cur =
        typeof cur === 'object' && cur !== null && Object.prototype.hasOwnProperty.call(cur, t)
          ? (cur as Record<string, unknown>)[t]
          : undefined
    }
  }
  return cur
}

/**
 * Extrait une chaîne au chemin Lot 1.
 * - `vault` : chemin depuis la racine du JSON vault (ex. `pageTitle.text`, `modules[0].content.title`).
 * - `cms_section` : chemin type `data.title` → navigation depuis `root` (déjà égal à `data`).
 */
export function getStringAtLot1Path(
  root: unknown,
  domain: IntegrityDomain,
  fieldPath: string,
): string | undefined {
  let path = fieldPath
  if (domain === 'cms_section' && path.startsWith('data.')) {
    path = path.slice(5)
  }
  const tokens = tokenizeLot1Path(path)
  if (tokens.length === 0) return undefined
  const v = walk(root, tokens)
  return typeof v === 'string' ? v : undefined
}

/**
 * Écrit une chaîne au chemin Lot 1 (même grammaire que `getStringAtLot1Path`).
 * `root` doit être l’objet racine (JSON vault ou `data` section CMS).
 */
export function setStringAtLot1Path(
  root: Record<string, unknown>,
  domain: IntegrityDomain,
  fieldPath: string,
  value: string,
): boolean {
  let path = fieldPath
  if (domain === 'cms_section' && path.startsWith('data.')) {
    path = path.slice(5)
  }
  const tokens = tokenizeLot1Path(path)
  if (tokens.length === 0) return false
  const last = tokens[tokens.length - 1]!
  const parentTokens = tokens.slice(0, -1)
  let cur: unknown = root
  for (const t of parentTokens) {
    if (cur == null || typeof cur !== 'object') return false
    if (typeof t === 'number') {
      if (!Array.isArray(cur)) return false
      cur = cur[t]
    } else {
      cur = (cur as Record<string, unknown>)[t]
    }
  }
  if (cur == null || typeof cur !== 'object') return false
  if (typeof last === 'string') {
    ;(cur as Record<string, unknown>)[last] = value
    return true
  }
  if (typeof last === 'number' && Array.isArray(cur)) {
    ;(cur as unknown[])[last] = value
    return true
  }
  return false
}

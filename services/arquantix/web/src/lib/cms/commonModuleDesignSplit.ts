/**
 * Modules communs : séparer champs « design » (partagés toutes langues)
 * et champs texte (FR / EN / IT), aligné sur `sectionI18nPolicy` +
 * `expandTranslatablePaths` (même logique que translateSectionData).
 */

import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { expandTranslatablePaths } from '@/lib/i18n/translatablePathExpansion'
import { resolveCanonicalSectionKey, getSectionType } from '@/lib/sections/library'
import { resolveSectionI18nPolicy } from '@/lib/sections/sectionI18nPolicy'

/** Forme minimale pour fusionner sans importer `commonModulesStorage` (évite cycle). */
export type CommonModuleEntryLike = {
  sectionKey: string
  defaultLocale: Locale
  design?: Record<string, unknown> | null
  locales: Partial<Record<Locale, Record<string, unknown>>>
}

function tokenizePath(path: string): Array<string | number> {
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

function getAtPath(root: unknown, path: string): unknown {
  const tokens = tokenizePath(path)
  let cur: unknown = root
  for (const t of tokens) {
    if (cur == null) return undefined
    if (typeof t === 'number') {
      cur = Array.isArray(cur) ? cur[t] : undefined
    } else {
      cur =
        typeof cur === 'object' && !Array.isArray(cur) && Object.prototype.hasOwnProperty.call(cur, t)
          ? (cur as Record<string, unknown>)[t]
          : undefined
    }
  }
  return cur
}

function setAtPath(root: Record<string, unknown>, path: string, value: unknown): void {
  const tokens = tokenizePath(path)
  if (tokens.length === 0) return
  const last = tokens[tokens.length - 1]!
  let cur: unknown = root
  for (let i = 0; i < tokens.length - 1; i++) {
    const t = tokens[i]!
    if (typeof t === 'number') {
      if (!Array.isArray(cur)) return
      const arr = cur as unknown[]
      if (arr[t] == null || typeof arr[t] !== 'object') {
        arr[t] = typeof tokens[i + 1] === 'number' ? [] : {}
      }
      cur = arr[t]
    } else {
      if (cur == null || typeof cur !== 'object' || Array.isArray(cur)) return
      const rec = cur as Record<string, unknown>
      const nextTok = tokens[i + 1]
      if (!(t in rec) || rec[t] == null) {
        rec[t] = typeof nextTok === 'number' ? [] : {}
      }
      cur = rec[t]
    }
  }
  if (typeof last === 'string') {
    if (cur != null && typeof cur === 'object' && !Array.isArray(cur)) {
      ;(cur as Record<string, unknown>)[last] = value as never
    }
  } else if (typeof last === 'number' && Array.isArray(cur)) {
    ;(cur as unknown[])[last] = value
  }
}

function deleteAtPath(root: unknown, path: string): void {
  const tokens = tokenizePath(path)
  if (tokens.length === 0) return
  const last = tokens[tokens.length - 1]!
  let cur: unknown = root
  for (let i = 0; i < tokens.length - 1; i++) {
    const t = tokens[i]!
    if (cur == null) return
    if (typeof t === 'number') {
      if (!Array.isArray(cur)) return
      cur = (cur as unknown[])[t]
    } else {
      if (typeof cur !== 'object' || Array.isArray(cur)) return
      cur = (cur as Record<string, unknown>)[t]
    }
  }
  if (typeof last === 'string') {
    if (cur != null && typeof cur === 'object' && !Array.isArray(cur)) {
      delete (cur as Record<string, unknown>)[last]
    }
  } else if (typeof last === 'number' && Array.isArray(cur)) {
    const arr = cur as unknown[]
    if (last >= 0 && last < arr.length) {
      arr.splice(last, 1)
    }
  }
}

function concretePathsDepth(p: string): number {
  return tokenizePath(p).length
}

function pruneValue(v: unknown): unknown {
  if (v == null) return v
  if (Array.isArray(v)) {
    const next = v.map(pruneValue).filter((x) => x !== undefined)
    return next.length ? next : undefined
  }
  if (typeof v === 'object') {
    const rec = v as Record<string, unknown>
    const out: Record<string, unknown> = {}
    for (const [k, val] of Object.entries(rec)) {
      const p = pruneValue(val)
      if (p !== undefined) out[k] = p as never
    }
    return Object.keys(out).length ? out : undefined
  }
  return v
}

export function deepMerge(
  a: Record<string, unknown>,
  b: Record<string, unknown>,
): Record<string, unknown> {
  const out = structuredClone(a) as Record<string, unknown>
  for (const [k, v] of Object.entries(b)) {
    if (v === undefined) continue
    if (
      v != null &&
      typeof v === 'object' &&
      !Array.isArray(v) &&
      out[k] != null &&
      typeof out[k] === 'object' &&
      !Array.isArray(out[k])
    ) {
      out[k] = deepMerge(out[k] as Record<string, unknown>, v as Record<string, unknown>)
    } else if (Array.isArray(v) && Array.isArray(out[k])) {
      const left = out[k] as unknown[]
      const right = v as unknown[]
      const max = Math.max(left.length, right.length)
      const merged: unknown[] = []
      for (let i = 0; i < max; i++) {
        const L = left[i]
        const R = right[i]
        if (R === undefined) {
          merged.push(L)
        } else if (L === undefined) {
          merged.push(structuredClone(R))
        } else if (
          L != null &&
          R != null &&
          typeof L === 'object' &&
          typeof R === 'object' &&
          !Array.isArray(L) &&
          !Array.isArray(R)
        ) {
          merged.push(deepMerge(L as Record<string, unknown>, R as Record<string, unknown>))
        } else {
          merged.push(structuredClone(R))
        }
      }
      out[k] = merged as never
    } else {
      out[k] = structuredClone(v) as never
    }
  }
  return out
}

export function deepMergeThree(
  a: Record<string, unknown>,
  b: Record<string, unknown>,
  c: Record<string, unknown>,
): Record<string, unknown> {
  return deepMerge(deepMerge(a, b), c)
}

/** Extrait uniquement les chemins traduisibles (données texte / markdown / etc.). */
export function pickTranslatableFromData(
  data: unknown,
  sectionKey: string,
): Record<string, unknown> {
  const canonical = resolveCanonicalSectionKey(sectionKey) ?? sectionKey
  const policy = resolveSectionI18nPolicy(sectionKey, canonical)
  if (policy.kind !== 'translatable') {
    return {}
  }
  const root = data
  if (root == null || typeof root !== 'object') {
    return {}
  }
  const out: Record<string, unknown> = {}
  for (const abstractPath of policy.paths) {
    const concretePaths = expandTranslatablePaths(root, abstractPath)
    for (const p of concretePaths) {
      const v = getAtPath(root, p)
      if (v !== undefined) {
        setAtPath(out, p, structuredClone(v))
      }
    }
  }
  const pruned = pruneValue(out) as Record<string, unknown> | undefined
  return pruned && typeof pruned === 'object' && !Array.isArray(pruned) ? pruned : {}
}

/** Retire les chemins traduisibles — conserve médias, couleurs, mise en page, etc. */
export function stripTranslatableFromData(
  data: unknown,
  sectionKey: string,
): Record<string, unknown> {
  const canonical = resolveCanonicalSectionKey(sectionKey) ?? sectionKey
  const policy = resolveSectionI18nPolicy(sectionKey, canonical)
  if (policy.kind !== 'translatable') {
    if (data != null && typeof data === 'object' && !Array.isArray(data)) {
      return structuredClone(data) as Record<string, unknown>
    }
    return {}
  }
  if (data == null || typeof data !== 'object') {
    return {}
  }
  const out = structuredClone(data) as Record<string, unknown>
  const allPaths: string[] = []
  for (const abstractPath of policy.paths) {
    allPaths.push(...expandTranslatablePaths(out, abstractPath))
  }
  const sorted = [...new Set(allPaths)].sort((a, b) => concretePathsDepth(b) - concretePathsDepth(a))
  for (const p of sorted) {
    deleteAtPath(out, p)
  }
  const pruned = pruneValue(out) as Record<string, unknown> | undefined
  return pruned && typeof pruned === 'object' && !Array.isArray(pruned) ? pruned : {}
}

/**
 * Calque « design » (hors texte traduit) : fallback dérivé de la locale par défaut du module
 * + surcouche `entry.design`. Évite de perdre p.ex. `backgroundMediaId` quand `design` n’est
 * rempli que partiellement (couleurs / opacités) alors que le média vivait encore côté locale.
 */
export function resolveCommonModuleDesignLayer(
  entry: CommonModuleEntryLike,
  base: Record<string, unknown>,
): Record<string, unknown> {
  const stripFallback = stripTranslatableFromData(
    deepMerge(base, (entry.locales[entry.defaultLocale] ?? {}) as Record<string, unknown>),
    entry.sectionKey,
  )
  const stored =
    entry.design != null && typeof entry.design === 'object'
      ? (entry.design as Record<string, unknown>)
      : {}
  return deepMerge(stripFallback, stored)
}

/**
 * Données effectives pour affichage public / preview (defaults + design partagé + texte locale).
 */
export function mergeCommonModuleResolvedData(
  entry: CommonModuleEntryLike,
  requestedLocale: Locale,
): Record<string, unknown> {
  const type = getSectionType(entry.sectionKey)
  const base = (type?.defaultData ?? {}) as Record<string, unknown>
  const design = resolveCommonModuleDesignLayer(entry, base)

  const order: Locale[] = [
    requestedLocale,
    entry.defaultLocale,
    defaultLocale,
    ...supportedLocales.filter(
      (l) => l !== requestedLocale && l !== entry.defaultLocale && l !== defaultLocale,
    ),
  ]
  const seen = new Set<Locale>()
  let text: Record<string, unknown> = {}
  for (const loc of order) {
    if (seen.has(loc)) continue
    seen.add(loc)
    const block = entry.locales[loc]
    if (block && typeof block === 'object' && !Array.isArray(block) && Object.keys(block).length > 0) {
      text = block as Record<string, unknown>
      break
    }
  }
  return deepMergeThree(base, design, text)
}

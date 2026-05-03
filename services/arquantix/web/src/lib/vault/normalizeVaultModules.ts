/**
 * Normalisation en lecture des modules `vault_builder_v1` (legacy → forme canonique).
 * Ne modifie pas la base : à appeler après lecture du JSON section.
 */
import {
  hasWebExplicitRenderer,
  isAdminRegisteredVaultModuleType,
} from '@/lib/vault/vaultModuleRegistry'

export type NormalizedVaultModule = {
  id: string
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

export type NormalizeVaultModulesResult = {
  modules: NormalizedVaultModule[]
  warnings: string[]
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function stableGeneratedId(index: number, type: string): string {
  return `gen-vault-mod:${index}:${type}`
}

/**
 * Fusionne `documentMediaIds` (legacy) vers `documentEntries` quand les entrées sont absentes.
 * Aligné sur la logique de lecture dans `exclusiveOfferVaultPage.ts` (`parseDocumentEntriesFromVaultContent`).
 */
export function normalizeDocumentsListModuleContent(
  content: Record<string, unknown>,
): Record<string, unknown> {
  const entries = Array.isArray(content.documentEntries) ? content.documentEntries : []
  if (entries.length > 0) {
    return { ...content }
  }
  const rawIds = content.documentMediaIds
  if (!Array.isArray(rawIds) || rawIds.length === 0) {
    return { ...content }
  }
  const documentEntries = rawIds
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((mediaId) => ({ mediaId: mediaId.trim(), documentName: '' }))
  return {
    ...content,
    documentEntries,
  }
}

function resolveModuleType(o: Record<string, unknown>, index: number, warnings: string[]): string {
  const t = typeof o.type === 'string' ? o.type.trim() : ''
  const m = typeof o.module === 'string' ? o.module.trim() : ''
  if (t && m && t !== m) {
    warnings.push(
      `module[${index}]: type/module divergents — conservé type="${t}" (module="${m}")`,
    )
  }
  if (t) return t
  if (m) {
    warnings.push(`module[${index}]: alias legacy "module" → type "${m}"`)
    return m
  }
  warnings.push(`module[${index}]: type manquant — "unknown"`)
  return 'unknown'
}

function normalizeModuleContent(type: string, content: Record<string, unknown>): Record<string, unknown> {
  if (type === 'DocumentsListModule') {
    return normalizeDocumentsListModuleContent(content)
  }
  return { ...content }
}

/**
 * Normalise le tableau `modules` extrait d’un `data` de section vault.
 *
 * @param modulesRaw — valeur de `data.modules` (souvent un tableau)
 * @param context — préfixe optionnel pour les warnings (ex. slug page)
 */
export function normalizeVaultModulesArray(
  modulesRaw: unknown,
  context?: string,
): NormalizeVaultModulesResult {
  const warnings: string[] = []
  const prefix = context ? `${context}: ` : ''

  if (!Array.isArray(modulesRaw)) {
    if (modulesRaw != null) {
      warnings.push(`${prefix}data.modules n’est pas un tableau — traité comme []`)
    }
    return { modules: [], warnings }
  }

  const modules: NormalizedVaultModule[] = []

  modulesRaw.forEach((raw, index) => {
    if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) {
      warnings.push(`${prefix}module[${index}]: entrée ignorée (non-objet)`)
      return
    }
    const o = raw as Record<string, unknown>

    if (o.enabled === false) {
      return
    }

    const type = resolveModuleType(o, index, warnings)

    if (type === 'unknown') {
      warnings.push(`${prefix}module[${index}]: type inconnu (non résolu)`)
    } else if (!isAdminRegisteredVaultModuleType(type)) {
      warnings.push(
        `${prefix}module[${index}]: type "${type}" absent du catalogue admin — rendu/incohérence possibles`,
      )
    } else if (!hasWebExplicitRenderer(type)) {
      warnings.push(
        `${prefix}module[${index}]: type "${type}" catalogue admin mais sans renderer web dédié (fallback placeholder)`,
      )
    }

    const idRaw = typeof o.id === 'string' ? o.id.trim() : ''
    const id = idRaw || stableGeneratedId(index, type)

    const contentIn = asRecord(o.content) ?? {}
    const content = normalizeModuleContent(type, contentIn)

    modules.push({
      id,
      type,
      enabled: true,
      content,
    })
  })

  return { modules, warnings }
}

/**
 * Extrait et normalise `modules` depuis la racine JSON `data` d’un SectionContent vault.
 */
export function normalizeVaultModulesFromSectionData(
  data: unknown,
  context?: string,
): NormalizeVaultModulesResult {
  const root = asRecord(data)
  const modulesRaw = root ? root.modules : undefined
  return normalizeVaultModulesArray(modulesRaw, context)
}

/**
 * Retourne une copie superficielle du `data` vault avec `modules` normalisés (pour BFF mobile, etc.).
 * Les autres clés (`templateKey`, `navbar`, …) sont préservées par référence peu profonde.
 */
export function normalizeVaultBuilderSectionDataRoot(
  data: unknown,
  context?: string,
): { data: Record<string, unknown> | null; warnings: string[] } {
  const root = asRecord(data)
  if (!root) {
    return {
      data: null,
      warnings: [context ? `${context}: data racine invalide` : 'data racine invalide'],
    }
  }
  const { modules, warnings } = normalizeVaultModulesFromSectionData(data, context)
  return {
    data: {
      ...root,
      modules,
    },
    warnings,
  }
}

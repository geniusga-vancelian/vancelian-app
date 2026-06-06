import matter from 'gray-matter'
import { isValidLocale, type Locale } from '@/config/locales'
import { getVaultModuleDefinition, getVaultModuleLabel } from '@/lib/admin/vaultModuleCatalog'

export const VAULT_MODULES_MARKDOWN_FORMAT = 'vancelian-vault-modules'
export const VAULT_MODULES_MARKDOWN_VERSION = 1

export type VaultModuleMarkdownRow = {
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

export type VaultModuleMarkdownWarningCode =
  | 'YAML_INVALID'
  | 'FORMAT_UNKNOWN'
  | 'VERSION_UNSUPPORTED'
  | 'BODY_EMPTY'
  | 'LOCALE_MISMATCH'
  | 'MODULE_TYPE_UNKNOWN'
  | 'MODULE_JSON_INVALID'
  | 'MODULE_SECTION_SKIPPED'
  | 'MODULES_WILL_REPLACE'

export type VaultModuleMarkdownWarning = {
  code: VaultModuleMarkdownWarningCode
  messageFr: string
  moduleIndex?: number
  moduleType?: string
}

export type VaultModulesMarkdownExportInput = {
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

export type VaultModulesMarkdownParseResult = {
  locale: Locale
  modules: VaultModuleMarkdownRow[]
  warnings: VaultModuleMarkdownWarning[]
}

const MODULE_SECTION_RE = /^## Module:\s*([A-Za-z0-9_]+)\s*$/gm
const ENABLED_RE = /^enabled:\s*(true|false)\s*$/im
const JSON_FENCE_RE = /```vault-module-json\s*\n([\s\S]*?)\n```/i

function cloneContent(content: Record<string, unknown>): Record<string, unknown> {
  return structuredClone(content) as Record<string, unknown>
}

/** Sérialise les modules « Modules du vault » (sans identité page, slug, cover). */
export function exportVaultModulesToMarkdown(
  modules: VaultModulesMarkdownExportInput[],
  locale: Locale,
): string {
  const rows = modules.map((m) => ({
    type: m.type,
    enabled: m.enabled !== false,
    content: cloneContent(
      m.content != null && typeof m.content === 'object' && !Array.isArray(m.content)
        ? (m.content as Record<string, unknown>)
        : {},
    ),
  }))

  const sections = rows.map((row) => {
    const json = JSON.stringify(row.content, null, 2)
    return [
      `## Module: ${row.type}`,
      '',
      `enabled: ${row.enabled ? 'true' : 'false'}`,
      '',
      '```vault-module-json',
      json,
      '```',
      '',
    ].join('\n')
  })

  const body = [
    '# Modules du vault',
    '',
    '> Export Vault Builder — section **Modules du vault** uniquement.',
    '> Exclut : titre page, slug, image de couverture, métadonnées produit et moteur.',
    '',
    rows.length === 0 ? '_Aucun module._' : sections.join('\n').trimEnd(),
    '',
  ].join('\n')

  const fm = {
    format: VAULT_MODULES_MARKDOWN_FORMAT,
    version: VAULT_MODULES_MARKDOWN_VERSION,
    locale,
    moduleCount: rows.length,
    exportedAt: new Date().toISOString(),
  }

  return matter.stringify(body, fm)
}

function parseModuleSection(
  sectionBody: string,
  moduleType: string,
  moduleIndex: number,
): { row: VaultModuleMarkdownRow | null; warnings: VaultModuleMarkdownWarning[] } {
  const warnings: VaultModuleMarkdownWarning[] = []

  if (!getVaultModuleDefinition(moduleType)) {
    warnings.push({
      code: 'MODULE_TYPE_UNKNOWN',
      messageFr: `Type de module ignoré (inconnu) : « ${moduleType} ».`,
      moduleIndex,
      moduleType,
    })
    return { row: null, warnings }
  }

  const enabledMatch = sectionBody.match(ENABLED_RE)
  const enabled = enabledMatch ? enabledMatch[1] === 'true' : true

  const jsonMatch = sectionBody.match(JSON_FENCE_RE)
  if (!jsonMatch?.[1]?.trim()) {
    warnings.push({
      code: 'MODULE_JSON_INVALID',
      messageFr: `Bloc JSON manquant ou vide pour le module « ${moduleType} ».`,
      moduleIndex,
      moduleType,
    })
    return { row: null, warnings }
  }

  let content: Record<string, unknown>
  try {
    const parsed = JSON.parse(jsonMatch[1]) as unknown
    if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('content must be object')
    }
    content = parsed as Record<string, unknown>
  } catch {
    warnings.push({
      code: 'MODULE_JSON_INVALID',
      messageFr: `JSON invalide pour le module « ${moduleType} ».`,
      moduleIndex,
      moduleType,
    })
    return { row: null, warnings }
  }

  return {
    row: { type: moduleType, enabled, content },
    warnings,
  }
}

/** Lit un export Markdown et reconstruit la liste ordonnée de modules vault. */
export function parseVaultModulesMarkdown(
  markdown: string,
  editorLocale: Locale,
): VaultModulesMarkdownParseResult {
  const warnings: VaultModuleMarkdownWarning[] = []

  if (!markdown.trim()) {
    return {
      locale: editorLocale,
      modules: [],
      warnings: [{ code: 'BODY_EMPTY', messageFr: 'Fichier markdown vide.' }],
    }
  }

  let fm: Record<string, unknown> = {}
  let body = markdown
  try {
    const parsed = matter(markdown)
    fm = (parsed.data ?? {}) as Record<string, unknown>
    body = parsed.content
  } catch {
    return {
      locale: editorLocale,
      modules: [],
      warnings: [{ code: 'YAML_INVALID', messageFr: 'Frontmatter YAML invalide.' }],
    }
  }

  const format = typeof fm.format === 'string' ? fm.format.trim() : ''
  if (format && format !== VAULT_MODULES_MARKDOWN_FORMAT) {
    warnings.push({
      code: 'FORMAT_UNKNOWN',
      messageFr: `Format non reconnu (« ${format} »). Attendu : ${VAULT_MODULES_MARKDOWN_FORMAT}.`,
    })
  }

  const version = Number(fm.version)
  if (Number.isFinite(version) && version !== VAULT_MODULES_MARKDOWN_VERSION) {
    warnings.push({
      code: 'VERSION_UNSUPPORTED',
      messageFr: `Version ${version} non supportée (attendu ${VAULT_MODULES_MARKDOWN_VERSION}).`,
    })
  }

  const fmLocale = typeof fm.locale === 'string' ? fm.locale.trim() : ''
  const locale: Locale = isValidLocale(fmLocale) ? fmLocale : editorLocale
  if (fmLocale && isValidLocale(fmLocale) && fmLocale !== editorLocale) {
    warnings.push({
      code: 'LOCALE_MISMATCH',
      messageFr: `Locale du fichier (${fmLocale.toUpperCase()}) différente de la langue éditée (${editorLocale.toUpperCase()}).`,
    })
  }

  const matches = [...body.matchAll(MODULE_SECTION_RE)]
  if (matches.length === 0) {
    if (!body.trim() || /_Aucun module\._/i.test(body)) {
      return { locale, modules: [], warnings }
    }
    warnings.push({
      code: 'BODY_EMPTY',
      messageFr: 'Aucune section « ## Module: … » trouvée dans le fichier.',
    })
    return { locale, modules: [], warnings }
  }

  const modules: VaultModuleMarkdownRow[] = []

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i]!
    const moduleType = match[1]!.trim()
    const start = (match.index ?? 0) + match[0].length
    const end = i + 1 < matches.length ? (matches[i + 1]!.index ?? body.length) : body.length
    const sectionBody = body.slice(start, end)

    const { row, warnings: sectionWarnings } = parseModuleSection(sectionBody, moduleType, i)
    warnings.push(...sectionWarnings)
    if (row) modules.push(row)
  }

  if (modules.length === 0 && matches.length > 0) {
    warnings.push({
      code: 'MODULE_SECTION_SKIPPED',
      messageFr: 'Aucun module valide n’a pu être reconstruit.',
    })
  }

  return { locale, modules, warnings }
}

export function vaultModulesToLandingModules(
  rows: VaultModuleMarkdownRow[],
): Array<{ id: string; type: string; enabled: boolean; content: Record<string, unknown> }> {
  return rows.map((row) => ({
    id: crypto.randomUUID(),
    type: row.type,
    enabled: row.enabled,
    content: cloneContent(row.content),
  }))
}

export function summarizeVaultModuleImportPreview(
  modules: VaultModuleMarkdownRow[],
): Array<{ index: number; type: string; label: string; enabled: boolean; preview: string }> {
  return modules.map((m, index) => {
    const label = getVaultModuleLabel(m.type)
    const preview =
      typeof m.content.moduleTitle === 'string'
        ? m.content.moduleTitle
        : typeof m.content.title === 'string'
          ? m.content.title
          : typeof m.content.text === 'string'
            ? m.content.text.slice(0, 80)
            : ''
    return { index, type: m.type, label, enabled: m.enabled, preview }
  })
}

/**
 * Dérive chemins Markdown admin + extraction des fiches wiki depuis les
 * tool calls persistés (`read_wiki_page`, `select_wiki_pages`).
 */
import type { AgentDecision } from '@/components/admin/AssistanceToolCallDetailDrawer'

const NON_FAQ_TOP = ['concepts', 'entities', 'policies'] as const

/** Chemin relatif sous la racine wiki (aligné sur `wiki_repo` / arborescence fichiers). */
export function wikiMarkdownRelativePath(category: string, slug: string): string {
  const c = category.trim().toLowerCase()
  const s = slug.trim().toLowerCase()
  if (NON_FAQ_TOP.includes(c as (typeof NON_FAQ_TOP)[number])) {
    return `${c}/${s}.md`
  }
  return `faq/${c}/${s}.md`
}

export type WikiReadRef = {
  category: string
  slug: string
  title: string
  relativePath: string
}

export type WikiSelectRef = {
  category: string
  slug: string
  title: string
  score?: number
  relativePath: string
}

export type WikiRefsForTurn = {
  /** Fiches effectivement lues (`read_wiki_page` sans erreur). */
  reads: WikiReadRef[]
  /** Candidats retournés par `select_wiki_pages` (pré-classement). */
  selectCandidates: WikiSelectRef[]
}

export type WikiPipelinePreloadRef = {
  category: string
  slug: string
  title: string
  relativePath: string
}

/**
 * Fiches wiki chargées FS lors du pipeline product (Pass 1 → prompt),
 * persistées sous `message_payload.metadata.product_pipeline_wiki_preload`.
 */
export function extractWikiPreloadFromAssistantPayload(
  messagePayload: Record<string, unknown> | null | undefined,
): WikiPipelinePreloadRef[] {
  if (!messagePayload || typeof messagePayload !== 'object') return []
  const meta = messagePayload.metadata
  if (!meta || typeof meta !== 'object') return []
  const raw = (meta as Record<string, unknown>).product_pipeline_wiki_preload
  if (!Array.isArray(raw)) return []
  const out: WikiPipelinePreloadRef[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const o = item as Record<string, unknown>
    const category = typeof o.category === 'string' ? o.category : ''
    const slug = typeof o.slug === 'string' ? o.slug : ''
    const title =
      typeof o.title === 'string' && o.title.trim()
        ? o.title
        : slug.replace(/-/g, ' ')
    const rp = typeof o.relative_path === 'string' ? o.relative_path : ''
    if (!category || !slug || !rp) continue
    out.push({ category, slug, title, relativePath: rp })
  }
  return out
}

function parseReadWiki(result: Record<string, unknown>): WikiReadRef | null {
  if (result.error != null) return null
  const category = typeof result.category === 'string' ? result.category : ''
  const slug = typeof result.slug === 'string' ? result.slug : ''
  if (!category || !slug) return null
  const title =
    typeof result.title === 'string' && result.title.trim()
      ? result.title
      : slug.replace(/-/g, ' ')
  return {
    category,
    slug,
    title,
    relativePath: wikiMarkdownRelativePath(category, slug),
  }
}

function parseSelectWiki(result: Record<string, unknown>): WikiSelectRef[] {
  const raw = result.matches
  if (!Array.isArray(raw)) return []
  const out: WikiSelectRef[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const o = item as Record<string, unknown>
    const category = typeof o.category === 'string' ? o.category : ''
    const slug = typeof o.slug === 'string' ? o.slug : ''
    if (!category || !slug) continue
    const title =
      typeof o.title === 'string' && o.title.trim()
        ? o.title
        : slug.replace(/-/g, ' ')
    out.push({
      category,
      slug,
      title,
      score: typeof o.score === 'number' ? o.score : undefined,
      relativePath: wikiMarkdownRelativePath(category, slug),
    })
  }
  return out
}

/**
 * Agrège les références wiki pour un turn, dans l’ordre des décisions (iteration).
 * Déduplique les lectures par (category, slug).
 */
export function extractWikiRefsFromDecisions(
  turnDecisions: AgentDecision[],
): WikiRefsForTurn {
  const reads: WikiReadRef[] = []
  const readKeys = new Set<string>()
  const selectCandidates: WikiSelectRef[] = []
  const selectKeys = new Set<string>()

  const sorted = [...turnDecisions].sort((a, b) => a.iteration - b.iteration)

  for (const d of sorted) {
    const rs = d.result_summary
    if (!rs || typeof rs !== 'object') continue
    const r = rs as Record<string, unknown>

    if (d.tool_name === 'read_wiki_page') {
      const ref = parseReadWiki(r)
      if (ref) {
        const k = `${ref.category}/${ref.slug}`
        if (!readKeys.has(k)) {
          readKeys.add(k)
          reads.push(ref)
        }
      }
    }

    if (d.tool_name === 'select_wiki_pages') {
      for (const cand of parseSelectWiki(r)) {
        const k = `${cand.category}/${cand.slug}`
        if (selectKeys.has(k)) continue
        selectKeys.add(k)
        selectCandidates.push(cand)
      }
    }
  }

  return { reads, selectCandidates }
}

export function adminWikiEditorUrl(relativePath: string): string {
  const q = new URLSearchParams({ path: relativePath })
  return `/admin/assistance/wiki?${q.toString()}`
}

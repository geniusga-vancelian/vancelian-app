import { ArticleBlockType } from '@prisma/client'

/**
 * Convertit une suite de blocs (issue de `resolveArticleBlocksForPublic` ou
 * `help_article_blocks` legacy) en markdown plat. Utilisé par les routes
 * `/api/help/articles/by-slug` et `/api/help/.../articles/[article]` quand
 * l'`article_i18n.contentMarkdown` n'est pas disponible (cas des articles
 * `Article(HELP)` unifiés qui s'appuient uniquement sur `ArticleBlock`).
 *
 * On ne couvre que les types simples nécessaires au rendu mobile lecture
 * Help (HEADING, PARAGRAPH, QUOTE, BULLET_LIST, DOCUMENT). Les types riches
 * (IMAGE, VIDEO, STEPS_MODULE, etc.) restent dans `blocks[]` pour rendu
 * dédié côté client.
 */
export function markdownFromHelpBlocks(
  blocks: Array<{ type: string | ArticleBlockType; data: unknown }>,
): string {
  const parts: string[] = []
  for (const block of blocks) {
    const data = (block.data as Record<string, unknown> | null | undefined) ?? {}
    const t = String(block.type)
    if (t === 'HEADING') {
      const text = typeof data.text === 'string' ? data.text.trim() : ''
      if (text) parts.push(`## ${text}`)
      continue
    }
    if (t === 'PARAGRAPH' || t === 'QUOTE') {
      const text = typeof data.text === 'string' ? data.text.trim() : ''
      if (text) parts.push(text)
      continue
    }
    if (t === 'BULLET_LIST') {
      const items = Array.isArray(data.items) ? data.items : []
      const list = items
        .map((item) => (typeof item === 'string' ? item.trim() : ''))
        .filter((item) => item.length > 0)
        .map((item) => `- ${item}`)
      if (list.length) parts.push(list.join('\n'))
      continue
    }
    if (t === 'DOCUMENT') {
      const title = typeof data.title === 'string' ? data.title.trim() : 'Document'
      const url = typeof data.url === 'string' ? data.url.trim() : ''
      if (url) parts.push(`[${title}](${url})`)
    }
  }
  return parts.join('\n\n').trim()
}

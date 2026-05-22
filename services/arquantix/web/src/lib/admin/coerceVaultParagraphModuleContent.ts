/**
 * Module vault `PARAGRAPH` : le corps Markdown doit vivre dans **`content.text`**
 * (aligné blocs article Prisma `PARAGRAPH`).
 *
 * Certaines données peuvent avoir **`content.markdown`** par confusion avec
 * `SimpleMarkdownContentModule` — on fusionne au chargement admin et on retire `markdown`.
 */
export function coerceVaultParagraphModuleContent(content: Record<string, unknown>): Record<string, unknown> {
  const tDirect = typeof content.text === 'string' ? content.text : ''
  const tMd = typeof content.markdown === 'string' ? content.markdown : ''
  const text = tDirect.trim().length > 0 ? tDirect : tMd
  const out: Record<string, unknown> = { ...content, text }
  delete out.markdown
  return out
}

export function normalizeVaultModulesParagraphContents<
  M extends { type: string; content: Record<string, unknown> },
>(modules: M[]): M[] {
  return modules.map((m) => {
    if (m.type !== 'PARAGRAPH') return m
    const c = m.content
    if (!c || typeof c !== 'object' || Array.isArray(c)) return m
    return { ...m, content: coerceVaultParagraphModuleContent(c as Record<string, unknown>) }
  })
}

/**
 * Entrée module « visite virtuelle » : URL de page viewer ou extrait `src` d’un iframe.
 * Seuls les schémas http/https sont acceptés.
 */
export function normalizeVirtualVisualizationInput(raw: string): string {
  const t = raw.trim()
  if (!t) return ''
  const iframeMatch = t.match(/<iframe[^>]+src=["']([^"']+)["']/i)
  const candidate = (iframeMatch?.[1] ?? t).trim()
  let toParse = candidate
  if (!/^https?:\/\//i.test(toParse)) {
    if (/^\/\//.test(toParse)) {
      toParse = `https:${toParse}`
    } else if (!toParse.includes('://')) {
      toParse = `https://${toParse}`
    }
  }
  try {
    const u = new URL(toParse)
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return ''
    return u.toString()
  } catch {
    return ''
  }
}

export function isVirtualVisualizationEmbedUrl(url: string): boolean {
  return url.length > 0 && /^https?:\/\//i.test(url)
}

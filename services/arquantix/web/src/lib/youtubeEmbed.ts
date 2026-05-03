/**
 * Extrait l’ID vidéo YouTube depuis une URL (watch, youtu.be, embed, shorts, mobile).
 * Retourne null si ce n’est pas une URL YouTube reconnue.
 */
export function getYouTubeVideoIdFromUrl(url: string): string | null {
  const s = url.trim()
  if (!s) return null

  try {
    const u = new URL(s.startsWith('http') ? s : `https://${s}`)
    const host = u.hostname.replace(/^www\./, '')
    if (host === 'youtu.be') {
      const id = u.pathname.replace(/^\//, '').split('/')[0]
      return id || null
    }
    if (host.includes('youtube.com')) {
      const v = u.searchParams.get('v')
      if (v) return v
      const embed = u.pathname.match(/\/embed\/([^/]+)/)
      if (embed?.[1]) return embed[1]
      const shorts = u.pathname.match(/\/shorts\/([^/]+)/)
      if (shorts?.[1]) return shorts[1]
    }
  } catch {
    // URL() peut échouer — repli regex ci-dessous
  }

  const m = s.match(
    /(?:youtube\.com\/watch\?v=|youtube\.com\/embed\/|youtube\.com\/shorts\/|youtu\.be\/)([^&\n?#/]+)/,
  )
  return m?.[1] ?? null
}

/**
 * Résolution du thumbnail (poster) pour les blocs `VIDEO` d'un article.
 *
 * Stratégie :
 * - YouTube : extraction sync de l'ID puis URL `img.youtube.com/vi/{id}/hqdefault.jpg`
 *   (toujours dispo, 480×360, contrairement à `maxresdefault` non garanti).
 * - Vimeo : appel oEmbed (`https://vimeo.com/api/oembed.json?url=...`) avec
 *   timeout court (2 s). Échec silencieux → retour `null` (le bloc Flutter
 *   tombera sur son placeholder vidéo natif).
 *
 * Idempotent et sans effet de bord ; aucun état persisté (aucune mutation DB,
 * aucun écrit sur le bloc `data`). Le thumbnail est ré-injecté à chaque
 * résolution publique du bloc.
 */

const YT_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'])
const VIMEO_HOSTS = new Set(['vimeo.com', 'www.vimeo.com', 'player.vimeo.com'])

/** Extrait l'ID YouTube depuis une URL. Retourne `null` si non YouTube. */
export function extractYouTubeId(rawUrl: string): string | null {
  let url: URL
  try {
    url = new URL(rawUrl)
  } catch {
    return null
  }
  const host = url.hostname.toLowerCase()
  if (!YT_HOSTS.has(host)) return null

  // youtu.be/{id}
  if (host === 'youtu.be') {
    const id = url.pathname.replace(/^\//, '').split('/')[0]
    return /^[A-Za-z0-9_-]{6,}$/.test(id) ? id : null
  }

  // youtube.com/watch?v={id}
  const v = url.searchParams.get('v')
  if (v && /^[A-Za-z0-9_-]{6,}$/.test(v)) return v

  // youtube.com/embed/{id}, /shorts/{id}, /v/{id}, /live/{id}
  const m = url.pathname.match(/^\/(?:embed|shorts|v|live)\/([A-Za-z0-9_-]{6,})/)
  if (m) return m[1]!

  return null
}

/** Extrait l'ID numérique Vimeo depuis une URL. Retourne `null` si non Vimeo. */
export function extractVimeoId(rawUrl: string): string | null {
  let url: URL
  try {
    url = new URL(rawUrl)
  } catch {
    return null
  }
  const host = url.hostname.toLowerCase()
  if (!VIMEO_HOSTS.has(host)) return null

  // vimeo.com/{id} ou player.vimeo.com/video/{id}
  const m = url.pathname.match(/\/(?:video\/)?(\d{5,})/)
  return m ? m[1]! : null
}

/** Construit l'URL du thumbnail YouTube depuis un ID (qualité `hqdefault`). */
export function youTubeThumbnailUrl(id: string): string {
  return `https://img.youtube.com/vi/${id}/hqdefault.jpg`
}

/** Appelle l'API oEmbed Vimeo (timeout 2 s). Retourne l'URL du thumbnail ou `null`. */
export async function fetchVimeoThumbnailUrl(rawUrl: string): Promise<string | null> {
  const ctrl = new AbortController()
  const timeout = setTimeout(() => ctrl.abort(), 2000)
  try {
    const oembed = `https://vimeo.com/api/oembed.json?url=${encodeURIComponent(rawUrl)}`
    const res = await fetch(oembed, { signal: ctrl.signal })
    if (!res.ok) return null
    const json = (await res.json()) as { thumbnail_url?: unknown }
    return typeof json.thumbnail_url === 'string' && json.thumbnail_url.length > 0
      ? json.thumbnail_url
      : null
  } catch {
    return null
  } finally {
    clearTimeout(timeout)
  }
}

/**
 * Résout l'URL de poster d'une vidéo (YouTube sync, Vimeo oEmbed async).
 * Retourne `null` si l'URL n'est ni YouTube ni Vimeo, ou si l'oEmbed échoue.
 */
export async function resolveVideoThumbnailUrl(rawUrl: string): Promise<string | null> {
  if (typeof rawUrl !== 'string' || rawUrl.trim().length === 0) return null
  const ytId = extractYouTubeId(rawUrl)
  if (ytId) return youTubeThumbnailUrl(ytId)
  const vimeoId = extractVimeoId(rawUrl)
  if (vimeoId) return fetchVimeoThumbnailUrl(rawUrl)
  return null
}

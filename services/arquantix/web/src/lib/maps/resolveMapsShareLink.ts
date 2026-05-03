/**
 * Résolution d’un lien de partage Google Maps (ex. maps.app.goo.gl) vers une URL
 * utilisable en iframe sans clé API : .../maps?q=lat,lng&output=embed
 */

/** Hôtes autorisés pour l’URL initiale (anti-SSRF sur la requête sortante). */
export function isAllowedMapsResolveStartUrl(raw: string): boolean {
  const t = raw.trim()
  if (!t.startsWith('http')) return false
  let u: URL
  try {
    u = new URL(t)
  } catch {
    return false
  }
  const h = u.hostname.toLowerCase()
  if (h === 'maps.app.goo.gl') return true
  if (h === 'goo.gl' || h === 'g.co') return true
  if (h === 'maps.google.com') return true
  if (h === 'www.google.com' || h === 'google.com') {
    return u.pathname.startsWith('/maps')
  }
  return false
}

function isAllowedFinalMapsUrl(u: URL): boolean {
  const h = u.hostname.toLowerCase()
  if (h.endsWith('.google.com') || h === 'google.com') return true
  if (h === 'maps.google.com') return true
  return false
}

function isValidLatLng(lat: number, lng: number): boolean {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    Math.abs(lat) <= 90 &&
    Math.abs(lng) <= 180 &&
    !(lat === 0 && lng === 0)
  )
}

/**
 * Extrait une paire lat,lng depuis une URL Google Maps déjà résolue
 * (inclut le fragment # où Google place souvent @lat,lng).
 */
export function extractLatLngFromGoogleMapsUrl(resolvedUrl: string): { lat: number; lng: number } | null {
  let u: URL
  try {
    u = new URL(resolvedUrl)
  } catch {
    return null
  }

  // Chemin + query + hash (les liens courts mènent parfois à ...#...data=...@lat,lng)
  const pathSearchHash = u.pathname + u.search + u.hash

  // Liens courts → souvent /maps/search/42.78,+140.65 (sans @)
  const searchMatch = pathSearchHash.match(
    /\/maps\/search\/(-?\d+\.?\d*)(?:%2C|,)\+?(-?\d+\.?\d*)/i,
  )
  if (searchMatch) {
    const lat = Number.parseFloat(searchMatch[1])
    const lng = Number.parseFloat(searchMatch[2])
    if (isValidLatLng(lat, lng)) {
      return { lat, lng }
    }
  }

  // /place/.../@lat,lng, zoom ou /...@lat,lng
  const atMatch = pathSearchHash.match(/@(-?\d+\.?\d*),(-?\d+\.?\d+)/)
  if (atMatch) {
    const lat = Number.parseFloat(atMatch[1])
    const lng = Number.parseFloat(atMatch[2])
    if (isValidLatLng(lat, lng)) {
      return { lat, lng }
    }
  }

  const ll = u.searchParams.get('ll')
  if (ll) {
    const parts = ll.split(',').map((s) => s.trim())
    if (parts.length >= 2) {
      const lat = Number.parseFloat(parts[0])
      const lng = Number.parseFloat(parts[1])
      if (isValidLatLng(lat, lng)) return { lat, lng }
    }
  }

  const q = u.searchParams.get('q')
  if (q && /^-?\d+\.?\d*,-?\d+\.?\d*$/.test(q.trim())) {
    const [a, b] = q.split(',').map((s) => Number.parseFloat(s.trim()))
    if (isValidLatLng(a, b)) return { lat: a, lng: b }
  }

  // Encodage type pb dans certains liens : !3dlat!4dlng
  const pbMatch = pathSearchHash.match(/!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/)
  if (pbMatch) {
    const lat = Number.parseFloat(pbMatch[1])
    const lng = Number.parseFloat(pbMatch[2])
    if (isValidLatLng(lat, lng)) {
      return { lat, lng }
    }
  }

  return null
}

const MAX_HTML_FOR_COORDS = 2_800_000

/**
 * Extrait lat/lng depuis le HTML d’une page Maps (liens courts → page sans @ dans l’URL bar).
 */
export function extractLatLngFromMapsHtml(html: string): { lat: number; lng: number } | null {
  const chunk = html.length > MAX_HTML_FOR_COORDS ? html.slice(0, MAX_HTML_FOR_COORDS) : html

  // Blocs pb dans la page : !3d!4d (ordre lat,lng dans l’encodage Maps)
  const pbGlobal = chunk.match(/!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/)
  if (pbGlobal) {
    const lat = Number.parseFloat(pbGlobal[1])
    const lng = Number.parseFloat(pbGlobal[2])
    if (isValidLatLng(lat, lng)) return { lat, lng }
  }

  // Centre / viewport dans du JSON inline
  const reAt = /@(-?\d{1,2}\.\d{5,14}),(-?\d{1,3}\.\d{5,14})/g
  let m: RegExpExecArray | null
  while ((m = reAt.exec(chunk)) !== null) {
    const lat = Number.parseFloat(m[1])
    const lng = Number.parseFloat(m[2])
    if (isValidLatLng(lat, lng)) return { lat, lng }
  }

  return null
}

async function extractLatLngFromMapsPageBody(pageUrl: string): Promise<{ lat: number; lng: number } | null> {
  let u: URL
  try {
    u = new URL(pageUrl)
  } catch {
    return null
  }
  if (!isAllowedFinalMapsUrl(u)) return null

  const res = await fetch(pageUrl, {
    method: 'GET',
    redirect: 'follow',
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    },
  })
  if (!res.ok) return null
  const ct = (res.headers.get('content-type') || '').toLowerCase()
  if (!ct.includes('text/html') && !ct.includes('application/xhtml')) return null

  const finalPageUrl = res.url
  const fromFinalUrl = extractLatLngFromGoogleMapsUrl(finalPageUrl)
  if (fromFinalUrl) return fromFinalUrl

  const text = await res.text()
  return extractLatLngFromMapsHtml(text)
}

export function buildMapsOutputEmbedUrl(lat: number, lng: number, zoom = 14): string {
  const q = `${lat},${lng}`
  return `https://www.google.com/maps?q=${encodeURIComponent(q)}&z=${zoom}&hl=fr&output=embed`
}

/**
 * Suit les redirections HTTP et retourne l’URL finale (GET).
 */
export async function fetchFinalUrl(startUrl: string): Promise<string> {
  const res = await fetch(startUrl.trim(), {
    method: 'GET',
    redirect: 'follow',
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    },
  })
  if (res.status >= 400) {
    throw new Error(`HTTP ${res.status} lors de la résolution du lien`)
  }
  return res.url
}

/** URL utilisable en src d’iframe : /maps/embed ou /maps?...&output=embed */
export function isGoogleMapsIframeEmbedUrl(raw: string): boolean {
  const t = raw.trim()
  if (!t.startsWith('http')) return false
  try {
    const u = new URL(t.startsWith('http') ? t : `https://${t}`)
    const host = u.hostname.toLowerCase()
    const googleHost =
      host === 'google.com' ||
      host === 'www.google.com' ||
      host === 'maps.google.com' ||
      host.endsWith('.google.com')
    if (!googleHost) return false
    if (u.pathname.includes('/maps/embed')) return true
    if (
      u.searchParams.get('output') === 'embed' &&
      (u.pathname === '/maps' || u.pathname.startsWith('/maps/'))
    ) {
      return true
    }
    return false
  } catch {
    return false
  }
}

export type ResolveMapsShareLinkResult =
  | { ok: true; embedUrl: string; resolvedUrl: string }
  | { ok: false; error: string }

/**
 * À partir d’un lien courts ou d’une URL maps.google.com, produit une URL iframe output=embed.
 */
export async function resolveMapsShareLinkToEmbed(startUrl: string): Promise<ResolveMapsShareLinkResult> {
  if (!isAllowedMapsResolveStartUrl(startUrl)) {
    return { ok: false, error: 'URL non autorisée (utilisez un lien maps.app.goo.gl ou une URL Google Maps).' }
  }

  let finalUrl: string
  try {
    finalUrl = await fetchFinalUrl(startUrl)
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Échec de la résolution'
    return { ok: false, error: msg }
  }

  let u: URL
  try {
    u = new URL(finalUrl)
  } catch {
    return { ok: false, error: 'URL finale invalide' }
  }

  const hostLower = u.hostname.toLowerCase()
  if (hostLower.includes('consent.google')) {
    return {
      ok: false,
      error:
        'Google affiche une page de consentement : ouvrez le lien dans un navigateur, puis utilisez Partager → Intégrer une carte.',
    }
  }

  if (!isAllowedFinalMapsUrl(u)) {
    return { ok: false, error: 'La redirection ne pointe pas vers Google Maps.' }
  }

  let coords = extractLatLngFromGoogleMapsUrl(finalUrl)
  if (!coords) {
    try {
      coords = await extractLatLngFromMapsPageBody(finalUrl)
    } catch {
      coords = null
    }
  }

  if (!coords) {
    return {
      ok: false,
      error:
        'Impossible d’extraire les coordonnées depuis cette page Maps. Utilisez Partager → Intégrer une carte et collez le src de l’iframe.',
    }
  }

  const embedUrl = buildMapsOutputEmbedUrl(coords.lat, coords.lng)
  return { ok: true, embedUrl, resolvedUrl: finalUrl }
}

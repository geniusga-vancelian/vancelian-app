/**
 * Résolution d’un lien de partage Google Maps (ex. maps.app.goo.gl) vers une URL
 * utilisable en iframe sans clé API : .../maps?q=lat,lng&output=embed
 */

/** Décode les entités HTML fréquentes dans une URL collée depuis le code d’intégration Google. */
export function decodeMinimalHtmlEntitiesInUrl(input: string): string {
  let s = input
  s = s.replace(/&#(\d+);/g, (match, n: string) => {
    const c = Number.parseInt(n, 10)
    return Number.isFinite(c) && c >= 0 && c <= 0x10ffff ? String.fromCodePoint(c) : match
  })
  s = s.replace(/&#x([\da-f]+);/gi, (match, h: string) => {
    const c = Number.parseInt(h, 16)
    return Number.isFinite(c) && c >= 0 && c <= 0x10ffff ? String.fromCodePoint(c) : match
  })
  s = s.replace(/&quot;/gi, '"')
  s = s.replace(/&apos;/gi, "'")
  s = s.replace(/&#39;/g, "'")
  s = s.replace(/&lt;/gi, '<')
  s = s.replace(/&gt;/gi, '>')
  s = s.replace(/&amp;/gi, '&')
  return s
}

/**
 * Extrait l’attribut src d’un fragment HTML `<iframe …>`, ou null.
 */
export function extractGoogleMapsIframeSrcFromHtml(html: string): string | null {
  const quoted = html.match(/<iframe\b[^>]*\bsrc\s*=\s*(["'])([\s\S]*?)\1/i)
  if (quoted?.[2]) {
    const v = quoted[2].trim()
    if (v.length > 0) return v
  }
  const bare = html.match(/<iframe\b[^>]*\bsrc\s*=\s*([^\s>]+)/i)
  if (bare?.[1]) {
    const v = bare[1].replace(/["']/g, '').trim()
    if (v.length > 0) return v
  }
  return null
}

/**
 * Normalise la saisie marketing : iframe complète → URL du src ; décodage &#39; &amp; etc.
 * À utiliser à l’enregistrement (admin) et au rendu (rétrocompat contenu déjà stocké).
 */
export function normalizeGoogleMapsEmbedInput(raw: string): string {
  let s = raw.trim()
  if (!s) return ''
  if (/<iframe\b/i.test(s)) {
    const src = extractGoogleMapsIframeSrcFromHtml(s)
    if (src) s = src
  }
  return decodeMinimalHtmlEntitiesInUrl(s).trim()
}

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
  const pbLatLngMatch = pathSearchHash.match(/!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/)
  if (pbLatLngMatch) {
    const lat = Number.parseFloat(pbLatLngMatch[1])
    const lng = Number.parseFloat(pbLatLngMatch[2])
    if (isValidLatLng(lat, lng)) {
      return { lat, lng }
    }
  }

  /** Iframe Maps `pb=` : très souvent **`!2d{lng}!3d{lat}`** (voir module Flutter LocalisationCard). */
  const pbLngLatMatch = pathSearchHash.match(/!2d(-?\d+\.?\d*)!3d(-?\d+\.?\d*)/)
  if (pbLngLatMatch) {
    const lng = Number.parseFloat(pbLngLatMatch[1])
    const lat = Number.parseFloat(pbLngLatMatch[2])
    if (isValidLatLng(lat, lng)) {
      return { lat, lng }
    }
  }

  return null
}

/**
 * Dézoom / zoom depuis un lien Maps (`...@lat,lng,17z` dans l’URL ou le hash).
 */
function extractZoomZFromMapsPathSearchHash(pathSearchHash: string): number | null {
  const mz = pathSearchHash.match(/@(?:-?\d+\.?\d*),(?:-?\d+\.?\d*),(\d{1,2}(?:\.\d+)?)z\b/)
  if (mz) {
    const z = Number.parseFloat(mz[1])
    if (Number.isFinite(z) && z >= 1 && z <= 22) return Math.round(z)
  }
  return null
}

/**
 * Si l’embed Google autorise une requête **`q=lat,lng&output=embed`**, le pin rouge « classique »
 * est garanti là où les iframe `pb=` peuvent n’afficher qu’une zone sans marqueur explicite.
 */
export function preferGoogleMapsPinnedEmbedIframeSrc(embedNormalized: string): string {
  const t = embedNormalized.trim()
  if (!t || !isGoogleMapsIframeEmbedUrl(t)) return t

  let coords = extractLatLngFromGoogleMapsUrl(t)
  if (!coords) {
    let u: URL
    try {
      u = new URL(t.startsWith('http') ? t : `https://${t}`)
    } catch {
      return t
    }
    const pb = u.searchParams.get('pb')
    if (pb) {
      try {
        const decoded = decodeURIComponent(pb)
        const m2 = decoded.match(/!2d(-?\d+\.?\d*)!3d(-?\d+\.?\d*)/)
        if (m2) {
          const lng = Number.parseFloat(m2[1])
          const lat = Number.parseFloat(m2[2])
          if (isValidLatLng(lat, lng)) coords = { lat, lng }
        }
        if (!coords) {
          const m3 = decoded.match(/!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/)
          if (m3) {
            const lat = Number.parseFloat(m3[1])
            const lng = Number.parseFloat(m3[2])
            if (isValidLatLng(lat, lng)) coords = { lat, lng }
          }
        }
      } catch {
        /* ignore */
      }
    }
  }

  if (!coords) return t

  const pathSearchHash = (() => {
    try {
      const u = new URL(t.startsWith('http') ? t : `https://${t}`)
      return u.pathname + u.search + u.hash
    } catch {
      return t
    }
  })()
  const zFromEmbed = extractZoomZFromMapsPathSearchHash(pathSearchHash)
  const zoom = zFromEmbed ?? 14
  const pinned = buildMapsOutputEmbedUrl(coords.lat, coords.lng, zoom)
  /** Évite boucle ou régression si l’iframe est déjà identique au format pin */
  try {
    const cur = new URL(t.startsWith('http') ? t : `https://${t}`)
    const next = new URL(pinned)
    if (cur.searchParams.get('q') === next.searchParams.get('q') && cur.searchParams.get('output') === 'embed') {
      return t
    }
  } catch {
    /* fall through */
  }
  return pinned
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
  const t = normalizeGoogleMapsEmbedInput(raw)
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
  const normalized = normalizeGoogleMapsEmbedInput(startUrl)
  if (isGoogleMapsIframeEmbedUrl(normalized)) {
    return { ok: true, embedUrl: normalized, resolvedUrl: normalized }
  }

  if (!isAllowedMapsResolveStartUrl(normalized)) {
    return { ok: false, error: 'URL non autorisée (utilisez un lien maps.app.goo.gl ou une URL Google Maps).' }
  }

  let finalUrl: string
  try {
    finalUrl = await fetchFinalUrl(normalized)
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

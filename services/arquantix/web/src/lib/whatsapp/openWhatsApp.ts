const WHATSAPP_HOST_RE = /(wa\.me|api\.whatsapp\.com|whatsapp\.com)/i

function normalizePhone(raw: string): string {
  return raw.replace(/[^\d]/g, '')
}

type WhatsAppDeepLink = {
  appUrl: string
  fallbackUrl: string
}

function buildWhatsAppDeepLink(href: string): WhatsAppDeepLink | null {
  const h = (href || '').trim()
  if (!h) return null

  if (/^whatsapp:\/\//i.test(h)) {
    return { appUrl: h, fallbackUrl: 'https://wa.me/' }
  }

  let url: URL
  try {
    url = new URL(h)
  } catch {
    return null
  }
  if (!WHATSAPP_HOST_RE.test(url.hostname)) return null

  let phone = ''
  let text = ''

  if (/wa\.me$/i.test(url.hostname)) {
    phone = normalizePhone(url.pathname)
    text = url.searchParams.get('text') || ''
  } else {
    phone = normalizePhone(url.searchParams.get('phone') || '')
    text = url.searchParams.get('text') || ''
  }

  const appParams = new URLSearchParams()
  if (phone) appParams.set('phone', phone)
  if (text) appParams.set('text', text)
  const appUrl = `whatsapp://send?${appParams.toString()}`

  const webParams = new URLSearchParams()
  if (text) webParams.set('text', text)
  const fallbackUrl = phone
    ? `https://wa.me/${phone}${webParams.toString() ? `?${webParams.toString()}` : ''}`
    : `https://api.whatsapp.com/send${appParams.toString() ? `?${appParams.toString()}` : ''}`

  return { appUrl, fallbackUrl }
}

/**
 * Ouvre l'app WhatsApp si possible (mobile/desktop), sinon fallback web.
 * Retourne `true` si le href est reconnu WhatsApp.
 */
export function openWhatsAppPreferApp(href: string): boolean {
  const deep = buildWhatsAppDeepLink(href)
  if (!deep) return false

  let fallbackTimer: number | null = null
  const cleanup = () => {
    if (fallbackTimer != null) {
      window.clearTimeout(fallbackTimer)
      fallbackTimer = null
    }
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }
  const onVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      cleanup()
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange)
  fallbackTimer = window.setTimeout(() => {
    if (document.visibilityState === 'visible') {
      window.location.assign(deep.fallbackUrl)
    }
  }, 900)

  try {
    window.location.assign(deep.appUrl)
  } catch {
    cleanup()
    window.location.assign(deep.fallbackUrl)
  }
  return true
}

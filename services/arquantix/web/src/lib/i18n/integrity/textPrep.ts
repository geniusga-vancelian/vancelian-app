/**
 * Prépare le texte pour la détection : retire URLs et allège le markdown sans être agressif.
 */

const URL_RE = /\bhttps?:\/\/[^\s)]+/gi
const MD_IMAGE_RE = /!\[[^\]]*]\([^)]+\)/g
const MD_LINK_RE = /\[([^\]]+)]\([^)]+\)/g

/**
 * Remplace les liens markdown par le libellé seul ; supprime les images ; retire les URLs brutes.
 */
export function prepareTextForLanguageDetection(raw: string): string {
  let s = raw.replace(MD_IMAGE_RE, ' ')
  s = s.replace(MD_LINK_RE, '$1')
  s = s.replace(URL_RE, ' ')
  s = s.replace(/\s+/g, ' ').trim()
  return s
}

export function excerpt(text: string, max = 180): string {
  const t = text.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

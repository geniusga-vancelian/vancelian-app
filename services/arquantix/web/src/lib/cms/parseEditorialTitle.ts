import * as React from 'react'

/**
 * Couleur dark officielle du DS Vancelian (footer, final-cta, mid-cta, nav dark).
 * Jamais `#000000` — anthracite chaud `#141208` (`--v-dark-bg`).
 */
export const VANCELIAN_DARK_BG = '#141208'

/** Remplace `#000000` / `#000` par la couleur dark DS. Laisse les autres valeurs intactes. */
export function normalizeVancelianDarkColor(value: string | undefined | null): string {
  const v = (value ?? '').trim().toLowerCase()
  if (!v || v === '#000000' || v === '#000' || v === '000000' || v === 'black') {
    return VANCELIAN_DARK_BG
  }
  return value!.trim()
}

/**
 * Parse un titre CMS en JSX éditorial Vancelian.
 *
 * Balises supportées (seules balises autorisées — pas de HTML arbitraire) :
 * - `<em>mot-clé</em>` → Newsreader italic (via `VEditorialTitle [&_em]`)
 * - `<br>` / `<br/>` / `<br />` → saut de ligne
 *
 * Exemple mid-cta DS :
 * `Prêt à acheter <em>votre premier Bitcoin ?</em>`
 */
export function parseEditorialTitle(raw: string | undefined | null): React.ReactNode {
  const text = (raw ?? '').trim()
  if (!text) return null
  if (!/<em>|<br/i.test(text)) return text

  const nodes: React.ReactNode[] = []
  const re = /<em>([\s\S]*?)<\/em>|<br\s*\/?>/gi
  let last = 0
  let key = 0
  let m: RegExpExecArray | null

  while ((m = re.exec(text)) !== null) {
    const before = text.slice(last, m.index)
    if (before) nodes.push(React.createElement(React.Fragment, { key: key++ }, before))

    if (m[0].toLowerCase().startsWith('<br')) {
      nodes.push(React.createElement('br', { key: key++ }))
    } else if (m[1] !== undefined) {
      nodes.push(React.createElement('em', { key: key++ }, m[1]))
    }

    last = re.lastIndex
  }

  const rest = text.slice(last)
  if (rest) nodes.push(React.createElement(React.Fragment, { key: key++ }, rest))

  return nodes.length > 0 ? nodes : text
}

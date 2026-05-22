/**
 * Taxonomie des keys UI strings (`cms_ui_strings.key`).
 *
 * Convention hiérarchique inspirée des best-practices fintech (Revolut /
 * Lokalise / Locize) : `<namespace>.<section>.<element>`.
 *
 * Exemples valides :
 *   - `common.invest`                          → atome universel
 *   - `common.balance`
 *   - `module.my_account.title`                → UI native d'un widget DS
 *   - `module.exclusive_offers.cta.viewAll`
 *   - `screen.dashboard.heroSubtitle`          → texte spécifique à un écran
 *   - `error.payment.insufficientFunds`        → message d'erreur
 *
 * Anti-patterns (refusés) :
 *   - `msg001`               → identifiant opaque
 *   - `Save`                 → key sans namespace
 *   - `module.X.Y.Z.W.A.B`   → > 4 niveaux après le namespace
 */

/// Namespaces canoniques. Le premier segment de la key DOIT appartenir à
/// cette liste (sinon `inferNamespace` renverra `'misc'` à titre de garde-fou).
export const UI_STRING_NAMESPACES = [
  'common',
  'module',
  'screen',
  'error',
  'misc',
] as const

export type UiStringNamespace = (typeof UI_STRING_NAMESPACES)[number]

/// Profondeur max d'une key (segments séparés par `.`), namespace inclus.
/// Au-delà : ergonomie nuisible pour les traducteurs (cf. anti-patterns
/// IntlPull/Locize), on refuse à l'`isValidUiKey`.
const MAX_KEY_SEGMENTS = 5

const KEY_RE = /^[a-z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$/

/**
 * Valide une key UI string.
 *
 * Règles :
 *   - Au moins 2 segments séparés par `.`.
 *   - Premier segment commence par une lettre minuscule.
 *   - Chaque segment : `[a-zA-Z][a-zA-Z0-9_]*` (camelCase ou snake_case OK,
 *     pas de tiret/espace).
 *   - Profondeur ≤ {@link MAX_KEY_SEGMENTS}.
 *   - Le 1er segment DOIT être un namespace connu sauf si `allowMisc=true`.
 */
export function isValidUiKey(
  key: string,
  opts: { allowMisc?: boolean } = {},
): boolean {
  const k = key.trim()
  if (!k) return false
  if (!KEY_RE.test(k)) return false
  const segs = k.split('.')
  if (segs.length > MAX_KEY_SEGMENTS) return false
  const ns = segs[0] as UiStringNamespace
  if (!UI_STRING_NAMESPACES.includes(ns)) {
    if (!opts.allowMisc) return false
  }
  return true
}

/**
 * Renvoie le namespace canonique pour une key. Si le 1er segment n'est pas
 * un namespace connu, renvoie `'misc'` (jamais d'erreur — l'admin pourra
 * réassigner via PATCH).
 */
export function inferNamespace(key: string): UiStringNamespace {
  const head = key.split('.', 1)[0] as UiStringNamespace | undefined
  if (head && (UI_STRING_NAMESPACES as readonly string[]).includes(head)) {
    return head
  }
  return 'misc'
}

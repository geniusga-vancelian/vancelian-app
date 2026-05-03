/**
 * Expansion des chemins « abstraits » de `SECTION_I18N_POLICIES` en chemins
 * concrets indexés selon la donnée réelle.
 *
 * Source de vérité **unique** pour les deux pipelines i18n des pages :
 *   - `pageCheckLanguage` (scan + apply « Vérifier la langue »)
 *   - `translateSectionData` (auto-traduction côté CMS)
 *
 * Avant ce helper, les deux pipelines avaient leur propre logique d'expansion,
 * divergente :
 *   - `pageCheckLanguage.expandPathForData` : récursive mais limitée (le
 *     préfixe avant `[]` devait être une clé top-level de `data`).
 *   - `translateSectionData` : un seul niveau d'array, et **silencieusement
 *     vide** pour les arrays de strings (`tags[]`) car `getValueAtPath`
 *     vérifiait `typeof item === 'object'`.
 *
 * Ce helper unifie les deux cas en gérant proprement :
 *   - `path.simple`                      → `["path.simple"]`
 *   - `tags[]` (array de **strings**)    → `["tags[0]", "tags[1]", …]`
 *   - `items[].title` (array d'objets)   → `["items[0].title", …]`
 *   - `items[].cards[].title` (multi)    → `["items[0].cards[0].title", …]`
 *   - tableau absent / vide              → `[]`
 *
 * Les chemins retournés sont **sans** préfixe `data.` — l'appelant ajoute le
 * préfixe lui-même (cohérent avec `getStringAtLot1Path` côté `cms_section`).
 *
 * Grammaire acceptée :
 *   - segments alphanumeric `[a-zA-Z_][a-zA-Z0-9_]*`
 *   - séparés par `.`
 *   - point d'itération `[]` accolé au segment précédent
 *   - 0…N occurrences de `[]`
 *
 * Garanties :
 *   - aucune mutation de `data`
 *   - tableaux de longueur 0 → 0 chemin (pas d'entrée fantôme)
 *   - clés absentes → 0 chemin (pas de levée d'exception)
 */

function getAtLocalPath(node: unknown, relativePath: string): unknown {
  if (!relativePath) return node
  let cur: unknown = node
  let i = 0
  const s = relativePath
  while (i < s.length) {
    if (s[i] === '.') {
      i++
      continue
    }
    if (/[a-zA-Z_]/.test(s[i]!)) {
      let j = i
      while (j < s.length && /[a-zA-Z0-9_]/.test(s[j]!)) j++
      const key = s.slice(i, j)
      if (cur == null || typeof cur !== 'object' || Array.isArray(cur)) return undefined
      cur = (cur as Record<string, unknown>)[key]
      i = j
      continue
    }
    if (s[i] === '[') {
      const end = s.indexOf(']', i)
      if (end === -1) return undefined
      const n = Number(s.slice(i + 1, end))
      if (Number.isNaN(n)) return undefined
      if (!Array.isArray(cur)) return undefined
      cur = cur[n]
      i = end + 1
      continue
    }
    i++
  }
  return cur
}

function joinSegments(left: string, right: string): string {
  if (!left) return right
  if (!right) return left
  if (right.startsWith('[')) return `${left}${right}`
  return `${left}.${right}`
}

/**
 * Étend un chemin abstrait selon la donnée réelle.
 *
 * @param data       Racine de navigation. Pour une section CMS, c'est le
 *                   `SectionContent.data` directement (pas l'enveloppe).
 * @param abstractPath  Chemin abstrait, ex. `items[].title`, `tags[]`,
 *                   `keyStats[].label`, `cards[].buttons[].label`.
 * @returns Liste des chemins concrets indexés. **Sans** préfixe `data.`.
 *          Tableau vide si la donnée ne contient aucun emplacement compatible.
 */
export function expandTranslatablePaths(
  data: unknown,
  abstractPath: string,
): string[] {
  const out: string[] = []

  function recurse(currentNode: unknown, remainingPath: string, accPath: string): void {
    const arrIdx = remainingPath.indexOf('[]')
    if (arrIdx === -1) {
      // Plus de wildcard : on a un chemin terminal.
      const finalPath = remainingPath ? joinSegments(accPath, remainingPath) : accPath
      if (finalPath) out.push(finalPath)
      return
    }

    const prefix = remainingPath.slice(0, arrIdx).replace(/\.$/, '')
    const suffix = remainingPath.slice(arrIdx + 2).replace(/^\./, '')

    const arr = prefix ? getAtLocalPath(currentNode, prefix) : currentNode
    if (!Array.isArray(arr)) return

    for (let i = 0; i < arr.length; i++) {
      const itemAccPath = joinSegments(accPath, prefix ? `${prefix}[${i}]` : `[${i}]`)
      // On ré-attaque la suite du path en repartant de l'élément du tableau
      // (et plus de la racine `data`), ce qui permet d'enchaîner les `[]`
      // imbriqués comme `cards[].buttons[].label`.
      recurse(arr[i], suffix, itemAccPath)
    }
  }

  recurse(data, abstractPath, '')
  return out
}

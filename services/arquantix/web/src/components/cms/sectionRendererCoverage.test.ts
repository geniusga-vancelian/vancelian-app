/**
 * Garde-fou « ground truth → renderer ».
 *
 * Pour chaque section listée dans `SECTION_EXPECTED_TRANSLATABLE_PATHS`,
 * on construit un objet `data` qui injecte une **sentinelle unique** sur
 * chaque top-level key attendue. On passe ce `data` à `mapDataToComponentProps`
 * (`@/lib/sections/mapDataToComponentProps`, sans charger le registry React).
 * et on vérifie que **toutes les sentinelles** apparaissent dans le résultat
 * sérialisé : c'est la garantie que le mapping renderer lit bien les champs
 * que la gouvernance i18n promet d'éditer / scanner / traduire.
 *
 * Si vous ajoutez un champ texte à `SECTION_EXPECTED_TRANSLATABLE_PATHS`
 * **sans** le brancher dans `SectionRenderer.mapDataToComponentProps`, ce
 * test casse — c'est l'effet recherché (cf. audit Famille 3).
 *
 * Limites volontaires (pas un parser de JSX) :
 *
 *  - on vérifie uniquement le top-level key (ex. `items[].title` → `items`).
 *    Si le top-level passe, on considère que la sous-arborescence est lue
 *    par le composant downstream (testée au niveau policy / scan ailleurs).
 *  - les sections `notTranslatable` (ex. `header`) ne sont pas dans le
 *    ground truth, donc ignorées ici.
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { mapDataToComponentProps } from '@/lib/sections/mapDataToComponentProps'
import { SECTION_EXPECTED_TRANSLATABLE_PATHS } from '@/lib/sections/sectionExpectedTranslatablePaths'

/** Sections dont le mapping a un comportement délibérément spécial — exceptions documentées. */
const RENDERER_EXCEPTIONS: Record<string, { reason: string; skipKeys?: string[] }> = {
  // `footer` (section-level) : `SectionRenderer` retourne `null` en amont du
  // mapping (footer global ailleurs). Le mapping reste défini pour ne pas
  // invalider d'éventuelles données ; on vérifie quand même que `copyright`
  // est lu.
}

/**
 * Extrait la clé racine d'un path abstrait (`items[].title` → `items`,
 * `tags[]` → `tags`, `description` → `description`).
 */
function topLevelKeyOf(abstractPath: string): string {
  const stop = abstractPath.search(/[\.\[]/)
  return stop === -1 ? abstractPath : abstractPath.slice(0, stop)
}

/**
 * Construit une valeur sentinelle adaptée au top-level path :
 *  - `tags[]`               → array contenant 1 string sentinelle
 *  - `items[].title`        → array contenant 1 objet sentinelle générique
 *  - `title` (scalaire)     → string sentinelle
 *
 * On ne cherche pas à respecter la structure exacte (le test vérifie que
 * la racine de la sentinelle remonte dans la sortie, pas plus).
 */
/** Chemins `a.b.c` sans `[]` : construit l’objet imbriqué attendu sous la clé racine. */
function nestPathFromRelative(relativePath: string, sentinel: string): unknown {
  const parts = relativePath.split('.').filter(Boolean)
  let cur: unknown = sentinel
  for (let i = parts.length - 1; i >= 0; i--) {
    cur = { [parts[i]!]: cur }
  }
  return cur
}

function buildSentinelValue(
  abstractPath: string,
  sentinel: string,
): unknown {
  // `tags[]` : tableau de strings
  if (/^[A-Za-z0-9_]+\[\]$/.test(abstractPath)) {
    return [sentinel]
  }
  // `items[].xxx` : tableau d'objets — la sentinelle remonte via JSON.stringify
  // dès lors que `items` est passé tel quel dans le mapping.
  if (abstractPath.includes('[]')) {
    return [{ __sentinel: sentinel }]
  }
  // Scalaire
  return sentinel
}

/**
 * Pour éviter les faux négatifs liés aux fallbacks OR (`data.ctaText || data.primaryButtonText`),
 * on teste **chaque top-level key isolément** : la sentinelle est seule présente
 * dans `data`, donc même un champ utilisé en fallback est détecté comme lu.
 */
describe('SectionRenderer.mapDataToComponentProps — ground truth ⊆ renderer-read', () => {
  for (const [sectionKey, expectedPaths] of Object.entries(
    SECTION_EXPECTED_TRANSLATABLE_PATHS,
  )) {
    const exception = RENDERER_EXCEPTIONS[sectionKey]
    const skipKeys = new Set(exception?.skipKeys ?? [])

    const seenTopKeys = new Set<string>()
    for (const path of expectedPaths) {
      const topKey = topLevelKeyOf(path)
      if (skipKeys.has(topKey)) continue
      if (seenTopKeys.has(topKey)) continue
      seenTopKeys.add(topKey)

      it(`section "${sectionKey}" : top-level "${topKey}" est lu par le mapping`, () => {
        const sentinel = `__SENTINEL_${sectionKey}_${topKey}__`
        const dotted =
          path.startsWith(`${topKey}.`) && !path.includes('[') && !path.includes('[]')
            ? path.slice(topKey.length + 1)
            : null
        const data: Record<string, unknown> = {
          [topKey]:
            dotted !== null ? nestPathFromRelative(dotted, sentinel) : buildSentinelValue(path, sentinel),
        }
        const props = mapDataToComponentProps(sectionKey, data, 'fr')
        const serialized = JSON.stringify(props)
        assert.ok(
          serialized.includes(sentinel),
          `Section "${sectionKey}" : top-level "${topKey}" déclaré au ground truth ` +
            `mais non lu par mapDataToComponentProps.\n` +
            `→ Soit brancher la lecture dans SectionRenderer, soit retirer ce path du ground truth ` +
            `et de la policy (cf. audit Famille 3).`,
        )
      })
    }
  }
})

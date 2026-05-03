/**
 * Garde-fou « editor → renderer ».
 *
 * Pour chaque section listée dans `SECTION_STRUCTURED_EDITOR_FIELDS`, on
 * injecte une sentinelle isolée sur chaque champ déclaré comme **édité**
 * dans l'UI admin (`SectionEditor.tsx`) et on vérifie qu'elle ressort dans
 * la sortie de `mapDataToComponentProps`.
 *
 * Effet souhaité
 * --------------
 *
 *  - Si vous **ajoutez** un input dans `SectionEditor.tsx` mais oubliez de
 *    le brancher dans le mapping, le test casse : c'est l'effet recherché
 *    (audit Famille 3 / F3.5).
 *  - Si vous **retirez** un input du mapping mais oubliez de le retirer du
 *    registre, vous obtiendrez aussi un échec : effet recherché aussi
 *    (l'opérateur verrait alors un champ saisissable sans effet).
 *
 * Différence avec `sectionRendererCoverage.test.ts`
 * -------------------------------------------------
 *
 *  - `sectionRendererCoverage` contrôle le contrat **i18n**
 *    (`SECTION_EXPECTED_TRANSLATABLE_PATHS`) → uniquement les champs texte.
 *  - Ce test contrôle le contrat **éditorial** (champs admin structurés)
 *    → tous les champs édités, traduisibles ou non (booléens, nombres,
 *    médias…). Il complémente l'autre, ne le remplace pas.
 *
 * Sentinelle
 * ----------
 *
 * Comme pour `sectionRendererCoverage`, la sentinelle est :
 *  - une string unique pour les champs scalaires,
 *  - un tableau `[sentinel]` pour les arrays scalaires,
 *  - un tableau `[{ __sentinel }]` pour les arrays d'objets.
 *
 * Le test n'inspecte que la **présence** de la sentinelle dans le JSON
 * sérialisé : le détail de la sous-arborescence est laissé au composant
 * downstream.
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { mapDataToComponentProps } from '@/lib/sections/mapDataToComponentProps'
import { SECTION_STRUCTURED_EDITOR_FIELDS } from './sectionStructuredEditorFields'

/**
 * Champs qui ne peuvent pas être détectés par sentinelle string (booléens,
 * nombres avec coercion stricte, valeurs de domaine restreint…) et qu'on
 * doit donc tester avec une valeur typée d'une autre manière.
 *
 * On documente ici le **type de sentinelle** à utiliser et la **valeur
 * attendue** dans la sortie sérialisée du mapping.
 */
const TYPED_SENTINELS: Record<string, { input: unknown; expected: string }> = {
  // Booléens : on injecte `true` et on vérifie qu'on retrouve `true` dans
  // la sortie sérialisée. Les mappings utilisent souvent `=== true`.
  hideCta: { input: true, expected: '"hideCta":true' },
  showAllExclusiveOffers: {
    input: true,
    expected: '"showAllExclusiveOffers":true',
  },
  hideStepNumbering: { input: true, expected: '"hideStepNumbering":true' },
  // `showPrimaryButton` / `showSecondaryButton` utilisent `!== false` côté
  // mapping → tester avec `false` est plus discriminant.
  showPrimaryButton: { input: false, expected: '"showPrimaryButton":false' },
  showSecondaryButton: { input: false, expected: '"showSecondaryButton":false' },
  mediaRight: { input: true, expected: '"mediaRight":true' },

  // Nombres : on injecte une valeur peu probable d'apparaître autrement.
  backgroundImageOpacity: {
    input: 0.37,
    expected: '"backgroundImageOpacity":0.37',
  },
  overlayOpacity: { input: 0.41, expected: '"overlayOpacity":0.41' },
  limit: { input: 17, expected: '"limit":17' },

  // Domaine restreint (`columns: 3 | 4 | 6`, `cardsPerRow: 1 | 2`) : on
  // choisit une valeur valide différente de la valeur par défaut.
  columns: { input: 6, expected: '"columns":6' },
  cardsPerRow: { input: 2, expected: '"cardsPerRow":2' },

  showTitle: { input: false, expected: '"showTitle":false' },

  pageSize: { input: 13, expected: '"pageSize":13' },

  showEyebrow: { input: false, expected: '"showEyebrow":false' },
  showStandfirst: { input: false, expected: '"showStandfirst":false' },
  showMeta: { input: false, expected: '"showMeta":false' },

  /**
   * Objet `ui` FAQ : sentinelle sur une sous-clé (le test sérialise tout le retour).
   */
  ui: {
    input: { expandAllLabel: '__SENTINEL_FIELD_ui__' },
    expected: '__SENTINEL_FIELD_ui__',
  },

  // `contentTextAlign: 'center' | 'justify'` : valeur valide non par défaut.
  contentTextAlign: {
    input: 'justify',
    expected: '"contentTextAlign":"justify"',
  },
}

/** Valeurs sentinelles par défaut pour les champs string / array. */
function buildDefaultSentinel(field: string): {
  input: unknown
  expected: string
} {
  // Heuristique : `items`, `stats`, `steps`, `tags`, `links`,
  // `selectedPackagedProductIds` sont des arrays (cf. `library.ts` /
  // `SectionEditor`). Si le mapping spread l'array, la sentinelle remonte.
  const arrayLikeKeys = new Set([
    'items',
    'stats',
    'steps',
    'tags',
    'links',
    'selectedPackagedProductIds',
  ])
  const sentinel = `__SENTINEL_FIELD_${field}__`
  if (arrayLikeKeys.has(field)) {
    if (field === 'tags' || field === 'selectedPackagedProductIds') {
      return { input: [sentinel], expected: sentinel }
    }
    return { input: [{ __sentinel: sentinel }], expected: sentinel }
  }
  return { input: sentinel, expected: sentinel }
}

describe('SectionEditor — editor declared fields ⊆ renderer-read fields', () => {
  for (const [sectionKey, def] of Object.entries(
    SECTION_STRUCTURED_EDITOR_FIELDS,
  )) {
    for (const field of def.direct) {
      it(`section "${sectionKey}" : champ admin "${field}" est lu par le mapping`, () => {
        const typed = TYPED_SENTINELS[field]
        const { input, expected } = typed ?? buildDefaultSentinel(field)

        const data: Record<string, unknown> = { [field]: input }
        const props = mapDataToComponentProps(sectionKey, data, 'fr')
        const serialized = JSON.stringify(props)

        assert.ok(
          serialized.includes(expected),
          `Section "${sectionKey}" : l'admin déclare un input pour "${field}" ` +
            `mais ce champ n'est pas lu par mapDataToComponentProps.\n` +
            `→ Soit brancher la lecture dans SectionRenderer, soit retirer ce champ ` +
            `de SECTION_STRUCTURED_EDITOR_FIELDS et de l'UI admin (audit Famille 3).\n` +
            `Sentinelle attendue dans la sortie : ${expected}\n` +
            `Sortie reçue (extrait) : ${serialized.slice(0, 400)}…`,
        )
      })
    }
  }
})

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { SECTION_I18N_POLICIES } from './sectionI18nPolicy'
import { SECTION_EXPECTED_TRANSLATABLE_PATHS } from './sectionExpectedTranslatablePaths'

/**
 * Garde-fou : pour chaque section listée dans le ground truth, la policy
 * doit déclarer **au moins** ces chemins (elle peut en déclarer plus pour
 * des champs encore au schéma mais désactivés côté rendu).
 *
 * Si vous ajoutez un champ texte rendu dans une section :
 *   1. ajoutez-le à `SECTION_EXPECTED_TRANSLATABLE_PATHS` ;
 *   2. ajoutez-le à `SECTION_I18N_POLICIES`.
 *
 * Sans la double mise à jour, ce test casse — c'est l'effet recherché.
 */

describe('SECTION_I18N_POLICIES — couverture vs ground truth', () => {
  for (const [sectionKey, expectedPaths] of Object.entries(
    SECTION_EXPECTED_TRANSLATABLE_PATHS,
  )) {
    it(`couvre tous les paths attendus pour la section "${sectionKey}"`, () => {
      const policy = SECTION_I18N_POLICIES[sectionKey]
      assert.ok(
        policy,
        `Pas de policy pour "${sectionKey}". Ajoutez une entrée dans SECTION_I18N_POLICIES.`,
      )
      assert.equal(
        policy.kind,
        'translatable',
        `La section "${sectionKey}" est attendue traduisible (ground truth) mais sa policy est "${policy.kind}".`,
      )
      if (policy.kind !== 'translatable') return
      const policyPathSet = new Set(policy.paths)
      const missing: string[] = []
      for (const expected of expectedPaths) {
        if (!policyPathSet.has(expected)) {
          missing.push(expected)
        }
      }
      assert.deepEqual(
        missing,
        [],
        `La policy "${sectionKey}" oublie : ${missing.join(', ')}.\n` +
          `Ajoutez ces chemins dans SECTION_I18N_POLICIES (et synchronisez le ground truth).`,
      )
    })
  }

  it('ne dérive pas (chaque clé du ground truth a une policy résolvable, pas notTranslatable)', () => {
    const drift: string[] = []
    for (const sectionKey of Object.keys(SECTION_EXPECTED_TRANSLATABLE_PATHS)) {
      const policy = SECTION_I18N_POLICIES[sectionKey]
      if (!policy || policy.kind !== 'translatable') {
        drift.push(sectionKey)
      }
    }
    assert.deepEqual(
      drift,
      [],
      `Sections du ground truth sans policy translatable : ${drift.join(', ')}`,
    )
  })
})

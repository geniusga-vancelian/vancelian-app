import { test } from 'node:test'
import assert from 'node:assert/strict'
import { SECTION_TYPES, resolveCanonicalSectionKey } from '@/lib/sections/library'
import { resolveSectionI18nPolicy } from '@/lib/sections/sectionI18nPolicy'

test('chaque type catalogue (SECTION_TYPES) a une politique i18n résoluble', () => {
  const keys = SECTION_TYPES.map((t) => t.key)
  assert.ok(keys.length > 0, 'SECTION_TYPES ne doit pas être vide')
  for (const key of keys) {
    const canon = resolveCanonicalSectionKey(key)
    const r = resolveSectionI18nPolicy(key, canon)
    assert.notEqual(
      r.kind,
      'missingPolicy',
      `Ajouter une politique dans sectionI18nPolicy.ts pour la clé "${key}" (canon: ${String(canon)})`,
    )
  }
})

test('resolveSectionI18nPolicy : suffixe numérique → canon', () => {
  const canon = resolveCanonicalSectionKey('cta_2')
  const r = resolveSectionI18nPolicy('cta_2', canon)
  assert.equal(r.kind, 'translatable')
  if (r.kind === 'translatable') {
    assert.ok(r.paths.includes('title'))
  }
})

test('resolveSectionI18nPolicy : header explicite non traduit', () => {
  const r = resolveSectionI18nPolicy('header', resolveCanonicalSectionKey('header'))
  assert.equal(r.kind, 'notTranslatable')
})

test('resolveSectionI18nPolicy : clé inconnue', () => {
  const r = resolveSectionI18nPolicy('totally_unknown_section_xyz', null)
  assert.equal(r.kind, 'missingPolicy')
})

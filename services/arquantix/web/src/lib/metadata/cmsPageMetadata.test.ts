import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildPublicCmsPageMetadata, metadataFromCmsPageFields } from './cmsPageMetadata'

test('metadataFromCmsPageFields : utilise title et description CMS', () => {
  const m = metadataFromCmsPageFields({
    title: '  Accueil  ',
    description: '  Sous-titre  ',
  })
  assert.equal(m.title, 'Accueil')
  assert.equal(m.description, 'Sous-titre')
})

test('metadataFromCmsPageFields : fallback si vides', () => {
  const m = metadataFromCmsPageFields({ title: null, description: '   ' })
  assert.equal(m.title, 'Arquantix')
  assert.equal(m.description, 'Fractional Real Estate, Institutional Rigor.')
})

test('buildPublicCmsPageMetadata : canonical stable sans query', () => {
  const m = buildPublicCmsPageMetadata({
    title: 'T',
    description: 'D',
    canonicalPath: '/offre',
    locale: 'fr',
  })
  assert.equal(m.alternates?.canonical, '/offre')
  assert.equal(m.openGraph?.title, 'T')
  assert.equal(m.openGraph?.locale, 'fr_FR')
  assert.ok(m.twitter && typeof m.twitter === 'object' && 'card' in m.twitter)
  assert.ok(m.robots && typeof m.robots === 'object' && 'index' in m.robots)
})

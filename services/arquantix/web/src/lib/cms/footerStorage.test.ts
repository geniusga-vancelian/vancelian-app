import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  buildFooterJsonV2AfterLocaleEdit,
  getAdminFooterLoadPayload,
  parseFooterStorage,
  resolveFooterPayloadForLocale,
} from './footerStorage'

test('parseFooterStorage : legacy plat', () => {
  const raw = { copyright: 'L', description: 'D' }
  const p = parseFooterStorage(raw)
  assert.equal(p.kind, 'legacy')
  if (p.kind === 'legacy') {
    assert.equal(p.data.copyright, 'L')
    assert.equal(p.data.description, 'D')
  }
})

test('parseFooterStorage : v2', () => {
  const raw = {
    version: 2,
    defaultLocale: 'fr' as const,
    locales: {
      fr: { copyright: 'FR' },
      en: { copyright: 'EN' },
    },
  }
  const p = parseFooterStorage(raw)
  assert.equal(p.kind, 'v2')
  if (p.kind === 'v2') {
    assert.equal(p.doc.locales.fr?.copyright, 'FR')
    assert.equal(p.doc.locales.en?.copyright, 'EN')
  }
})

test('parseFooterStorage : version 2 invalide → invalid', () => {
  const p = parseFooterStorage({ version: 2, defaultLocale: 'xx' })
  assert.equal(p.kind, 'invalid')
})

test('resolveFooterPayloadForLocale : legacy identique pour toutes les locales', () => {
  const parsed = parseFooterStorage({ copyright: 'X' })
  assert.equal(parsed.kind, 'legacy')
  const a = resolveFooterPayloadForLocale(parsed, 'fr')
  const b = resolveFooterPayloadForLocale(parsed, 'en')
  assert.deepEqual(a, b)
  assert.equal(a.copyright, 'X')
})

test('resolveFooterPayloadForLocale : v2 locale demandée', () => {
  const parsed = parseFooterStorage({
    version: 2,
    defaultLocale: 'fr',
    locales: { fr: { copyright: 'FR' }, en: { copyright: 'EN' } },
  })
  assert.equal(parsed.kind, 'v2')
  const en = resolveFooterPayloadForLocale(parsed, 'en')
  assert.equal(en.copyright, 'EN')
})

test('resolveFooterPayloadForLocale : v2 locale absente → defaultLocale du doc', () => {
  const parsed = parseFooterStorage({
    version: 2,
    defaultLocale: 'fr',
    locales: { fr: { copyright: 'FR' }, en: { copyright: 'EN' } },
  })
  assert.equal(parsed.kind, 'v2')
  const it = resolveFooterPayloadForLocale(parsed, 'it')
  assert.equal(it.copyright, 'FR')
})

test('resolveFooterPayloadForLocale : v2 tout vide → {}', () => {
  const parsed = parseFooterStorage({
    version: 2,
    defaultLocale: 'fr',
    locales: { fr: {}, en: {}, it: {} },
  })
  assert.equal(parsed.kind, 'v2')
  const out = resolveFooterPayloadForLocale(parsed, 'en')
  assert.deepEqual(out, {})
})

test('resolveFooterPayloadForLocale : invalid → {}', () => {
  const parsed = parseFooterStorage(null)
  assert.equal(parsed.kind, 'invalid')
  assert.deepEqual(resolveFooterPayloadForLocale(parsed, 'fr'), {})
})

test('getAdminFooterLoadPayload : legacy → tout dans fr', () => {
  const p = getAdminFooterLoadPayload({ copyright: 'L' })
  assert.equal(p.isLegacyStorage, true)
  assert.equal(p.defaultLocale, 'fr')
  assert.equal(p.locales.fr.copyright, 'L')
  assert.deepEqual(p.locales.en, {})
})

test('getAdminFooterLoadPayload : v2 → trois blocs', () => {
  const p = getAdminFooterLoadPayload({
    version: 2,
    defaultLocale: 'en',
    locales: { fr: { copyright: 'F' }, en: { copyright: 'E' } },
  })
  assert.equal(p.isLegacyStorage, false)
  assert.equal(p.defaultLocale, 'en')
  assert.equal(p.locales.fr.copyright, 'F')
  assert.equal(p.locales.en.copyright, 'E')
})

test('buildFooterJsonV2AfterLocaleEdit : depuis legacy, n’écrase que la langue cible', () => {
  const raw = { copyright: 'Legacy' }
  const out = buildFooterJsonV2AfterLocaleEdit({
    existingRaw: raw,
    locale: 'en',
    defaultLocale: 'fr',
    block: { copyright: 'EN only' },
  })
  assert.equal(out.version, 2)
  assert.equal(out.defaultLocale, 'fr')
  assert.equal(out.locales.fr?.copyright, 'Legacy')
  assert.equal(out.locales.en?.copyright, 'EN only')
})

test('buildFooterJsonV2AfterLocaleEdit : depuis v2, préserve l’autre langue', () => {
  const raw = {
    version: 2,
    defaultLocale: 'fr',
    locales: { fr: { copyright: 'FR' }, en: { copyright: 'EN' }, it: {} },
  }
  const out = buildFooterJsonV2AfterLocaleEdit({
    existingRaw: raw,
    locale: 'fr',
    defaultLocale: 'fr',
    block: { copyright: 'FR2' },
  })
  assert.equal(out.locales.fr?.copyright, 'FR2')
  assert.equal(out.locales.en?.copyright, 'EN')
})

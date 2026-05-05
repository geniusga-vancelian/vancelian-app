import { test } from 'node:test'
import assert from 'node:assert/strict'
import { resolvePublicLocale } from './resolvePublicLocale'
import { ARQUANTIX_LOCALE_COOKIE } from './locale-server'

function mockStore(map: Record<string, string | undefined>) {
  return {
    get: (name: string) => {
      const v = map[name]
      return v !== undefined ? { value: v } : undefined
    },
  }
}

test('priorité cookie sur query', () => {
  const locale = resolvePublicLocale({
    cookieStore: mockStore({ [ARQUANTIX_LOCALE_COOKIE]: 'fr' }),
    searchParams: { locale: 'en' },
  })
  assert.equal(locale, 'fr')
})

test('sans cookie, utilise searchParams valide', () => {
  const locale = resolvePublicLocale({
    cookieStore: mockStore({}),
    searchParams: { locale: 'en' },
  })
  assert.equal(locale, 'en')
})

test('sans cookie ni query valide → en (défaut site)', () => {
  const locale = resolvePublicLocale({
    cookieStore: mockStore({}),
    searchParams: { locale: 'xx' },
  })
  assert.equal(locale, 'en')
})

test('searchParams locale en tableau', () => {
  const locale = resolvePublicLocale({
    cookieStore: mockStore({}),
    searchParams: { locale: ['it', 'en'] },
  })
  assert.equal(locale, 'it')
})

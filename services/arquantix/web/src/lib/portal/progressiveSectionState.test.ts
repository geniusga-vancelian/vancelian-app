import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  failSectionState,
  initSectionState,
  resetSectionState,
  startSectionState,
  succeedSectionState,
  type PortalSectionState,
} from './progressiveSectionState'

type Demo = { value: number }

function baseState(overrides: Partial<PortalSectionState<Demo>> = {}): PortalSectionState<Demo> {
  return { data: null, loading: false, refreshing: false, error: '', ...overrides }
}

test('initSectionState: cache vide → loading plein', () => {
  const s = initSectionState<Demo>({ data: null, hasInitialData: false, isFresh: false })
  assert.equal(s.loading, true)
  assert.equal(s.refreshing, false)
  assert.equal(s.data, null)
  assert.equal(s.error, '')
})

test('initSectionState: cache stale présent → pas de loading (pas de flash)', () => {
  const s = initSectionState<Demo>({ data: { value: 1 }, hasInitialData: true, isFresh: false })
  assert.equal(s.loading, false)
  assert.deepEqual(s.data, { value: 1 })
})

test('startSectionState: premier chargement → loading=true', () => {
  const s = startSectionState(baseState(), {
    hasDisplayed: false,
    isManualRefresh: false,
    isFresh: false,
  })
  assert.equal(s.loading, true)
  assert.equal(s.refreshing, false)
})

test('startSectionState: données affichées + stale → refreshing, pas loading', () => {
  const s = startSectionState(baseState({ data: { value: 2 } }), {
    hasDisplayed: true,
    isManualRefresh: false,
    isFresh: false,
  })
  assert.equal(s.loading, false)
  assert.equal(s.refreshing, true)
  assert.deepEqual(s.data, { value: 2 })
})

test('startSectionState: refresh manuel → refreshing même si déjà affiché', () => {
  const s = startSectionState(baseState({ data: { value: 3 } }), {
    hasDisplayed: true,
    isManualRefresh: true,
    isFresh: true,
  })
  assert.equal(s.refreshing, true)
  assert.equal(s.loading, false)
})

test('startSectionState: reset error au démarrage', () => {
  const s = startSectionState(baseState({ error: 'boom' }), {
    hasDisplayed: false,
    isManualRefresh: false,
    isFresh: false,
  })
  assert.equal(s.error, '')
})

test('succeedSectionState: données fraîches, tout nettoyé', () => {
  const s = succeedSectionState<Demo>({ value: 9 })
  assert.deepEqual(s.data, { value: 9 })
  assert.equal(s.loading, false)
  assert.equal(s.refreshing, false)
  assert.equal(s.error, '')
})

test('failSectionState: stale dispo → pas d’erreur visible', () => {
  const s = failSectionState(baseState(), {
    staleData: { value: 5 },
    errorMessage: 'oops',
  })
  assert.deepEqual(s.data, { value: 5 })
  assert.equal(s.error, '')
  assert.equal(s.loading, false)
})

test('failSectionState: pas de stale mais data précédente → conserve data, pas d’erreur', () => {
  const s = failSectionState(baseState({ data: { value: 7 } }), {
    staleData: null,
    errorMessage: 'oops',
  })
  assert.deepEqual(s.data, { value: 7 })
  assert.equal(s.error, '')
})

test('failSectionState: aucune donnée → erreur visible', () => {
  const s = failSectionState(baseState(), {
    staleData: null,
    errorMessage: 'Unable to load section.',
  })
  assert.equal(s.data, null)
  assert.equal(s.error, 'Unable to load section.')
})

test('resetSectionState: nouveau scope sans cache → loading', () => {
  const s = resetSectionState<Demo>({ data: null, hasInitialData: false, isFresh: false })
  assert.equal(s.loading, true)
  assert.equal(s.data, null)
})

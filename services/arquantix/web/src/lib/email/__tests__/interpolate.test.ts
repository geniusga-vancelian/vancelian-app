import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { z } from 'zod'
import {
  interpolate,
  prepareVarsForMjml,
  validateVars,
  EmailTemplateVarsError,
} from '@/lib/email/interpolate'

describe('interpolate (Mustache wrapper)', () => {
  it('substitue les variables {{var}} avec escape HTML par défaut', () => {
    const out = interpolate('Hello {{name}}!', { name: '<script>alert(1)</script>' })
    assert.equal(out, 'Hello &lt;script&gt;alert(1)&lt;&#x2F;script&gt;!')
  })

  it('rend les sections vides quand la valeur est falsy', () => {
    const out = interpolate('A{{#shown}}B{{/shown}}C', { shown: false })
    assert.equal(out, 'AC')
  })

  it('itère les arrays via une section', () => {
    const out = interpolate('{{#items}}[{{name}}]{{/items}}', {
      items: [{ name: 'a' }, { name: 'b' }, { name: 'c' }],
    })
    assert.equal(out, '[a][b][c]')
  })

  it('expose les partials passés en 3e argument', () => {
    const partials = { Greeting: 'Hello {{name}}!' }
    const out = interpolate('{{> Greeting}}', { name: 'Sarah' }, partials)
    assert.equal(out, 'Hello Sarah!')
  })

  it('triple-mustache {{{html}}} ne fait pas d’échappement', () => {
    const out = interpolate('{{{raw}}}', { raw: '<b>ok</b>' })
    assert.equal(out, '<b>ok</b>')
  })
})

describe('prepareVarsForMjml', () => {
  it('remplace null/undefined par chaîne vide pour éviter [object]', () => {
    const out = prepareVarsForMjml({ a: null, b: undefined, c: 'x' })
    assert.equal(out.a, '')
    assert.equal(out.b, '')
    assert.equal(out.c, 'x')
  })

  it('préserve arrays et objets', () => {
    const arr = [1, 2, 3]
    const obj = { foo: 'bar' }
    const out = prepareVarsForMjml({ arr, obj })
    assert.equal(out.arr, arr)
    assert.equal(out.obj, obj)
  })
})

describe('validateVars', () => {
  const schema = z.object({ a: z.string().min(2) })

  it('renvoie les vars typées si valides', () => {
    const v = validateVars(schema, { a: 'hello' })
    assert.equal(v.a, 'hello')
  })

  it('lève EmailTemplateVarsError si invalide, avec issues détaillées', () => {
    assert.throws(
      () => validateVars(schema, { a: 'x' }),
      (err) =>
        err instanceof EmailTemplateVarsError &&
        err.zodError.issues.length > 0 &&
        err.message.includes('a:'),
    )
  })
})

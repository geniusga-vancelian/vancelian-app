import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  renderMjmlString,
  MjmlValidationError,
} from '@/lib/email/mjmlRender'

const VALID_MJML = `
<mjml>
  <mj-body>
    <mj-section>
      <mj-column>
        <mj-text>Hi</mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>`

describe('renderMjmlString', () => {
  it('produit du HTML valide à partir de MJML correct', async () => {
    const r = await renderMjmlString(VALID_MJML, { validationLevel: 'strict' })
    assert.ok(r.html.length > 500, 'HTML doit être substantiel')
    assert.ok(r.html.includes('<table'), 'doit contenir des tables (output MJML)')
    assert.ok(r.html.toLowerCase().includes('<!doctype'), 'doit avoir un doctype')
    assert.equal(r.errors.length, 0)
  })

  it('lève MjmlValidationError en mode strict si le MJML est invalide', async () => {
    const broken = '<mjml><mj-body><mj-section><mj-column><mj-foobar>x</mj-foobar></mj-column></mj-section></mj-body></mjml>'
    await assert.rejects(
      () => renderMjmlString(broken, { validationLevel: 'strict' }),
      (err) => err instanceof MjmlValidationError && err.errors.length > 0,
    )
  })

  it('ne lève pas en mode skip même avec une balise inconnue', async () => {
    const broken = '<mjml><mj-body><mj-section><mj-column><mj-foobar>x</mj-foobar></mj-column></mj-section></mj-body></mjml>'
    const r = await renderMjmlString(broken, { validationLevel: 'skip' })
    assert.ok(typeof r.html === 'string')
  })
})

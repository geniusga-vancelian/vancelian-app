import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { parseLombardApiError } from '@/lib/portal/lombard/parseLombardApiError'

describe('parseLombardApiError', () => {
  it('maps 401 to session message (not OTP exchange copy)', () => {
    const msg = parseLombardApiError({ error: 'unauthorized' }, 401)
    assert.match(msg, /Session expirée/i)
    assert.doesNotMatch(msg, /ouvrir votre session pour le moment/i)
  })

  it('uses API message when present', () => {
    const msg = parseLombardApiError(
      { code: 'lombard.invalid_target_ltv', message: 'Choose a target LTV between 1% and 70%.' },
      400,
    )
    assert.equal(msg, 'Choose a target LTV between 1% and 70%.')
  })

  it('maps Zod invalid borrow amount to French hint', () => {
    const msg = parseLombardApiError(
      { error: 'Invalid request data', issues: [{ message: 'Invalid borrow amount.' }] },
      400,
    )
    assert.match(msg, /Montant emprunté invalide/i)
  })
})

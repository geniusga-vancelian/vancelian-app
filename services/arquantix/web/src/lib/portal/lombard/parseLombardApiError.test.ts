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

  it('maps borrow_exceeds_capacity to French product copy', () => {
    const msg = parseLombardApiError(
      {
        code: 'lombard.borrow_exceeds_capacity',
        message: 'Maximum available borrow is 0 USDC at 28% LTV with your current cbETH balance.',
      },
      400,
    )
    assert.match(msg, /capacité d’emprunt/i)
  })

  it('maps prepare_timeout to French product copy', () => {
    const msg = parseLombardApiError(
      { code: 'lombard.prepare_timeout', message: 'timeout' },
      504,
    )
    assert.match(msg, /préparation de l’emprunt a expiré/i)
  })
})

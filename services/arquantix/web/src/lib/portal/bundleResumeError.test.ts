import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { normalizeBundleResumeError } from '@/lib/portal/bundleResumeError'

describe('normalizeBundleResumeError', () => {
  it('mappe Internal Server Error vers message français', () => {
    assert.equal(
      normalizeBundleResumeError(new Error('Internal Server Error')),
      'Service temporairement indisponible — réessayez le rééquilibrage dans quelques instants.',
    )
  })

  it('mappe timeout resume', () => {
    assert.equal(
      normalizeBundleResumeError(new Error('signal timed out')),
      'La reprise du rééquilibrage a expiré — réessayez dans quelques instants.',
    )
  })
})

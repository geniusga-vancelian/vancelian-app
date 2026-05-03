import assert from 'node:assert'
import { describe, it } from 'node:test'
import { mergeSiblingOrderPreservingHidden } from '@/lib/admin/siteStructureReorder'

describe('mergeSiblingOrderPreservingHidden', () => {
  it('préserve les frères absents du bucket visuel (ex. vault sous autre nœud)', () => {
    const merged = mergeSiblingOrderPreservingHidden(
      ['vault', 'x', 'y'],
      ['y', 'x'],
      new Set(['x', 'y']),
    )
    assert.deepStrictEqual(merged, ['vault', 'y', 'x'])
  })
})

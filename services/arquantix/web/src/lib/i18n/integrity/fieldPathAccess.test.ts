import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { getStringAtLot1Path, tokenizeLot1Path } from '@/lib/i18n/integrity/fieldPathAccess'

describe('tokenizeLot1Path', () => {
  it('modules[n].content.title', () => {
    assert.deepEqual(tokenizeLot1Path('modules[2].content.title'), ['modules', 2, 'content', 'title'])
  })

  it('keyStats[i].label', () => {
    assert.deepEqual(tokenizeLot1Path('keyStats[0].label'), ['keyStats', 0, 'label'])
  })
})

describe('getStringAtLot1Path', () => {
  it('vault racine', () => {
    const root = { pageTitle: { text: 'Titre' } }
    assert.equal(getStringAtLot1Path(root, 'vault', 'pageTitle.text'), 'Titre')
  })

  it('cms data.title', () => {
    const data = { title: 'Hello', keyStats: [{ label: 'L', value: 'V' }] }
    assert.equal(getStringAtLot1Path(data, 'cms_section', 'data.title'), 'Hello')
    assert.equal(getStringAtLot1Path(data, 'cms_section', 'data.keyStats[0].label'), 'L')
  })
})

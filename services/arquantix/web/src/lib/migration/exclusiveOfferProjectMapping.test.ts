import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildVaultModulesFromProject,
  mapCompetitiveAdvantagesJson,
  mapHowItWorksToMarkdown,
  mapKeyInformationJson,
  mapProjectStatusToCommercial,
} from './exclusiveOfferProjectMapping'

describe('exclusiveOfferProjectMapping', () => {
  it('mapProjectStatusToCommercial', () => {
    assert.equal(mapProjectStatusToCommercial('PUBLISHED'), 'PUBLISHED')
    assert.equal(mapProjectStatusToCommercial('DRAFT'), 'DRAFT')
  })

  it('mapCompetitiveAdvantagesJson parses template-like rows', () => {
    const raw = {
      title: 'Atouts',
      rows: [
        {
          icon: 'x',
          iconBackgroundColor: '#111',
          title: 'A',
          description: 'd',
        },
      ],
    }
    const r = mapCompetitiveAdvantagesJson(raw)
    assert.equal(r.title, 'Atouts')
    assert.equal(r.rows.length, 1)
    assert.equal((r.rows[0] as { title: string }).title, 'A')
  })

  it('mapKeyInformationJson flattens infoContent into value', () => {
    const r = mapKeyInformationJson({
      title: 'Infos',
      rows: [
        { label: 'L', value: 'V', showInfoIcon: true, infoTitle: 't', infoContent: 'extra' },
      ],
    })
    assert.ok(r.rows[0].value.includes('extra'))
  })

  it('mapHowItWorksToMarkdown', () => {
    const r = mapHowItWorksToMarkdown({
      title: 'How',
      content: 'line1',
      links: [{ label: 'a', url: 'https://x.com' }],
    })
    assert.ok(r.markdown.includes('line1'))
    assert.ok(r.markdown.includes('[a](https://x.com)'))
  })

  it('buildVaultModulesFromProject produces TitlePage + markdown + legal', () => {
    const mods = buildVaultModulesFromProject({
      projectId: 'clxxxxxxxxxxxxxxxxxxxxxx01',
      title: 'T',
      shortDescription: 'S',
      description: '# Hello',
      competitiveAdvantages: null,
      howItWorks: null,
      keyInformation: null,
      faq: { items: [] },
    })
    assert.ok(mods.some((m) => m.type === 'TitlePage'))
    assert.ok(mods.some((m) => m.type === 'SimpleMarkdownContentModule'))
    assert.ok(mods.some((m) => m.type === 'ContentBasDePageSansModuleBlanc'))
  })
})

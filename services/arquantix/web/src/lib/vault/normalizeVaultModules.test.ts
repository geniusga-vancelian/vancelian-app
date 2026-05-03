import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { buildVaultModulesFromProject } from '@/lib/migration/exclusiveOfferProjectMapping'
import {
  normalizeDocumentsListModuleContent,
  normalizeVaultModulesArray,
  normalizeVaultModulesFromSectionData,
  normalizeVaultBuilderSectionDataRoot,
} from '@/lib/vault/normalizeVaultModules'

describe('normalizeDocumentsListModuleContent', () => {
  it('laisse documentEntries inchangé si déjà présent', () => {
    const c = {
      documentEntries: [{ mediaId: 'm1', documentName: 'A' }],
      documentMediaIds: ['m2'],
    }
    const out = normalizeDocumentsListModuleContent(c)
    assert.equal((out.documentEntries as unknown[]).length, 1)
    assert.equal((out.documentEntries as { mediaId: string }[])[0].mediaId, 'm1')
  })

  it('dérive documentEntries depuis documentMediaIds legacy', () => {
    const out = normalizeDocumentsListModuleContent({
      documentMediaIds: [' id1 ', '', 'id2'],
    })
    const e = out.documentEntries as { mediaId: string; documentName: string }[]
    assert.equal(e.length, 2)
    assert.equal(e[0].mediaId, 'id1')
    assert.equal(e[1].mediaId, 'id2')
    assert.equal(e[0].documentName, '')
  })
})

describe('normalizeVaultModulesArray', () => {
  it('filtre enabled: false', () => {
    const { modules, warnings } = normalizeVaultModulesArray([
      { id: 'a', type: 'TitlePage', enabled: false, content: {} },
      { id: 'b', type: 'TitlePage', enabled: true, content: { title: 'T' } },
    ])
    assert.equal(modules.length, 1)
    assert.equal(modules[0].id, 'b')
    assert.equal(warnings.length, 0)
  })

  it('résout type depuis clé legacy module', () => {
    const { modules, warnings } = normalizeVaultModulesArray([
      { id: 'x', module: 'TitlePage', content: { title: 'Hi' } },
    ])
    assert.equal(modules.length, 1)
    assert.equal(modules[0].type, 'TitlePage')
    assert.ok(warnings.some((w) => w.includes('alias legacy')))
  })

  it('avertit si type et module divergent et préfère type', () => {
    const { modules, warnings } = normalizeVaultModulesArray([
      { id: 'x', type: 'TitlePage', module: 'TagsModule', content: {} },
    ])
    assert.equal(modules[0].type, 'TitlePage')
    assert.ok(warnings.some((w) => w.includes('divergents')))
  })

  it('signale type inconnu et type admin sans renderer web', () => {
    const { modules, warnings } = normalizeVaultModulesArray([
      { id: '1', type: 'TotalementInconnu', content: {} },
      { id: '2', type: 'AllocationModule', content: { title: 'A' } },
    ])
    assert.equal(modules.length, 2)
    assert.ok(warnings.some((w) => w.includes('absent du catalogue')))
    assert.ok(warnings.some((w) => w.includes('sans renderer web dédié')))
  })

  it('génère id stable si id absent', () => {
    const { modules } = normalizeVaultModulesArray([
      { type: 'TagsModule', content: { tags: ['x'] } },
    ])
    assert.equal(modules[0].id, 'gen-vault-mod:0:TagsModule')
  })

  it('non-tableau modules → vide + warning', () => {
    const { modules, warnings } = normalizeVaultModulesArray({ foo: 1 }, 'ctx')
    assert.equal(modules.length, 0)
    assert.ok(warnings.some((w) => w.includes('n’est pas un tableau')))
  })
})

describe('normalizeVaultModulesFromSectionData', () => {
  it('lit data.modules depuis racine', () => {
    const { modules } = normalizeVaultModulesFromSectionData({
      templateKey: 'PageSimpleNavBarTopTitlePageContent',
      modules: [{ id: 'm', type: 'TitlePage', content: { title: 'X' } }],
    })
    assert.equal(modules.length, 1)
    assert.equal(modules[0].content.title, 'X')
  })
})

describe('normalizeVaultBuilderSectionDataRoot', () => {
  it('préserve les clés racine et remplace modules', () => {
    const { data, warnings } = normalizeVaultBuilderSectionDataRoot({
      templateKey: 'PageSimpleNavBarTopTitlePageContent',
      headerMediaId: 'hm',
      modules: [{ type: 'DocumentsListModule', content: { documentMediaIds: ['d1'] } }],
    })
    assert.ok(data)
    assert.equal(data!.headerMediaId, 'hm')
    const m = data!.modules as NormalizedVaultModuleLike[]
    assert.equal(m.length, 1)
    const entries = m[0].content.documentEntries as { mediaId: string }[]
    assert.equal(entries.length, 1)
    assert.equal(entries[0].mediaId, 'd1')
    assert.equal(warnings.length, 0)
  })
})

type NormalizedVaultModuleLike = { type: string; content: Record<string, unknown> }

describe('golden — buildVaultModulesFromProject → normalizer', () => {
  it('produit des types attendus sans warnings bloquants', () => {
    const built = buildVaultModulesFromProject({
      projectId: 'proj_test_01',
      title: 'Titre',
      shortDescription: 'Sous',
      description: '## Corps',
      competitiveAdvantages: null,
      howItWorks: null,
      keyInformation: null,
      faq: { items: [] },
    })
    const { modules, warnings } = normalizeVaultModulesArray(built, 'golden')
    const types = modules.map((m) => m.type)
    assert.ok(types.includes('TitlePage'))
    assert.ok(types.includes('SimpleMarkdownContentModule'))
    assert.ok(types.includes('ContentBasDePageSansModuleBlanc'))
    assert.ok(
      warnings.filter((w) => w.includes('absent du catalogue') || w.includes('n’est pas un tableau'))
        .length === 0,
    )
  })
})

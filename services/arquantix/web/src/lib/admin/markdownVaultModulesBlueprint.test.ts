import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  exportVaultModulesToMarkdown,
  parseVaultModulesMarkdown,
  vaultModulesToLandingModules,
} from './markdownVaultModulesBlueprint'

describe('markdownVaultModulesBlueprint', () => {
  const sampleModules = [
    {
      type: 'SimpleMarkdownContentModule',
      enabled: true,
      content: {
        moduleTitle: 'À propos',
        markdown: 'Texte **riche** avec lien.',
        links: [{ label: 'Site', url: 'https://example.com' }],
      },
    },
    {
      type: 'HEADING',
      enabled: true,
      content: { text: 'Section clé' },
    },
    {
      type: 'FaqAccordionModule',
      enabled: false,
      content: { title: 'FAQ', items: [{ articleSlug: 'what-is-investing' }] },
    },
  ]

  it('export puis import round-trip les modules', () => {
    const exported = exportVaultModulesToMarkdown(sampleModules, 'fr')
    assert.match(exported, /format: vancelian-vault-modules/)
    assert.match(exported, /## Module: SimpleMarkdownContentModule/)
    assert.match(exported, /```vault-module-json/)

    const parsed = parseVaultModulesMarkdown(exported, 'fr')
    assert.equal(parsed.modules.length, 3)
    assert.equal(parsed.modules[0]?.type, 'SimpleMarkdownContentModule')
    assert.equal(parsed.modules[0]?.content.moduleTitle, 'À propos')
    assert.equal(parsed.modules[1]?.type, 'HEADING')
    assert.equal(parsed.modules[2]?.enabled, false)

    const landing = vaultModulesToLandingModules(parsed.modules)
    assert.equal(landing.length, 3)
    assert.ok(landing.every((m) => typeof m.id === 'string' && m.id.length > 10))
    assert.notEqual(landing[0]?.id, landing[1]?.id)
  })

  it('ignore un type de module inconnu avec avertissement', () => {
    const md = exportVaultModulesToMarkdown(
      [{ type: 'TotallyUnknownModule', enabled: true, content: { foo: 'bar' } }],
      'fr',
    )
    const parsed = parseVaultModulesMarkdown(md, 'fr')
    assert.equal(parsed.modules.length, 0)
    assert.ok(parsed.warnings.some((w) => w.code === 'MODULE_TYPE_UNKNOWN'))
  })

  it('rejette un YAML invalide', () => {
    const parsed = parseVaultModulesMarkdown('---\nfoo: [\n---\n\n# x', 'fr')
    assert.equal(parsed.modules.length, 0)
    assert.ok(parsed.warnings.some((w) => w.code === 'YAML_INVALID'))
  })
})

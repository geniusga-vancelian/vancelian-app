import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { ArticleBlockType } from '@prisma/client'
import {
  exportArticleBlocksToMarkdown,
  isArticleBlocksMarkdownExport,
  parseArticleBlocksMarkdown,
} from './markdownArticleBlocksBlueprint'

describe('markdownArticleBlocksBlueprint', () => {
  const sampleBlocks = [
    {
      type: ArticleBlockType.HEADING,
      data: { text: 'Introduction' },
    },
    {
      type: ArticleBlockType.PARAGRAPH,
      data: { text: 'Texte **riche** avec lien.' },
    },
    {
      type: ArticleBlockType.KEY_INFORMATION,
      data: {
        title: 'Informations clés',
        ctaLabel: '',
        ctaHref: '',
        rows: [{ label: 'Durée', value: '5 ans' }],
      },
    },
    {
      type: ArticleBlockType.BULLET_LIST,
      data: { items: ['Premier point', 'Deuxième point'] },
    },
  ]

  it('export puis import round-trip les blocs', () => {
    const exported = exportArticleBlocksToMarkdown(sampleBlocks, 'fr')
    assert.match(exported, /format: vancelian-article-blocks/)
    assert.match(exported, /## Block: HEADING/)
    assert.match(exported, /```article-block-json/)

    assert.equal(isArticleBlocksMarkdownExport(exported), true)

    const parsed = parseArticleBlocksMarkdown(exported, 'fr')
    assert.equal(parsed.blocks.length, 4)
    assert.equal(parsed.blocks[0]?.type, ArticleBlockType.HEADING)
    assert.equal(parsed.blocks[0]?.data.text, 'Introduction')
    assert.equal(parsed.blocks[1]?.type, ArticleBlockType.PARAGRAPH)
    assert.equal(parsed.blocks[2]?.type, ArticleBlockType.KEY_INFORMATION)
    assert.equal(parsed.blocks[3]?.type, ArticleBlockType.BULLET_LIST)
    assert.deepEqual(parsed.blocks[3]?.data.items, ['Premier point', 'Deuxième point'])
  })

  it('exporte une liste vide', () => {
    const exported = exportArticleBlocksToMarkdown([], 'en')
    assert.match(exported, /_Aucun bloc\._/)
    const parsed = parseArticleBlocksMarkdown(exported, 'en')
    assert.equal(parsed.blocks.length, 0)
  })

  it('ignore un type de bloc inconnu avec avertissement', () => {
    const md = [
      '---',
      'format: vancelian-article-blocks',
      'version: 1',
      'locale: fr',
      '---',
      '',
      '## Block: TotallyUnknownBlock',
      '',
      '```article-block-json',
      '{ "foo": "bar" }',
      '```',
      '',
    ].join('\n')
    const parsed = parseArticleBlocksMarkdown(md, 'fr')
    assert.equal(parsed.blocks.length, 0)
    assert.ok(parsed.warnings.some((w) => w.code === 'BLOCK_TYPE_UNKNOWN'))
  })

  it('rejette un YAML invalide', () => {
    const parsed = parseArticleBlocksMarkdown('---\nfoo: [\n---\n\n# x', 'fr')
    assert.equal(parsed.blocks.length, 0)
    assert.ok(parsed.warnings.some((w) => w.code === 'YAML_INVALID'))
  })
})

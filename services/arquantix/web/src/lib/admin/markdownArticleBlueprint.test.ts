import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ArticleBlockType } from '@prisma/client'
import { parseMarkdownArticleBlueprint } from './markdownArticleBlueprint'

const FIXTURE_PATH =
  '/Users/gael_mac/Downloads/wall-street-on-chain-convergence-2030.md'

describe('parseMarkdownArticleBlueprint', () => {
  it('parse le fixture Wall Street (metadata + blocs structurés)', () => {
    let markdown: string
    try {
      markdown = readFileSync(FIXTURE_PATH, 'utf8')
    } catch {
      console.warn('Fixture non trouvé, test ignoré:', FIXTURE_PATH)
      return
    }

    const result = parseMarkdownArticleBlueprint(markdown, 'en')

    assert.equal(result.metadata.slug, 'wall-street-on-chain-convergence-2030')
    assert.match(result.metadata.title, /Wall Street On-Chain/)
    assert.match(result.metadata.standfirst, /Citi's Tokenization 2030/)
    assert.equal(result.metadata.status, 'DRAFT')
    assert.equal(result.metadata.authorName, 'Vancelian Research')
    assert.equal(result.metadata.metaTitle, 'Tokenization 2030: convergence of banks & crypto | Vancelian')
    assert.ok(result.metadata.seoJson.focus_keywords?.includes('tokenization 2030'))
    assert.ok(result.metadata.seoJson.named_entities?.includes('Citi Institute'))

    const types = result.blocks.map((b) => b.type)
    assert.ok(types.includes(ArticleBlockType.KEY_INFORMATION), 'key_facts frontmatter')
    assert.ok(types.includes(ArticleBlockType.QUOTE), 'blockquote')
    assert.ok(types.includes(ArticleBlockType.HEADING), 'sections')
    assert.ok(types.includes(ArticleBlockType.BULLET_LIST), 'listes')
    assert.ok(types.includes(ArticleBlockType.PARAGRAPH), 'paragraphes')

    const learnMoreIdx = result.blocks.findIndex(
      (b) =>
        b.type === ArticleBlockType.HEADING &&
        String((b.data as { text?: string }).text).toLowerCase() === 'learn more',
    )
    assert.ok(learnMoreIdx >= 0, 'section Learn more')
    assert.equal(result.blocks[learnMoreIdx + 1]?.type, ArticleBlockType.PARAGRAPH)

    const sourcesHeading = result.blocks.filter(
      (b) =>
        b.type === ArticleBlockType.HEADING &&
        String((b.data as { text?: string }).text).toLowerCase() === 'sources',
    )
    assert.equal(sourcesHeading.length, 1)

    const h1Skipped = result.warnings.some((w) => w.code === 'H1_SKIPPED')
    assert.ok(h1Skipped)
  })

  it('rejette un YAML invalide', () => {
    const bad = '---\nfoo: [\n---\n\n# Hi'
    const result = parseMarkdownArticleBlueprint(bad, 'en')
    assert.equal(result.blocks.length, 0)
    assert.ok(result.warnings.some((w) => w.code === 'YAML_INVALID'))
  })
})

/**
 * Après `zodSchema.parse`, les champs effectivement lus par `mapDataToComponentProps`
 * (URLs résolues, alias, contexte Help, etc.) ne doivent pas être supprimés.
 * Un test par famille de module — ajouter une entrée ici lors de tout nouveau champ résolu côté renderer.
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { getSectionType } from '@/lib/sections/library'

function parse(key: string, input: Record<string, unknown>) {
  const st = getSectionType(key)
  assert.ok(st, `section type ${key}`)
  return st!.zodSchema.parse(input) as Record<string, unknown>
}

describe('Zod — pas de strip des champs alignés renderer (module par module)', () => {
  it('feature_grid : médias, corps, CTA legacy', () => {
    const out = parse('feature_grid', {
      title: 'T',
      imageUrl: 'https://a',
      imageMediaUrl: 'https://b',
      content: 'C',
      ctaText: 'Go',
      ctaLink: '/x',
    })
    assert.equal(out.imageMediaUrl, 'https://b')
    assert.equal(out.ctaText, 'Go')
  })

  it('cta : backgroundMediaUrl + alias ctaText', () => {
    const out = parse('cta', {
      title: 'T',
      backgroundMediaUrl: 'https://bg',
      ctaText: 'Legacy',
      ctaLink: '/l',
    })
    assert.equal(out.backgroundMediaUrl, 'https://bg')
    assert.equal(out.ctaText, 'Legacy')
  })

  it('project_grid : resolvedProjects + backgroundImage sur item', () => {
    const out = parse('project_grid', {
      title: 'G',
      resolvedProjects: [{ id: '1', slug: 'a' }],
      items: [{ title: 'x', backgroundImage: 'https://card' }],
    })
    assert.ok(Array.isArray(out.resolvedProjects))
    assert.equal((out.resolvedProjects as unknown[]).length, 1)
    const items = out.items as Array<Record<string, unknown>>
    assert.equal(items[0].backgroundImage, 'https://card')
  })

  it('how_it_works : imageMediaUrl sur une étape', () => {
    const out = parse('how_it_works', {
      steps: [
        {
          number: '1',
          title: 'A',
          description: 'B',
          imageMediaUrl: 'https://step',
        },
      ],
    })
    const steps = out.steps as Array<Record<string, unknown>>
    assert.equal(steps[0].imageMediaUrl, 'https://step')
  })

  it('media_text : imageMediaUrl + alt', () => {
    const out = parse('media_text', {
      title: 'T',
      imageMediaUrl: 'https://i',
      imageMediaAlt: 'Alt',
    })
    assert.equal(out.imageMediaUrl, 'https://i')
    assert.equal(out.imageMediaAlt, 'Alt')
  })

  it('company_map : backgroundMediaUrl + alt', () => {
    const out = parse('company_map', {
      title: 'T',
      backgroundMediaUrl: ' https://map ',
      backgroundMediaAlt: 'M',
    })
    assert.equal(out.backgroundMediaUrl, ' https://map ')
  })

  it('key_figures : backgroundMediaUrl', () => {
    const out = parse('key_figures', {
      title: 'K',
      stats: [{ value: '1', label: 'L' }],
      backgroundMediaUrl: 'https://kf',
    })
    assert.equal(out.backgroundMediaUrl, 'https://kf')
  })

  it('blog_article_hero : imageMediaUrl', () => {
    const out = parse('blog_article_hero', {
      title: 'Article',
      imageMediaUrl: 'https://cover',
    })
    assert.equal(out.imageMediaUrl, 'https://cover')
  })

  it('blog_article_reader : __demoBlogArticle', () => {
    const demo = { id: 'demo', slug: 's' }
    const out = parse('blog_article_reader', {
      blogLabel: 'B',
      __demoBlogArticle: demo,
    })
    assert.deepStrictEqual(out.__demoBlogArticle, demo)
  })

  it('testimonials : avatarMediaUrl sur un item', () => {
    const out = parse('testimonials', {
      items: [{ name: 'N', text: 'T', avatarMediaUrl: 'https://av' }],
    })
    const items = out.items as Array<Record<string, unknown>>
    assert.equal(items[0].avatarMediaUrl, 'https://av')
  })

  it('help_hero_v1 : contexte fil d’Ariane stocké dans le JSON', () => {
    const out = parse('help_hero_v1', {
      title: 'H',
      collectionTitle: 'Col',
      categoryTitle: 'Cat',
      showBreadcrumbs: true,
      breadcrumbsRootLabel: 'Racine',
      breadcrumbsSeparator: '›',
      collectionSlug: 'c',
      categorySlug: 'g',
    })
    assert.equal(out.collectionTitle, 'Col')
    assert.equal(out.showBreadcrumbs, true)
    assert.equal(out.collectionSlug, 'c')
  })

  it('help_breadcrumbs_v1 : titres route', () => {
    const out = parse('help_breadcrumbs_v1', {
      rootLabel: 'R',
      collectionTitle: 'C',
      articleTitle: 'A',
    })
    assert.equal(out.articleTitle, 'A')
  })

  it('help_sidebar_toc_v1 : articleId', () => {
    const out = parse('help_sidebar_toc_v1', {
      tocTitle: 'T',
      articleId: 'uuid-1',
    })
    assert.equal(out.articleId, 'uuid-1')
  })
})

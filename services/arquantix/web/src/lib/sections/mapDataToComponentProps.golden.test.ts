/**
 * Golden tests : comportement stable du mapping CMS → props.
 * Toute évolution volontaire du contrat doit mettre à jour ces assertions.
 */

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { mapDataToComponentProps } from '@/lib/sections/mapDataToComponentProps'

describe('mapDataToComponentProps — golden / non-régression', () => {
  it('hero : transmet sidebarText, variante homepage, tags absents', () => {
    const props = mapDataToComponentProps(
      'hero',
      {
        title: 'T1',
        subtitle: 'S1',
        sidebarText: 'Side',
        ctaText: 'Go',
        ctaLink: '/x',
        backgroundMediaUrl: ' https://cdn.example/bg.jpg ',
        backgroundImageOpacity: 0.5,
        tags: ['should', 'not', 'show'],
      },
      'fr',
    )
    assert.deepStrictEqual(
      {
        title: props.title,
        subtitle: props.subtitle,
        sidebarText: props.sidebarText,
        ctaText: props.ctaText,
        ctaLink: props.ctaLink,
        variant: props.variant,
        backgroundImage: props.backgroundImage,
        backgroundImageOpacity: props.backgroundImageOpacity,
        hideCta: props.hideCta,
        inverseOverlay: props.inverseOverlay,
        tags: props.tags,
      },
      {
        title: 'T1',
        subtitle: 'S1',
        sidebarText: 'Side',
        ctaText: 'Go',
        ctaLink: '/x',
        variant: 'homepage',
        backgroundImage: 'https://cdn.example/bg.jpg',
        backgroundImageOpacity: 0.5,
        hideCta: false,
        inverseOverlay: false,
        tags: undefined,
      },
    )
  })

  it('hero_secondary : pastilles + inverseOverlay si image', () => {
    const props = mapDataToComponentProps(
      'hero_secondary',
      {
        title: 'A',
        subtitle: 'B',
        backgroundMediaUrl: '/pic.png',
        tags: [' x ', '', 'y'],
      },
      'fr',
    )
    assert.equal(props.variant, 'secondary')
    assert.deepStrictEqual(props.tags, ['x', 'y'])
    assert.equal(props.inverseOverlay, true)
  })

  it('faq : title, subtitle legacy et description passent tels quels', () => {
    const props = mapDataToComponentProps(
      'faq',
      {
        eyebrow: 'E',
        title: 'T',
        subtitle: 'Legacy',
        description: 'D',
        items: [{ id: '1', question: 'Q', answerMarkdown: 'A' }],
      },
      'fr',
    )
    assert.deepStrictEqual(props, {
      eyebrow: 'E',
      title: 'T',
      subtitle: 'Legacy',
      description: 'D',
      items: [{ id: '1', question: 'Q', answerMarkdown: 'A' }],
    })
  })

  it('faq : ui expand/collapse transmis au composant', () => {
    const props = mapDataToComponentProps(
      'faq',
      {
        title: 'T',
        items: [],
        ui: { expandAllLabel: 'Ouvrir tout', collapseAllLabel: 'Fermer tout' },
      },
      'fr',
    )
    assert.deepStrictEqual(props.ui, {
      expandAllLabel: 'Ouvrir tout',
      collapseAllLabel: 'Fermer tout',
    })
  })

  it('cta : alias ctaText / ctaLink lorsque primary vide (falsy)', () => {
    const props = mapDataToComponentProps(
      'cta',
      {
        eyebrow: 'E',
        title: 'T',
        description: 'D',
        primaryButtonText: '',
        primaryButtonHref: '',
        ctaText: 'Alias',
        ctaLink: '/alias',
      },
      'fr',
    )
    assert.equal(props.primaryButtonText, 'Alias')
    assert.equal(props.primaryButtonHref, '/alias')
    assert.equal(props.marketingVariant, 'image')
  })

  it('cta : primaryButton l’emporte sur ctaText si non vide', () => {
    const props = mapDataToComponentProps(
      'cta',
      {
        primaryButtonText: 'Canon',
        primaryButtonHref: '/c',
        ctaText: 'Alias',
        ctaLink: '/a',
      },
      'fr',
    )
    assert.equal(props.primaryButtonText, 'Canon')
    assert.equal(props.primaryButtonHref, '/c')
  })

  it('feature_grid : imageMediaUrl prioritaire sur imageUrl', () => {
    const props = mapDataToComponentProps(
      'feature_grid',
      {
        title: 'F',
        description: 'Desc',
        imageMediaUrl: 'https://m',
        imageUrl: 'https://legacy',
      },
      'fr',
    )
    assert.equal(props.imageUrl, 'https://m')
  })

  it('project_grid : branche resolvedProjects sans items mappés', () => {
    const resolved = [{ id: 'p1' }]
    const props = mapDataToComponentProps(
      'project_grid',
      {
        title: 'Offres',
        eyebrow: 'E',
        description: 'D',
        resolvedProjects: resolved,
        showAllExclusiveOffers: true,
        viewAllButtonText: 'Voir tout',
      },
      'fr',
    )
    assert.deepStrictEqual(props, {
      title: 'Offres',
      description: 'D',
      eyebrow: 'E',
      resolvedProjects: resolved,
      showAllExclusiveOffers: true,
      viewAllButtonText: 'Voir tout',
    })
  })

  it('project_grid : items legacy — mediaUrl → backgroundImage', () => {
    const props = mapDataToComponentProps(
      'project_grid',
      {
        items: [{ title: 'X', mediaUrl: 'https://card.jpg' }],
      },
      'fr',
    )
    assert.ok(Array.isArray(props.items))
    assert.equal(props.items[0].backgroundImage, 'https://card.jpg')
  })

  it('how_it_works : surface toujours light (ignore CMS)', () => {
    const props = mapDataToComponentProps(
      'how_it_works',
      {
        surface: 'dark',
        label: 'L',
        title: 'T',
      },
      'fr',
    )
    assert.equal(props.surface, 'light')
  })

  it('blog_feed : loadMoreLabel par défaut siteCommonCta fr', () => {
    const props = mapDataToComponentProps('blog_feed', {}, 'fr')
    assert.equal(props.loadMoreLabel, 'Charger plus')
  })

  it('clé instanciée project_grid_2 : même mapping que project_grid', () => {
    const props = mapDataToComponentProps('project_grid_2', { title: 'T2' }, 'fr')
    assert.equal(props.title, 'T2')
  })
})

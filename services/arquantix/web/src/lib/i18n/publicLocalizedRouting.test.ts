import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildLocalizedCmsPagePath,
  buildLocalizedHomePath,
  buildLocalizedProjectDetailPath,
  buildLocalizedProjectHubPath,
  getActiveLocaleFromPathname,
  isPublicHrefExternalNavigation,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from './publicLocalizedRouting'

describe('publicLocalizedRouting', () => {
  it('getActiveLocaleFromPathname lit le préfixe locale', () => {
    assert.equal(getActiveLocaleFromPathname('/fr/projects'), 'fr')
    assert.equal(getActiveLocaleFromPathname('/en/projects/foo'), 'en')
  })

  it('builders', () => {
    assert.equal(buildLocalizedProjectHubPath('it'), '/it/projects')
    assert.equal(buildLocalizedProjectDetailPath('en', 'x'), '/en/projects/x')
    assert.equal(buildLocalizedHomePath('fr'), '/fr')
    assert.equal(buildLocalizedCmsPagePath('en', 'about'), '/en/about')
    assert.equal(buildLocalizedCmsPagePath('fr', 'home'), '/fr')
  })

  it('localizePublicInternalHref remplace la locale préfixée', () => {
    assert.equal(localizePublicInternalHref('/fr/projects/a', 'en'), '/en/projects/a')
    assert.equal(localizePublicInternalHref('/fr/about', 'it'), '/it/about')
  })

  it('localizePublicInternalHref gère /projects sans préfixe', () => {
    assert.equal(localizePublicInternalHref('/projects', 'en'), '/en/projects')
    assert.equal(localizePublicInternalHref('/projects/z', 'it'), '/it/projects/z')
  })

  it('legacy top-level inchangé (blog, help, app)', () => {
    assert.equal(localizePublicInternalHref('/blog/foo', 'en'), '/blog/foo')
    assert.equal(localizePublicInternalHref('/help/a/b', 'it'), '/help/a/b')
    assert.equal(localizePublicInternalHref('/app/login', 'en'), '/app/login')
  })

  it('segment CMS seul → /{locale}/{slug}', () => {
    assert.equal(localizePublicInternalHref('/about', 'en'), '/en/about')
  })

  it('externes et ancres non modifiés', () => {
    assert.equal(localizePublicInternalHref('https://x/y', 'en'), 'https://x/y')
    assert.equal(localizePublicInternalHref('#x', 'en'), '#x')
    assert.equal(shouldSkipLocalizePublicHref('#'), true)
    assert.equal(isPublicHrefExternalNavigation('https://a'), true)
    assert.equal(isPublicHrefExternalNavigation('/en/a'), false)
  })
})

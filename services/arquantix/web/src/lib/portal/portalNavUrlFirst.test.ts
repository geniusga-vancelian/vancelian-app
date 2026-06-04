import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, it } from 'node:test'

import { resolvePortalShellSegmentLoadingMode } from '@/components/portal/portalShellMainNavigation'
import { hasPortalRouteCachedPreview } from '@/lib/portal/portalRouteCachePreview'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

describe('portalNavUrlFirst — URL-first shell navigation', () => {
  it('segment loading : preview si cache, sinon skeleton', () => {
    assert.equal(resolvePortalShellSegmentLoadingMode(true), 'preview')
    assert.equal(resolvePortalShellSegmentLoadingMode(false), 'skeleton')
  })

  it('NavPendingContext — pas de pending optimiste (source statique)', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/components/site/NavPendingContext.tsx'),
      'utf8',
    )
    assert.doesNotMatch(source, /pendingPath\s*\?\?/)
    assert.doesNotMatch(source, /useState.*[Pp]ending/)
    assert.match(source, /isNavigating: false/)
    assert.match(source, /effectivePath: pathname/)
  })

  it('PortalNavLink — Link natif, pas setPendingPath ni preventDefault', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/components/portal/PortalNavLink.tsx'),
      'utf8',
    )
    assert.match(source, /from 'next\/link'/)
    assert.match(source, /<Link/)
    assert.doesNotMatch(source, /setPendingPath/)
    assert.doesNotMatch(source, /preventDefault/)
    assert.doesNotMatch(source, /useNavPending/)
    assert.doesNotMatch(source, /router\.push/)
  })

  it('PortalTopnav — active state depuis pathname', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/components/portal/PortalTopnav.tsx'),
      'utf8',
    )
    assert.match(source, /usePathname/)
    assert.match(source, /isNavActive\(pathname/)
    assert.doesNotMatch(source, /useNavPending/)
    assert.doesNotMatch(source, /effectivePath/)
  })

  it('PortalShellMain — pas de keep-children ni pending bar', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/components/portal/PortalShellMain.tsx'),
      'utf8',
    )
    assert.doesNotMatch(source, /keep-children/)
    assert.doesNotMatch(source, /useNavPending/)
    assert.doesNotMatch(source, /PortalNavPendingBar/)
    assert.doesNotMatch(source, /pointer-events-none/)
  })

  it('(shell)/loading.tsx — preview ou skeleton destination', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/app/app/(shell)/loading.tsx'),
      'utf8',
    )
    assert.match(source, /usePathname/)
    assert.match(source, /PortalRouteCachedPreview/)
    assert.match(source, /PortalRouteSkeleton/)
    assert.match(source, /hasPortalRouteCachedPreview/)
  })

  it('hasPortalRouteCachedPreview — false pour route sans cache connu', () => {
    assert.equal(hasPortalRouteCachedPreview('/app/search'), false)
    assert.equal(hasPortalRouteCachedPreview(PORTAL_ROUTES.markets), false)
  })
})

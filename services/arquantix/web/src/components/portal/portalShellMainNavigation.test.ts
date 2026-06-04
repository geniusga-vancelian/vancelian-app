import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, it } from 'node:test'

import { resolvePortalShellMainNavMode } from '@/components/portal/portalShellMainNavigation'

describe('portalShellMainNavigation — G4-B1', () => {
  it('idle quand pas de navigation', () => {
    assert.equal(resolvePortalShellMainNavMode(false, false), 'idle')
    assert.equal(resolvePortalShellMainNavMode(false, true), 'idle')
  })

  it('preview quand navigation + cache destination', () => {
    assert.equal(resolvePortalShellMainNavMode(true, true), 'preview')
  })

  it('keep-children quand navigation sans preview (pas de skeleton)', () => {
    assert.equal(resolvePortalShellMainNavMode(true, false), 'keep-children')
  })

  it('PortalShellMain ne monte plus PortalRouteSkeleton sans preview', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/components/portal/PortalShellMain.tsx'),
      'utf8',
    )
    assert.doesNotMatch(source, /next\/dynamic/)
    assert.doesNotMatch(source, /PortalRouteSkeleton/)
    assert.match(source, /resolvePortalShellMainNavMode/)
    assert.match(source, /pointer-events-none/)
    assert.match(source, /PortalRouteCachedPreview/)
  })
})

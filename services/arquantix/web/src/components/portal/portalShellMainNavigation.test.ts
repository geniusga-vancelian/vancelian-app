import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, it } from 'node:test'

import { resolvePortalShellSegmentLoadingMode } from '@/components/portal/portalShellMainNavigation'

describe('portalShellMainNavigation — URL-first', () => {
  it('preview quand cache destination disponible', () => {
    assert.equal(resolvePortalShellSegmentLoadingMode(true), 'preview')
  })

  it('skeleton quand pas de preview', () => {
    assert.equal(resolvePortalShellSegmentLoadingMode(false), 'skeleton')
  })

  it('PortalShellMain délègue la transition au segment loading', () => {
    const source = readFileSync(
      path.join(process.cwd(), 'src/components/portal/PortalShellMain.tsx'),
      'utf8',
    )
    assert.doesNotMatch(source, /resolvePortalShellMainNavMode/)
    assert.doesNotMatch(source, /keep-children/)
    assert.match(source, /loading\.tsx/)
  })
})

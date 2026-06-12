import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

import { PortalHeroBackgroundVideo } from './PortalHeroBackgroundVideo'

describe('PortalHeroBackgroundVideo', () => {
  it('embed YouTube en lecture auto muette pour le hero', () => {
    const html = renderToStaticMarkup(
      PortalHeroBackgroundVideo({
        videoUrl: 'https://www.youtube.com/watch?v=JpT4qLGlqzE',
      }),
    )
    assert.match(html, /dh-article__video/)
    assert.match(html, /youtube\.com\/embed\/JpT4qLGlqzE/)
    assert.match(html, /autoplay=1/)
    assert.match(html, /mute=1/)
  })
})

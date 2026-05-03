import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  extractYouTubeId,
  extractVimeoId,
  youTubeThumbnailUrl,
} from '@/lib/blog/videoThumbnail'

describe('videoThumbnail — extractYouTubeId', () => {
  it('reconnaît watch?v=', () => {
    assert.equal(extractYouTubeId('https://www.youtube.com/watch?v=dQw4w9WgXcQ'), 'dQw4w9WgXcQ')
  })

  it('reconnaît youtu.be short link', () => {
    assert.equal(extractYouTubeId('https://youtu.be/dQw4w9WgXcQ'), 'dQw4w9WgXcQ')
  })

  it('reconnaît /embed/ et /shorts/ et /v/ et /live/', () => {
    assert.equal(extractYouTubeId('https://www.youtube.com/embed/abcdef12345'), 'abcdef12345')
    assert.equal(extractYouTubeId('https://www.youtube.com/shorts/abcdef12345'), 'abcdef12345')
    assert.equal(extractYouTubeId('https://www.youtube.com/v/abcdef12345'), 'abcdef12345')
    assert.equal(extractYouTubeId('https://www.youtube.com/live/abcdef12345'), 'abcdef12345')
  })

  it('ignore les query params parasites sur watch?v=', () => {
    assert.equal(
      extractYouTubeId('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=ABC'),
      'dQw4w9WgXcQ',
    )
  })

  it('renvoie null sur URL non YouTube', () => {
    assert.equal(extractYouTubeId('https://example.com/foo'), null)
    assert.equal(extractYouTubeId(''), null)
    assert.equal(extractYouTubeId('not a url'), null)
  })

  it('génère bien l\'URL hqdefault', () => {
    assert.equal(
      youTubeThumbnailUrl('dQw4w9WgXcQ'),
      'https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
    )
  })
})

describe('videoThumbnail — extractVimeoId', () => {
  it('reconnaît vimeo.com/{id}', () => {
    assert.equal(extractVimeoId('https://vimeo.com/123456789'), '123456789')
  })

  it('reconnaît player.vimeo.com/video/{id}', () => {
    assert.equal(extractVimeoId('https://player.vimeo.com/video/987654321'), '987654321')
  })

  it('renvoie null sur URL non Vimeo ou ID trop court', () => {
    assert.equal(extractVimeoId('https://vimeo.com/abc'), null)
    assert.equal(extractVimeoId('https://example.com/123456'), null)
  })
})

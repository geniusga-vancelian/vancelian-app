import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { compileMjml } from '@/lib/ai-email/compileMjml'
import { buildMjmlV2 } from '@/lib/ai-email/buildMjmlV2'
import type { EmailSpec } from '@/components/ai-email/types'

const MIN_SPEC: EmailSpec = {
  subject: 'Hello world',
  preheader: 'Just a test',
  locale: 'en',
  blocks: [
    { type: 'hero', title: 'Welcome', subtitle: 'A great test', cta_label: 'Go', cta_url: 'https://example.com' },
    { type: 'text', heading: 'Body', body: 'Line 1\nLine 2 with <script>x</script>' },
    { type: 'bullets', heading: 'Bullets', items: ['One', 'Two & co', 'Three'] },
    { type: 'divider' },
    { type: 'spacer', variant: 'lg' },
    { type: 'image', image_url: 'https://example.com/img.png', alt_text: 'alt', caption: 'caption' },
    { type: 'feature_cards', heading: 'Cards', items: [{ title: 'A', body: 'a' }, { title: 'B', body: 'b' }] },
    { type: 'cta', label: 'Click', url: 'https://example.com', hint: 'hint' },
    { type: 'social_icons', links: { linkedin: 'https://l.in/x' }, size: 'sm' },
    { type: 'footer', company_name: 'Arquantix', address: '1 rue', unsubscribe_url_placeholder: '{{unsubscribe_url}}' },
  ],
}

describe('compileMjml — migration in-process', () => {
  it('compile un MJML valide vers du HTML sans spawn npx', async () => {
    const mjml = `<mjml><mj-body><mj-section><mj-column><mj-text>Hi</mj-text></mj-column></mj-section></mj-body></mjml>`
    const r = await compileMjml(mjml)
    assert.equal(r.error, null)
    assert.ok(r.html.length > 500)
    assert.ok(r.html.toLowerCase().includes('<!doctype'))
  })

  it('renvoie un fallback HTML si MJML est cassé (mode soft, pas de throw)', async () => {
    const broken = '<mjml><mj-body><mj-foobar /></mj-body></mjml>'
    const r = await compileMjml(broken)
    /**
     * En mode soft, MJML n’échoue pas dur — il warn et tente de produire
     * du HTML. On vérifie juste que la fonction renvoie une string non vide.
     */
    assert.ok(r.html.length > 0)
  })
})

describe('buildMjmlV2 — couverture complète des blocs', () => {
  it('produit du MJML pour les 11 types de blocs et reste compilable', async () => {
    const mjml = buildMjmlV2(MIN_SPEC)
    assert.ok(mjml.includes('<mjml>'))
    assert.ok(mjml.includes('</mjml>'))
    // tous les blocs apparaissent
    assert.ok(mjml.includes('Welcome'), 'hero title présent')
    assert.ok(mjml.includes('Body'), 'text heading présent')
    assert.ok(mjml.includes('Bullets'), 'bullets heading présent')
    assert.ok(mjml.includes('mj-divider'), 'divider rendu')
    assert.ok(mjml.includes('mj-spacer'), 'spacer rendu')
    assert.ok(mjml.includes('caption'), 'image caption rendue')
    assert.ok(mjml.includes('Cards'), 'feature_cards heading présent')
    assert.ok(mjml.includes('Click'), 'cta label présent')
    assert.ok(mjml.includes('LinkedIn'), 'social_icons rendus')
    assert.ok(mjml.includes('Arquantix'), 'footer company présent')

    // Le MJML doit compiler proprement.
    const r = await compileMjml(mjml)
    assert.equal(r.error, null, `compilation MJML doit réussir : ${r.error}`)
    assert.ok(r.html.length > 1000)
  })

  it('XML-escape le contenu utilisateur (anti-XSS)', () => {
    const mjml = buildMjmlV2(MIN_SPEC)
    // Le bloc text body contient `<script>x</script>` — il doit être échappé.
    assert.ok(!mjml.includes('<script>'), 'le tag <script> brut ne doit pas apparaître')
    assert.ok(
      mjml.includes('&lt;script&gt;'),
      'le contenu utilisateur doit être échappé en &lt;script&gt;',
    )
  })
})

/**
 * `buildMjmlV2` — version améliorée de `buildMjml` qui :
 *
 * 1. Couvre **tous** les types de blocs déclarés dans le schéma
 *    (`hero, section_title, text, bullets, feature_cards, image, cta,
 *    divider, spacer, social_icons, footer`) — la v1 ignorait silencieusement
 *    6 d’entre eux.
 * 2. Utilise les **tokens centralisés** du DS e-mail (`emailTokens`) pour la
 *    typographie, les couleurs et les rayons.
 * 3. **XML-escape** systématiquement le contenu (incluant `body` du bloc text)
 *    pour éliminer la surface XSS de la v1.
 * 4. Émet un `mj-attributes` global aligné avec le DS (font-family, couleurs
 *    boutons, dividers).
 * 5. Reste **compatible signature** avec `buildMjml` :
 *    `buildMjmlV2(spec: EmailSpec): string`.
 *
 * **Non destructif** : la v1 (`buildMjml`) reste exportée et intacte.
 * Les appelants peuvent migrer template par template.
 */
import { EmailSpec, Block } from '@/components/ai-email/types'
import { emailTokens } from '@/lib/email/tokens'

const T = emailTokens

export function buildMjmlV2(spec: EmailSpec): string {
  const out: string[] = []
  out.push('<?xml version="1.0" encoding="UTF-8"?>')
  out.push('<mjml>')
  out.push('<mj-head>')
  out.push(`<mj-title>${escapeXml(spec.subject)}</mj-title>`)
  if (spec.preheader) out.push(`<mj-preview>${escapeXml(spec.preheader)}</mj-preview>`)
  out.push('<mj-attributes>')
  out.push(`<mj-all font-family="${escapeXml(T.fonts.body)}" />`)
  out.push(`<mj-text color="${T.colors.ink}" font-size="15px" line-height="1.6" padding="0" />`)
  out.push(
    `<mj-button background-color="${T.colors.black}" color="${T.colors.white}" border-radius="${T.layout.radius.pill}px" font-size="12px" font-weight="500" letter-spacing="0.04em" text-transform="uppercase" font-family="${escapeXml(T.fonts.eyebrow)}" inner-padding="14px 22px" padding="0" />`,
  )
  out.push(
    `<mj-divider border-color="${T.colors.borderNavy20}" border-width="1px" padding="0" />`,
  )
  out.push('</mj-attributes>')
  out.push('</mj-head>')
  out.push(
    `<mj-body background-color="${T.colors.background}" width="${T.layout.contentWidthPx}px">`,
  )
  for (const block of spec.blocks) {
    out.push(renderBlock(block))
  }
  out.push('</mj-body>')
  out.push('</mjml>')
  return out.join('')
}

function renderBlock(block: Block): string {
  switch (block.type) {
    case 'hero':
      return renderHero(block)
    case 'section_title':
      return renderSectionTitle(block)
    case 'text':
      return renderText(block)
    case 'bullets':
      return renderBullets(block)
    case 'feature_cards':
      return renderFeatureCards(block)
    case 'image':
      return renderImage(block)
    case 'cta':
      return renderCta(block)
    case 'divider':
      return renderDivider()
    case 'spacer':
      return renderSpacer(block)
    case 'social_icons':
      return renderSocialIcons(block)
    case 'footer':
      return renderFooter(block)
    default: {
      // Couvre les éventuels nouveaux blocs ajoutés au schéma sans v3 du builder.
      const _exhaustive: never = block
      void _exhaustive
      return ''
    }
  }
}

/* ------------------------------------------------------------------ */
/* Renderers (tous escape XML strict)                                  */
/* ------------------------------------------------------------------ */

function renderHero(block: Extract<Block, { type: 'hero' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.white}" padding="0">`)
  parts.push('<mj-column>')
  if (block.image_url) {
    parts.push(
      `<mj-image src="${escapeXml(block.image_url)}" alt="" width="${T.layout.contentWidthPx}px" padding="0" />`,
    )
  }
  parts.push(
    `<mj-text align="center" padding="32px 24px 12px" font-family="${escapeXml(T.fonts.display)}" font-size="32px" font-weight="500" color="${T.colors.ink}" line-height="1.15" letter-spacing="-0.02em">${escapeXml(block.title)}</mj-text>`,
  )
  if (block.subtitle) {
    parts.push(
      `<mj-text align="center" padding="0 24px 24px" font-size="16px" color="${T.colors.textMuted}" line-height="1.55">${escapeXml(block.subtitle)}</mj-text>`,
    )
  }
  if (block.cta_label && block.cta_url) {
    parts.push(
      `<mj-button align="center" href="${escapeXml(block.cta_url)}">${escapeXml(block.cta_label)}</mj-button>`,
    )
    parts.push(`<mj-spacer height="24px" />`)
  }
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

function renderSectionTitle(block: Extract<Block, { type: 'section_title' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.white}" padding="24px 32px 0">`)
  parts.push('<mj-column>')
  parts.push(
    `<mj-text font-family="${escapeXml(T.fonts.display)}" font-size="22px" font-weight="500" color="${T.colors.ink}" line-height="1.2" letter-spacing="-0.01em" padding="0 0 8px 0">${escapeXml(block.title)}</mj-text>`,
  )
  if (block.subtitle) {
    parts.push(
      `<mj-text font-size="14px" color="${T.colors.textMuted}" line-height="1.5" padding="0">${escapeXml(block.subtitle)}</mj-text>`,
    )
  }
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

function renderText(block: Extract<Block, { type: 'text' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.white}" padding="16px 32px">`)
  parts.push('<mj-column>')
  if (block.heading) {
    parts.push(
      `<mj-text font-family="${escapeXml(T.fonts.display)}" font-size="20px" font-weight="500" color="${T.colors.ink}" line-height="1.25" padding="0 0 10px 0">${escapeXml(block.heading)}</mj-text>`,
    )
  }
  // Sécurité : on échappe le body, puis on convertit \n → <br/> APRES escape.
  const safeBody = escapeXml(block.body).replace(/\n/g, '<br />')
  parts.push(
    `<mj-text font-size="15px" color="${T.colors.ink}" line-height="1.6" padding="0">${safeBody}</mj-text>`,
  )
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

function renderBullets(block: Extract<Block, { type: 'bullets' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.white}" padding="16px 32px">`)
  parts.push('<mj-column>')
  if (block.heading) {
    parts.push(
      `<mj-text font-family="${escapeXml(T.fonts.display)}" font-size="18px" font-weight="500" color="${T.colors.ink}" line-height="1.25" padding="0 0 10px 0">${escapeXml(block.heading)}</mj-text>`,
    )
  }
  const items = block.items
    .map(
      (i) =>
        `<li style="margin: 0 0 6px 0; padding-left: 4px;">${escapeXml(i)}</li>`,
    )
    .join('')
  parts.push(
    `<mj-text font-size="15px" color="${T.colors.ink}" line-height="1.6" padding="0"><ul style="margin: 0; padding-left: 18px;">${items}</ul></mj-text>`,
  )
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

function renderFeatureCards(block: Extract<Block, { type: 'feature_cards' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.neutral100}" padding="24px 16px">`)
  if (block.heading) {
    parts.push('<mj-column>')
    parts.push(
      `<mj-text align="center" font-family="${escapeXml(T.fonts.display)}" font-size="24px" font-weight="500" color="${T.colors.ink}" line-height="1.2" padding="0 16px 18px">${escapeXml(block.heading)}</mj-text>`,
    )
    parts.push('</mj-column></mj-section>')
    parts.push(`<mj-section background-color="${T.colors.neutral100}" padding="0 16px 24px">`)
  }
  const num = block.items.length
  const width = num === 1 ? '100%' : num === 2 ? '50%' : '33.33%'
  parts.push('<mj-group>')
  for (const item of block.items) {
    parts.push(
      `<mj-column width="${width}" background-color="${T.colors.white}" border-radius="${T.layout.radius.card}px" padding="16px">`,
    )
    parts.push(
      `<mj-text font-family="${escapeXml(T.fonts.display)}" font-size="16px" font-weight="500" color="${T.colors.ink}" line-height="1.25" padding="0 0 8px 0">${escapeXml(item.title)}</mj-text>`,
    )
    parts.push(
      `<mj-text font-size="13px" color="${T.colors.textMuted}" line-height="1.55" padding="0">${escapeXml(item.body)}</mj-text>`,
    )
    parts.push('</mj-column>')
  }
  parts.push('</mj-group>')
  parts.push('</mj-section>')
  return parts.join('')
}

function renderImage(block: Extract<Block, { type: 'image' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.white}" padding="16px 32px">`)
  parts.push('<mj-column>')
  parts.push(
    `<mj-image src="${escapeXml(block.image_url)}" alt="${escapeXml(block.alt_text ?? '')}" border-radius="${T.layout.radius.card}px" padding="0" />`,
  )
  if (block.caption) {
    parts.push(
      `<mj-text align="center" font-size="12px" color="${T.colors.textMuted}" padding="8px 0 0 0">${escapeXml(block.caption)}</mj-text>`,
    )
  }
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

function renderCta(block: Extract<Block, { type: 'cta' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.white}" padding="24px 32px">`)
  parts.push('<mj-column>')
  parts.push(
    `<mj-button align="center" href="${escapeXml(block.url)}">${escapeXml(block.label)}</mj-button>`,
  )
  if (block.hint) {
    parts.push(
      `<mj-text align="center" font-size="12px" color="${T.colors.textMuted}" padding="12px 0 0 0">${escapeXml(block.hint)}</mj-text>`,
    )
  }
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

function renderDivider(): string {
  return `<mj-section background-color="${T.colors.white}" padding="0 32px"><mj-column><mj-divider padding="16px 0" /></mj-column></mj-section>`
}

function renderSpacer(block: Extract<Block, { type: 'spacer' }>): string {
  const height = block.variant === 'lg' ? '40px' : '24px'
  return `<mj-section background-color="${T.colors.white}" padding="0"><mj-column><mj-spacer height="${height}" /></mj-column></mj-section>`
}

function renderSocialIcons(block: Extract<Block, { type: 'social_icons' }>): string {
  const links = block.links ?? {}
  const networks = (
    [
      ['linkedin', 'LinkedIn'],
      ['twitter', 'X / Twitter'],
      ['facebook', 'Facebook'],
      ['instagram', 'Instagram'],
      ['youtube', 'YouTube'],
      ['telegram', 'Telegram'],
    ] as const
  ).filter(([k]) => Boolean(links[k]))

  if (networks.length === 0) return ''

  const items = networks
    .map(
      ([key, label]) =>
        `<a href="${escapeXml(links[key] as string)}" style="color:${T.colors.ink};text-decoration:none;margin:0 12px;font-size:13px;">${escapeXml(label)}</a>`,
    )
    .join('')

  return `<mj-section background-color="${T.colors.white}" padding="16px 32px"><mj-column><mj-text align="center" padding="0">${items}</mj-text></mj-column></mj-section>`
}

function renderFooter(block: Extract<Block, { type: 'footer' }>): string {
  const parts: string[] = []
  parts.push(`<mj-section background-color="${T.colors.black}" padding="32px 32px 24px">`)
  parts.push('<mj-column>')
  parts.push(
    `<mj-text align="center" font-family="${escapeXml(T.fonts.display)}" font-size="16px" font-weight="500" color="${T.colors.white}" padding="0 0 12px 0">${escapeXml(block.company_name)}</mj-text>`,
  )
  if (block.address) {
    parts.push(
      `<mj-text align="center" font-size="12px" color="${T.colors.textLight}" line-height="1.5" padding="0 0 18px 0">${escapeXml(block.address)}</mj-text>`,
    )
  }
  parts.push(
    `<mj-text align="center" font-size="11px" color="${T.colors.textSubtle}" padding="0"><a href="${escapeXml(block.unsubscribe_url_placeholder)}" style="color:${T.colors.textSubtle};text-decoration:underline;">Unsubscribe</a></mj-text>`,
  )
  parts.push('</mj-column></mj-section>')
  return parts.join('')
}

/* ------------------------------------------------------------------ */

function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

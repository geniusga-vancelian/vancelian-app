/**
 * Build MJML from EmailSpec
 * Matches backend render.py logic
 */
import { EmailSpec, Block } from '@/components/ai-email/types'

export function buildMjml(spec: EmailSpec): string {
  let mjml = '<?xml version="1.0" encoding="UTF-8"?>'
  mjml += '<mjml>'
  mjml += '<mj-head>'
  mjml += `<mj-title>${escapeXml(spec.subject)}</mj-title>`
  if (spec.preheader) {
    mjml += `<mj-preview>${escapeXml(spec.preheader)}</mj-preview>`
  }
  mjml += '<mj-attributes>'
  mjml += '<mj-all font-family="Arial, Helvetica, sans-serif" />'
  mjml += '</mj-attributes>'
  mjml += '</mj-head>'
  mjml += '<mj-body background-color="#f4f4f4" width="600px">'
  
  // Render each block
  for (const block of spec.blocks) {
    mjml += renderBlock(block)
  }
  
  mjml += '</mj-body>'
  mjml += '</mjml>'
  
  return mjml
}

function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function renderBlock(block: Block): string {
  switch (block.type) {
    case 'hero':
      return renderHero(block)
    case 'text':
      return renderText(block)
    case 'feature_cards':
      return renderFeatureCards(block)
    case 'cta':
      return renderCta(block)
    case 'footer':
      return renderFooter(block)
    default:
      return ''
  }
}

function renderHero(block: Block & { type: 'hero' }): string {
  let mjml = '<mj-section background-color="#ffffff" padding="0">'
  mjml += '<mj-column>'
  
  if (block.image_url) {
    mjml += `<mj-image src="${escapeXml(block.image_url)}" alt="" width="600px" padding="0" />`
  }
  
  mjml += '<mj-text align="center" padding="40px 20px 20px" font-size="32px" font-weight="bold" color="#1a1a1a" line-height="1.2">'
  mjml += `<p style="margin: 0;">${escapeXml(block.title)}</p>`
  mjml += '</mj-text>'
  
  if (block.subtitle) {
    mjml += '<mj-text align="center" padding="0 20px 30px" font-size="18px" color="#666666" line-height="1.5">'
    mjml += `<p style="margin: 0;">${escapeXml(block.subtitle)}</p>`
    mjml += '</mj-text>'
  }
  
  if (block.cta_label && block.cta_url) {
    mjml += `<mj-button href="${escapeXml(block.cta_url)}" background-color="#C6A47C" color="#ffffff" font-size="16px" font-weight="bold" padding="15px 40px" border-radius="4px" align="center">`
    mjml += escapeXml(block.cta_label)
    mjml += '</mj-button>'
  }
  
  mjml += '</mj-column>'
  mjml += '</mj-section>'
  return mjml
}

function renderText(block: Block & { type: 'text' }): string {
  let mjml = '<mj-section background-color="#ffffff" padding="20px 0">'
  mjml += '<mj-column>'
  
  if (block.heading) {
    mjml += '<mj-text padding="0 40px 10px" font-size="24px" font-weight="bold" color="#1a1a1a" line-height="1.3">'
    mjml += `<p style="margin: 0;">${escapeXml(block.heading)}</p>`
    mjml += '</mj-text>'
  }
  
  mjml += '<mj-text padding="0 40px" font-size="16px" color="#333333" line-height="1.6">'
  const bodyHtml = block.body.replace(/\n/g, '<br/>')
  mjml += `<p style="margin: 0;">${bodyHtml}</p>`
  mjml += '</mj-text>'
  
  mjml += '</mj-column>'
  mjml += '</mj-section>'
  return mjml
}

function renderFeatureCards(block: Block & { type: 'feature_cards' }): string {
  let mjml = '<mj-section background-color="#f8f8f8" padding="40px 0">'
  mjml += '<mj-column>'
  
  if (block.heading) {
    mjml += '<mj-text align="center" padding="0 40px 30px" font-size="28px" font-weight="bold" color="#1a1a1a" line-height="1.3">'
    mjml += `<p style="margin: 0;">${escapeXml(block.heading)}</p>`
    mjml += '</mj-text>'
  }
  
  const numItems = block.items.length
  const columnWidth = numItems === 1 ? '100%' : numItems === 2 ? '50%' : '33.33%'
  
  mjml += '<mj-group>'
  for (const item of block.items) {
    mjml += `<mj-column width="${columnWidth}">`
    mjml += '<mj-text padding="20px" font-size="18px" font-weight="bold" color="#1a1a1a" line-height="1.3">'
    mjml += `<p style="margin: 0 0 10px 0;">${escapeXml(item.title)}</p>`
    mjml += '</mj-text>'
    mjml += '<mj-text padding="0 20px 20px" font-size="14px" color="#666666" line-height="1.5">'
    mjml += `<p style="margin: 0;">${escapeXml(item.body)}</p>`
    mjml += '</mj-text>'
    mjml += '</mj-column>'
  }
  mjml += '</mj-group>'
  
  mjml += '</mj-column>'
  mjml += '</mj-section>'
  return mjml
}

function renderCta(block: Block & { type: 'cta' }): string {
  let mjml = '<mj-section background-color="#ffffff" padding="40px 0">'
  mjml += '<mj-column>'
  
  mjml += `<mj-button href="${escapeXml(block.url)}" background-color="#C6A47C" color="#ffffff" font-size="18px" font-weight="bold" padding="18px 50px" border-radius="4px" align="center">`
  mjml += escapeXml(block.label)
  mjml += '</mj-button>'
  
  if (block.hint) {
    mjml += '<mj-text align="center" padding="15px 40px 0" font-size="14px" color="#999999" line-height="1.4">'
    mjml += `<p style="margin: 0;">${escapeXml(block.hint)}</p>`
    mjml += '</mj-text>'
  }
  
  mjml += '</mj-column>'
  mjml += '</mj-section>'
  return mjml
}

function renderFooter(block: Block & { type: 'footer' }): string {
  let mjml = '<mj-section background-color="#1a1a1a" padding="40px 20px">'
  mjml += '<mj-column>'
  
  mjml += '<mj-text align="center" padding="0 0 15px" font-size="16px" font-weight="bold" color="#ffffff" line-height="1.3">'
  mjml += `<p style="margin: 0;">${escapeXml(block.company_name)}</p>`
  mjml += '</mj-text>'
  
  if (block.address) {
    mjml += '<mj-text align="center" padding="0 0 20px" font-size="14px" color="#cccccc" line-height="1.5">'
    mjml += `<p style="margin: 0;">${escapeXml(block.address)}</p>`
    mjml += '</mj-text>'
  }
  
  mjml += '<mj-text align="center" padding="0" font-size="12px" color="#999999" line-height="1.4">'
  mjml += `<p style="margin: 0;"><a href="${escapeXml(block.unsubscribe_url_placeholder)}" style="color: #999999; text-decoration: underline;">Unsubscribe</a></p>`
  mjml += '</mj-text>'
  
  mjml += '</mj-column>'
  mjml += '</mj-section>'
  return mjml
}



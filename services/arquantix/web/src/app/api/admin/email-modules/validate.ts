import { EmailSpec } from '@/components/ai-email/types'

/**
 * Validate module spec against module type constraints
 */
export async function validateModuleSpec(moduleType: string, spec: EmailSpec): Promise<void> {
  const errors: string[] = []
  
  const allowedTypes = getAllowedBlockTypes(moduleType)
  
  for (const block of spec.blocks) {
    if (!allowedTypes.includes(block.type)) {
      errors.push(
        `Block type '${block.type}' is not allowed for module type '${moduleType}'. Allowed: ${allowedTypes.join(', ')}`
      )
    }
  }
  
  if (moduleType === 'FOOTER') {
    const hasUnsubscribe = spec.blocks.some(block => {
      if (block.type === 'footer') {
        const footer = block as any
        return footer.unsubscribe_url_placeholder?.includes('{{unsubscribe_url}}')
      }
      return false
    })
    if (!hasUnsubscribe) {
      errors.push('FOOTER module must include a footer block with {{unsubscribe_url}} placeholder')
    }
  }
  
  if (moduleType === 'HEADER') {
    const hasCta = spec.blocks.some(block => block.type === 'cta')
    if (hasCta) {
      errors.push('HEADER module should not contain CTA blocks')
    }
  }
  
  if (errors.length > 0) {
    throw new Error(`Module validation failed:\n${errors.map(e => `  - ${e}`).join('\n')}`)
  }
}

export function getAllowedBlockTypes(moduleType: string): string[] {
  const allowedMap: Record<string, string[]> = {
    HEADER: ['section_title', 'text', 'divider', 'spacer'],
    FOOTER: ['social_icons', 'text', 'bullets', 'divider', 'footer'],
    LEGAL: ['text'],
    DISCLAIMER: ['text'],
    SIGNATURE: ['text', 'section_title'],
    SOCIAL: ['text', 'section_title'],
    CUSTOM: ['hero', 'section_title', 'text', 'bullets', 'feature_cards', 'image', 'cta', 'divider', 'spacer', 'social_icons', 'footer'],
  }
  
  return allowedMap[moduleType] || []
}


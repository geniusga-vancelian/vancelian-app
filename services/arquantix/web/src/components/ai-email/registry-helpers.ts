/**
 * Frontend registry helpers
 * Mirrors backend registry definitions
 */

export interface BlockDefinition {
  type: string
  variant: string
  slot: 'core' | 'optional'
  maxOccurrences?: number
  editableProps: string[]
}

const BLOCK_DEFINITIONS: Record<string, BlockDefinition> = {
  'HERO_image_top': {
    type: 'HERO',
    variant: 'image_top',
    slot: 'core',
    editableProps: ['title', 'subtitle', 'image_url', 'cta_label', 'cta_url'],
  },
  'HERO_text_only': {
    type: 'HERO',
    variant: 'text_only',
    slot: 'core',
    editableProps: ['title', 'subtitle', 'cta_label', 'cta_url'],
  },
  'SECTION_TITLE_centered': {
    type: 'SECTION_TITLE',
    variant: 'centered',
    slot: 'core',
    editableProps: ['title', 'subtitle'],
  },
  'TEXT_body': {
    type: 'TEXT',
    variant: 'body',
    slot: 'core',
    editableProps: ['heading', 'body'],
  },
  'BULLETS_default': {
    type: 'BULLETS',
    variant: 'default',
    slot: 'core',
    editableProps: ['heading', 'items'],
  },
  'FEATURE_CARDS_3up': {
    type: 'FEATURE_CARDS',
    variant: '3up',
    slot: 'core',
    editableProps: ['heading', 'items'],
  },
  'CTA_primary': {
    type: 'CTA',
    variant: 'primary',
    slot: 'core',
    editableProps: ['label', 'url', 'hint'],
  },
  'FOOTER_default': {
    type: 'FOOTER',
    variant: 'default',
    slot: 'core',
    editableProps: ['company_name', 'address', 'unsubscribe_url_placeholder'],
  },
  'IMAGE_contained': {
    type: 'IMAGE',
    variant: 'contained',
    slot: 'optional',
    maxOccurrences: 3,
    editableProps: ['image_url', 'alt_text', 'caption'],
  },
  'DIVIDER_default': {
    type: 'DIVIDER',
    variant: 'default',
    slot: 'optional',
    maxOccurrences: 2,
    editableProps: [],
  },
  'SPACER_md': {
    type: 'SPACER',
    variant: 'md',
    slot: 'optional',
    maxOccurrences: 3,
    editableProps: [],
  },
  'SPACER_lg': {
    type: 'SPACER',
    variant: 'lg',
    slot: 'optional',
    maxOccurrences: 3,
    editableProps: [],
  },
}

export function getBlockDefinition(type: string, variant: string = 'default'): BlockDefinition {
  const key = `${type.toUpperCase()}_${variant}`
  return BLOCK_DEFINITIONS[key] || {
    type: type.toUpperCase(),
    variant,
    slot: 'core',
    editableProps: [],
  }
}



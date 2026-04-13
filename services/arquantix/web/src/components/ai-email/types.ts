/**
 * TypeScript types matching backend EmailSpec
 */

export type BlockType = 'hero' | 'text' | 'feature_cards' | 'cta' | 'footer'

export interface HeroBlock {
  type: 'hero'
  variant?: 'image_top' | 'text_only'
  title: string
  subtitle?: string
  image_url?: string
  cta_label?: string
  cta_url?: string
}

export interface TextBlock {
  type: 'text'
  variant?: 'body'
  heading?: string
  body: string
}

export interface FeatureCardItem {
  title: string
  body: string
  icon?: string
}

export interface FeatureCardsBlock {
  type: 'feature_cards'
  heading?: string
  items: FeatureCardItem[]
}

export interface CtaBlock {
  type: 'cta'
  variant?: 'primary'
  label: string
  url: string
  hint?: string
}

export interface FooterBlock {
  type: 'footer'
  company_name: string
  address?: string
  unsubscribe_url_placeholder: string
}

export interface ImageBlock {
  type: 'image'
  variant?: 'contained'
  image_url: string
  alt_text?: string
  caption?: string
}

export interface DividerBlock {
  type: 'divider'
  variant?: 'default'
}

export interface SpacerBlock {
  type: 'spacer'
  variant?: 'md' | 'lg'
}

export interface SectionTitleBlock {
  type: 'section_title'
  variant?: 'centered'
  title: string
  subtitle?: string
}

export interface BulletsBlock {
  type: 'bullets'
  variant?: 'default'
  heading?: string
  items: string[]
}

export interface SocialIconsBlock {
  type: 'social_icons'
  variant?: 'default'
  links: {
    twitter?: string
    facebook?: string
    youtube?: string
    instagram?: string
    linkedin?: string
    telegram?: string
  }
  size?: 'sm' | 'md'
}

export type Block = HeroBlock | TextBlock | FeatureCardsBlock | CtaBlock | FooterBlock | ImageBlock | DividerBlock | SpacerBlock | SectionTitleBlock | BulletsBlock | SocialIconsBlock

export interface EmailSpec {
  subject: string
  preheader?: string
  locale: string
  theme?: string
  blocks: Block[]
}

export interface BlockDefinition {
  type: string
  variant: string
  slot: 'core' | 'optional'
  maxOccurrences?: number
  editableProps: string[]
}

export interface ComposeEmailRequest {
  prompt: string
  locale?: string
  previous_spec?: EmailSpec
  templateId?: string
  templateSource?: 'hardcoded' | 'db'
  lockStructure?: boolean
}

export interface ComposeEmailResponse {
  assistant_text: string
  spec: EmailSpec
  mjml: string
  html: string
  warnings?: string[]
  templateId?: string
  locked?: boolean
}

export interface EmailTemplate {
  id: string
  name: string
  description: string
  locked: boolean
  source?: 'hardcoded' | 'db'
}

export interface TranscribeAudioResponse {
  transcript: string
}


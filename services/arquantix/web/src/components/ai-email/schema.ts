/**
 * Zod schema for EmailSpec validation
 * Matches backend Pydantic schemas
 */
import { z } from 'zod'

export const HeroBlockSchema = z.object({
  type: z.literal('hero'),
  variant: z.string().optional(),
  title: z.string().min(1).max(200),
  subtitle: z.string().max(300).optional(),
  image_url: z.string().optional(), // Allow any string, not just valid URLs (for placeholders)
  cta_label: z.string().max(50).optional(),
  cta_url: z.string().optional(), // Allow any string, not just valid URLs (for placeholders)
})

export const TextBlockSchema = z.object({
  type: z.literal('text'),
  variant: z.string().optional(),
  heading: z.string().max(200).optional(),
  body: z.string().min(1).max(2000),
})

export const FeatureCardItemSchema = z.object({
  title: z.string().min(1).max(100),
  body: z.string().min(1).max(300),
  icon: z.string().optional(),
})

export const FeatureCardsBlockSchema = z.object({
  type: z.literal('feature_cards'),
  variant: z.string().optional(),
  heading: z.string().max(200).optional(),
  items: z.array(FeatureCardItemSchema).min(1).max(3),
})

export const CtaBlockSchema = z.object({
  type: z.literal('cta'),
  variant: z.string().optional(),
  label: z.string().min(1).max(50),
  url: z.string().min(1), // Allow any string, not just valid URLs (for placeholders)
  hint: z.string().max(200).optional(),
})

export const ImageBlockSchema = z.object({
  type: z.literal('image'),
  variant: z.string().optional(),
  image_url: z.string(),
  alt_text: z.string().optional(),
  caption: z.string().optional(),
})

export const DividerBlockSchema = z.object({
  type: z.literal('divider'),
  variant: z.string().optional(),
})

export const SpacerBlockSchema = z.object({
  type: z.literal('spacer'),
  variant: z.enum(['md', 'lg']).optional(),
})

export const SectionTitleBlockSchema = z.object({
  type: z.literal('section_title'),
  variant: z.string().optional(),
  title: z.string().min(1).max(200),
  subtitle: z.string().max(300).optional(),
})

export const BulletsBlockSchema = z.object({
  type: z.literal('bullets'),
  variant: z.string().optional(),
  heading: z.string().max(200).optional(),
  items: z.array(z.string()).min(1),
})

export const SocialIconsBlockSchema = z.object({
  type: z.literal('social_icons'),
  variant: z.string().optional(),
  links: z.object({
    twitter: z.string().optional(),
    facebook: z.string().optional(),
    youtube: z.string().optional(),
    instagram: z.string().optional(),
    linkedin: z.string().optional(),
    telegram: z.string().optional(),
  }).optional().default({}),
  size: z.enum(['sm', 'md']).optional().default('sm'),
})

export const FooterBlockSchema = z.object({
  type: z.literal('footer'),
  variant: z.string().optional(),
  company_name: z.string().min(1).max(100),
  address: z.string().max(500).optional(),
  unsubscribe_url_placeholder: z.string().regex(/\{\{unsubscribe_url\}\}/),
})

export const BlockSchema = z.discriminatedUnion('type', [
  HeroBlockSchema,
  SectionTitleBlockSchema,
  TextBlockSchema,
  BulletsBlockSchema,
  FeatureCardsBlockSchema,
  ImageBlockSchema,
  CtaBlockSchema,
  DividerBlockSchema,
  SpacerBlockSchema,
  SocialIconsBlockSchema,
  FooterBlockSchema,
])

export const EmailSpecSchema = z.object({
  subject: z.string().min(1).max(200),
  preheader: z.string().max(150).optional().nullable(),
  locale: z.string().regex(/^[a-z]{2}$/).default('en'),
  theme: z.string().optional(),
  blocks: z.array(BlockSchema).min(2).max(6).refine(
    (blocks) => {
      // Max 1 hero
      const heroCount = blocks.filter(b => b.type === 'hero').length
      if (heroCount > 1) return false
      
      // Footer must be last
      if (blocks.length === 0 || blocks[blocks.length - 1].type !== 'footer') return false
      
      return true
    },
    { message: 'Invalid blocks: max 1 hero, footer must be last' }
  ),
})


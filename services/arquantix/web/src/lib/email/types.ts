import { z } from 'zod'

/**
 * Catalogue des templates MJML disponibles. Chaque entrée doit avoir :
 * - un fichier `emails/mjml/templates/<id>.mjml`
 * - un schéma Zod (variables typées)
 * - une fixture `emails/fixtures/<id>.json` pour la preview / les snapshots
 */
export const EMAIL_TEMPLATE_IDS = [
  'newsletter-quarterly',
  'otp-login',
  'transaction-confirmation',
  'welcome',
] as const

export type EmailTemplateId = (typeof EMAIL_TEMPLATE_IDS)[number]

export const SUPPORTED_EMAIL_LOCALES = ['fr', 'en'] as const
export type EmailLocale = (typeof SUPPORTED_EMAIL_LOCALES)[number]

const url = z.string().url()

/* ------------------------------------------------------------------ */
/* Briques communes                                                    */
/* ------------------------------------------------------------------ */

const ctaSchema = z.object({
  label: z.string().min(1).max(40),
  href: url,
  /** Bouton inversé (utile en bloc sombre) */
  dark: z.boolean().optional(),
  align: z.enum(['left', 'center', 'right']).optional(),
})

const secondaryCtaSchema = z.object({
  label: z.string().min(1).max(40),
  href: url,
  onDark: z.boolean().optional(),
  align: z.enum(['left', 'center', 'right']).optional(),
})

const socialSchema = z.object({
  label: z.string().min(1).max(40),
  href: url,
})

const footerSchema = z.object({
  tagline: z.string().max(220).optional(),
  social: z.array(socialSchema).max(8).optional().default([]),
  unsubscribeUrl: url,
  unsubscribeLabel: z.string().max(30).default('Unsubscribe'),
  preferencesUrl: url.optional(),
  preferencesLabel: z.string().max(30).default('Preferences'),
  copyright: z.string().max(140),
})

/* ------------------------------------------------------------------ */
/* Newsletter trimestrielle                                            */
/* ------------------------------------------------------------------ */

export const newsletterQuarterlyVarsSchema = z.object({
  locale: z.enum(SUPPORTED_EMAIL_LOCALES),
  preheader: z.string().max(140),
  assetOrigin: url,
  hero: z.object({
    eyebrow: z.string().max(40),
    title: z.string().max(120),
    kicker: z.string().max(80).optional(),
    imageUrl: url,
    cta: ctaSchema.optional(),
  }),
  intro: z.object({
    eyebrow: z.string().max(40).optional(),
    heading: z.string().max(120),
    paragraphs: z.array(z.string().max(700)).min(1).max(5),
    cta: ctaSchema.optional(),
  }),
  highlightsTwo: z
    .object({
      columns: z
        .array(
          z.object({
            eyebrow: z.string().max(40),
            title: z.string().max(80),
            body: z.string().max(280),
            cta: secondaryCtaSchema.optional(),
          }),
        )
        .length(2),
    })
    .optional(),
  darkBlock: z
    .object({
      dark: z.literal(true).default(true),
      eyebrow: z.string().max(40),
      title: z.string().max(80),
      body: z.string().max(280),
      cta: ctaSchema.extend({ dark: z.literal(true).default(true) }),
    })
    .optional(),
  signature: z.object({
    closing: z.string().max(40),
    name: z.string().max(60),
    role: z.string().max(60).optional(),
  }),
  footer: footerSchema,
})

export type NewsletterQuarterlyVars = z.infer<typeof newsletterQuarterlyVarsSchema>

/* ------------------------------------------------------------------ */
/* OTP login                                                           */
/* ------------------------------------------------------------------ */

export const otpLoginVarsSchema = z.object({
  locale: z.enum(SUPPORTED_EMAIL_LOCALES),
  preheader: z.string().max(140),
  assetOrigin: url,
  title: z.string().max(120),
  intro: z.string().max(280),
  otp: z.object({
    label: z.string().max(40).optional(),
    code: z.string().regex(/^[0-9]{4,8}$/, 'OTP doit être 4 à 8 chiffres'),
    expiryText: z.string().max(120).optional(),
  }),
  metadata: z
    .object({
      title: z.string().max(40).optional(),
      rows: z
        .array(z.object({ label: z.string().max(60), value: z.string().max(120) }))
        .min(1)
        .max(8),
    })
    .optional(),
  warning: z
    .object({
      title: z.string().max(60).optional(),
      body: z.string().max(280),
      variant: z
        .object({
          warning: z.boolean().optional(),
          danger: z.boolean().optional(),
          info: z.boolean().optional(),
          success: z.boolean().optional(),
        })
        .default({ warning: true }),
    })
    .optional(),
  legal: z.object({ body: z.string().max(700) }).optional(),
  footer: footerSchema,
})

export type OtpLoginVars = z.infer<typeof otpLoginVarsSchema>

/* ------------------------------------------------------------------ */
/* Transaction confirmation                                            */
/* ------------------------------------------------------------------ */

export const transactionConfirmationVarsSchema = z.object({
  locale: z.enum(SUPPORTED_EMAIL_LOCALES),
  preheader: z.string().max(140),
  assetOrigin: url,
  eyebrow: z.string().max(40),
  title: z.string().max(120),
  intro: z.string().max(280),
  /** Référence interne — utilisée pour construire le sujet via le registry. */
  reference: z.string().max(40),
  summary: z.object({
    title: z.string().max(40).optional(),
    rows: z
      .array(z.object({ label: z.string().max(60), value: z.string().max(120) }))
      .min(2)
      .max(10),
  }),
  cta: z.object({
    eyebrow: z.string().max(40).optional(),
    title: z.string().max(80),
    body: z.string().max(280),
    dark: z.boolean().optional(),
    cta: ctaSchema,
  }),
  legal: z.object({ body: z.string().max(700) }).optional(),
  footer: footerSchema,
})

export type TransactionConfirmationVars = z.infer<typeof transactionConfirmationVarsSchema>

/* ------------------------------------------------------------------ */
/* Welcome                                                             */
/* ------------------------------------------------------------------ */

export const welcomeVarsSchema = z.object({
  locale: z.enum(SUPPORTED_EMAIL_LOCALES),
  preheader: z.string().max(140),
  assetOrigin: url,
  /** Prénom utilisé dans le sujet via le registry. */
  recipientName: z.string().max(80),
  hero: z.object({
    eyebrow: z.string().max(40),
    title: z.string().max(120),
    kicker: z.string().max(80).optional(),
    imageUrl: url,
    cta: ctaSchema.optional(),
  }),
  greetingTitle: z.string().max(120),
  greetingBody: z.string().max(700),
  stepsTitle: z.string().max(40),
  steps: z
    .array(
      z.object({
        index: z.union([z.string(), z.number()]),
        title: z.string().max(60),
        body: z.string().max(280),
      }),
    )
    .min(1)
    .max(5),
  cta: z.object({
    eyebrow: z.string().max(40).optional(),
    title: z.string().max(80),
    body: z.string().max(280),
    dark: z.boolean().optional(),
    cta: ctaSchema,
  }),
  footer: footerSchema,
})

export type WelcomeVars = z.infer<typeof welcomeVarsSchema>

/* ------------------------------------------------------------------ */

export interface RenderedEmail {
  /** Subject prêt-à-envoyer (déjà localisé via les `vars`). */
  subject: string
  /** HTML inline-styled, prêt-à-envoyer. */
  html: string
  /** Variante texte (fallback clients sans HTML). */
  text: string
  /** Locale effectivement utilisée. */
  locale: EmailLocale
  /** Identifiant du template. */
  templateId: EmailTemplateId
}

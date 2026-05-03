import { z } from 'zod'
import type {
  EmailLocale,
  EmailTemplateId,
  NewsletterQuarterlyVars,
  OtpLoginVars,
  TransactionConfirmationVars,
  WelcomeVars,
} from './types'
import {
  newsletterQuarterlyVarsSchema,
  otpLoginVarsSchema,
  transactionConfirmationVarsSchema,
  welcomeVarsSchema,
} from './types'

/**
 * Définition d’un template MJML.
 *
 * - `mjmlPath` : relatif à `emails/mjml/`
 * - `subject` : fonction (vars, locale) → sujet localisé. Sépare la copy
 *   localisée du fichier MJML pour rester contrôlable côté code.
 * - `varsSchema` : schéma Zod strict qui contraint les valeurs acceptées,
 *   notamment celles produites par l’IA chat.
 */
export interface EmailTemplateDefinition<TVars> {
  id: EmailTemplateId
  mjmlPath: string
  varsSchema: z.ZodType<TVars>
  subject: (vars: TVars, locale: EmailLocale) => string
  /** Description courte (UI admin). */
  description: string
}

/* ------------------------------------------------------------------ */
/* Helpers de localisation des sujets                                  */
/* ------------------------------------------------------------------ */

const subjectsNewsletter = {
  fr: () => 'La lettre trimestrielle Arquantix',
  en: () => 'The Arquantix Quarterly Letter',
} as const

const subjectsOtp = {
  fr: (code: string) => `Votre code de connexion : ${code}`,
  en: (code: string) => `Your login code: ${code}`,
} as const

const subjectsTransaction = {
  fr: (ref: string) => `Confirmation de votre opération · ${ref}`,
  en: (ref: string) => `Confirmation of your operation · ${ref}`,
} as const

const subjectsWelcome = {
  fr: (name: string) => `Bienvenue chez Arquantix, ${name}`,
  en: (name: string) => `Welcome to Arquantix, ${name}`,
} as const

const localeFallback = (locale: EmailLocale): EmailLocale => locale

/* ------------------------------------------------------------------ */
/* Registry                                                            */
/* ------------------------------------------------------------------ */

export const EMAIL_TEMPLATES: {
  'newsletter-quarterly': EmailTemplateDefinition<NewsletterQuarterlyVars>
  'otp-login': EmailTemplateDefinition<OtpLoginVars>
  'transaction-confirmation': EmailTemplateDefinition<TransactionConfirmationVars>
  welcome: EmailTemplateDefinition<WelcomeVars>
} = {
  'newsletter-quarterly': {
    id: 'newsletter-quarterly',
    mjmlPath: 'templates/newsletter-quarterly.mjml',
    varsSchema: newsletterQuarterlyVarsSchema,
    subject: (_vars, locale) => subjectsNewsletter[localeFallback(locale)](),
    description: 'Lettre éditoriale trimestrielle (hero L1 + cards + dark CTA).',
  },
  'otp-login': {
    id: 'otp-login',
    mjmlPath: 'templates/otp-login.mjml',
    varsSchema: otpLoginVarsSchema,
    subject: (vars, locale) => subjectsOtp[localeFallback(locale)](vars.otp.code),
    description: 'Code OTP de connexion (transactionnel critique).',
  },
  'transaction-confirmation': {
    id: 'transaction-confirmation',
    mjmlPath: 'templates/transaction-confirmation.mjml',
    varsSchema: transactionConfirmationVarsSchema,
    subject: (vars, locale) =>
      subjectsTransaction[localeFallback(locale)](vars.reference),
    description: 'Confirmation d’une opération (souscription, retrait, virement).',
  },
  welcome: {
    id: 'welcome',
    mjmlPath: 'templates/welcome.mjml',
    varsSchema: welcomeVarsSchema,
    subject: (vars, locale) => subjectsWelcome[localeFallback(locale)](vars.recipientName),
    description: 'Email de bienvenue après inscription validée.',
  },
}

export function getEmailTemplate<T extends EmailTemplateId>(
  id: T,
): (typeof EMAIL_TEMPLATES)[T] {
  return EMAIL_TEMPLATES[id]
}

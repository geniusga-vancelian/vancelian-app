import { z } from 'zod'

export const portalAuthShellSchema = z.object({
  backToWebsiteLabel: z.string().optional(),
  backToWebsiteHref: z.string().optional(),
})

export const portalAuthLoginSchema = z.object({
  title: z.string().optional(),
  body: z.string().optional(),
  emailLabel: z.string().optional(),
  submitLabel: z.string().optional(),
  helperText: z.string().optional(),
  switchLabel: z.string().optional(),
  orSeparator: z.string().optional(),
  ssoGoogleLabel: z.string().optional(),
  ssoAppleLabel: z.string().optional(),
  ssoGoogleIconSrc: z.string().optional(),
  ssoAppleIconSrc: z.string().optional(),
})

export const portalAuthSignupSchema = z.object({
  title: z.string().optional(),
  body: z.string().optional(),
  submitLabel: z.string().optional(),
  helperText: z.string().optional(),
  switchLabel: z.string().optional(),
})

export const portalAuthVerifySchema = z.object({
  loginTitle: z.string().optional(),
  signupTitle: z.string().optional(),
  /** Placeholder `{email}` */
  bodySent: z.string().optional(),
  bodyPending: z.string().optional(),
  /** Placeholder `{seconds}` */
  resendCountdown: z.string().optional(),
  resendLabel: z.string().optional(),
  wrongEmailHelper: z.string().optional(),
  backToLoginLabel: z.string().optional(),
  backToSignupLabel: z.string().optional(),
})

export const portalAuthLegalSchema = z.object({
  footnotePrefix: z.string().optional(),
  footnoteConjunction: z.string().optional(),
  termsLabel: z.string().optional(),
  termsHref: z.string().optional(),
  privacyLabel: z.string().optional(),
  privacyHref: z.string().optional(),
})

export const portalAuthLocaleBlockSchema = z.object({
  shell: portalAuthShellSchema.optional(),
  login: portalAuthLoginSchema.optional(),
  signup: portalAuthSignupSchema.optional(),
  verify: portalAuthVerifySchema.optional(),
  legal: portalAuthLegalSchema.optional(),
})

export const portalAuthJsonV2Schema = z.object({
  version: z.literal(2),
  defaultLocale: z.enum(['fr', 'en', 'it']),
  /** Durée entre deux renvois de code OTP (secondes) — global, hors locale. */
  resendSeconds: z.number().int().min(15).max(300).optional(),
  /** Affiche le séparateur OR + boutons Google/Apple (login et signup). */
  ssoEnabled: z.boolean().optional(),
  locales: z.object({
    fr: portalAuthLocaleBlockSchema.optional(),
    en: portalAuthLocaleBlockSchema.optional(),
    it: portalAuthLocaleBlockSchema.optional(),
  }),
})

export type PortalAuthLocaleBlock = z.infer<typeof portalAuthLocaleBlockSchema>
export type PortalAuthJsonV2 = z.infer<typeof portalAuthJsonV2Schema>

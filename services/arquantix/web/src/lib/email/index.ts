/**
 * Façade publique du **système email MJML** (rendu, validation, envoi).
 *
 * Ce module est volontairement **séparé** de `src/lib/ai-email/` (pipeline IA
 * historique : `composeEmail` + `buildMjml` à base de string concat) pour
 * permettre une migration progressive sans rupture.
 *
 * Voir `docs/EMAIL_MJML.md` pour l’architecture complète.
 */
export { renderTemplate, EMAIL_TEMPLATE_IDS_LIST } from './renderTemplate'
export { EMAIL_TEMPLATES, getEmailTemplate } from './templateRegistry'
export type { EmailTemplateDefinition } from './templateRegistry'
export {
  renderMjmlFile,
  renderMjmlString,
  MjmlValidationError,
  MJML_PATHS,
} from './mjmlRender'
export type { MjmlRenderOptions, MjmlRenderResult } from './mjmlRender'
export {
  interpolate,
  prepareVarsForMjml,
  validateVars,
  EmailTemplateVarsError,
} from './interpolate'
export { loadEmailPartials, resetEmailPartialsCache } from './loadPartials'
export {
  EMAIL_TEMPLATE_IDS,
  SUPPORTED_EMAIL_LOCALES,
  newsletterQuarterlyVarsSchema,
  otpLoginVarsSchema,
  transactionConfirmationVarsSchema,
  welcomeVarsSchema,
} from './types'
export type {
  EmailTemplateId,
  EmailLocale,
  RenderedEmail,
  NewsletterQuarterlyVars,
  OtpLoginVars,
  TransactionConfirmationVars,
  WelcomeVars,
} from './types'
export {
  getEmailSendAdapter,
  noopSendAdapter,
  consoleSendAdapter,
} from './sendAdapter'
export type {
  EmailSendAdapter,
  OutboundEmail,
  OutboundEmailRecipient,
  SendResult,
} from './sendAdapter'

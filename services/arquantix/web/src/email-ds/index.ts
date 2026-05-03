/**
 * **Design system HTML e-mail Arquantix** — ne pas confondre avec le DS site (`figmaDs*`, `components/design-system`).
 *
 * - Jetons : `emailDsColors`, `emailDsFonts`, `emailDsLayout`, etc. (`tokens.ts`)
 * - Assets statiques : `public/email-ds/*` — utiliser `emailDsAssetUrl(file, origin)` pour les envois réels
 * - Composants : styles inline uniquement, compatibles rendu HTML e-mail
 */

export {
  emailDsColors,
  emailDsFonts,
  emailDsType,
  emailDsLayout,
  emailDsRadius,
  emailDsGradient,
} from '@/email-ds/tokens'

export { emailDsAssetUrl } from '@/email-ds/resolveAssetUrl'

export { EmailShell } from '@/email-ds/components/EmailShell'
export type { EmailShellProps } from '@/email-ds/components/EmailShell'

export { EmailWordmark } from '@/email-ds/components/EmailWordmark'
export type { EmailWordmarkProps } from '@/email-ds/components/EmailWordmark'

export { EmailHeader } from '@/email-ds/components/EmailHeader'
export type { EmailHeaderProps, EmailNavLink } from '@/email-ds/components/EmailHeader'

export { EmailFooter } from '@/email-ds/components/EmailFooter'
export type { EmailFooterProps, EmailFooterSocial } from '@/email-ds/components/EmailFooter'

export { EmailEyebrow } from '@/email-ds/components/EmailEyebrow'
export type { EmailEyebrowProps } from '@/email-ds/components/EmailEyebrow'

export { EmailSectionRule } from '@/email-ds/components/EmailSectionRule'

export { EmailPrimaryButton, EmailSecondaryButton } from '@/email-ds/components/EmailButtons'
export type { EmailPrimaryButtonProps, EmailSecondaryButtonProps } from '@/email-ds/components/EmailButtons'

export { NewsletterExample } from '@/email-ds/templates/NewsletterExample'
export type { NewsletterExampleProps } from '@/email-ds/templates/NewsletterExample'

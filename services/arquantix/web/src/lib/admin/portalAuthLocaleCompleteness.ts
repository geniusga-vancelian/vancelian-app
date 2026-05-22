import type { PortalAuthLocaleBlock } from '@/lib/cms/portalAuthSchema'
import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'

function t(s: string | undefined): string {
  return (s ?? '').trim()
}

export function levelForPortalAuthBlock(block: PortalAuthLocaleBlock): LocaleCompletenessLevel {
  const loginOk =
    t(block.login?.title) &&
    t(block.login?.body) &&
    t(block.login?.submitLabel) &&
    t(block.login?.emailLabel)
  const signupOk =
    t(block.signup?.title) && t(block.signup?.body) && t(block.signup?.submitLabel)
  const verifyOk =
    t(block.verify?.loginTitle) &&
    t(block.verify?.signupTitle) &&
    t(block.verify?.bodySent) &&
    t(block.verify?.resendLabel)
  const legalOk =
    t(block.legal?.footnotePrefix) &&
    t(block.legal?.termsLabel) &&
    t(block.legal?.termsHref) &&
    t(block.legal?.privacyLabel) &&
    t(block.legal?.privacyHref)

  const hasAny =
    loginOk || signupOk || verifyOk || legalOk || t(block.shell?.backToWebsiteLabel)

  if (!hasAny) return 'missing'
  if (loginOk && signupOk && verifyOk && legalOk) return 'complete'
  return 'partial'
}

export function computePortalAuthLocalesCompleteness(
  locales: Record<Locale, PortalAuthLocaleBlock>,
): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    out[loc] = levelForPortalAuthBlock(locales[loc] ?? {})
  }
  return out
}

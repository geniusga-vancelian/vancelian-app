import { defaultLocale, type Locale } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import {
  parsePortalAuthStorage,
  resolvePortalAuthBlockForLocale,
} from '@/lib/cms/portalAuthStorage'

/** Runtime portail auth : EN uniquement pour l’instant (traductions préparables en admin). */
export const PORTAL_AUTH_RUNTIME_LOCALE: Locale = 'en'

export type PortalAuthContent = {
  shell: {
    backToWebsiteLabel: string
    backToWebsiteHref: string
  }
  login: {
    title: string
    body: string
    emailLabel: string
    submitLabel: string
    helperText: string
    switchLabel: string
    orSeparator: string
    ssoGoogleLabel: string
    ssoAppleLabel: string
    ssoGoogleIconSrc: string
    ssoAppleIconSrc: string
  }
  signup: {
    title: string
    body: string
    submitLabel: string
    helperText: string
    switchLabel: string
  }
  verify: {
    loginTitle: string
    signupTitle: string
    bodySent: string
    bodyPending: string
    resendCountdown: string
    resendLabel: string
    wrongEmailHelper: string
    backToLoginLabel: string
    backToSignupLabel: string
  }
  legal: {
    footnotePrefix: string
    footnoteConjunction: string
    termsLabel: string
    termsHref: string
    privacyLabel: string
    privacyHref: string
  }
  resendSeconds: number
  ssoEnabled: boolean
}

export function getDefaultPortalAuthContent(): PortalAuthContent {
  return {
    shell: {
      backToWebsiteLabel: 'Back to the website',
      backToWebsiteHref: `/${defaultLocale}`,
    },
    login: {
      title: 'Sign in to your account',
      body: "Enter your email and we'll send a verification code to your inbox.",
      emailLabel: 'Email address',
      submitLabel: 'Sign in with email',
      helperText: 'New to Vancelian?',
      switchLabel: 'Create an account',
      orSeparator: 'or',
      ssoGoogleLabel: 'Continue with Google',
      ssoAppleLabel: 'Continue with Apple',
      ssoGoogleIconSrc: '/brand/vancelian/sso-google.svg',
      ssoAppleIconSrc: '/brand/vancelian/sso-apple.svg',
    },
    signup: {
      title: 'Create your account',
      body: "Get early access to off-grid wealth building. We'll send a magic link to your inbox.",
      submitLabel: 'Sign up with email',
      helperText: 'Already have an account?',
      switchLabel: 'Log in',
    },
    verify: {
      loginTitle: 'Email sign-in code',
      signupTitle: 'Email sign-up code',
      bodySent: 'Code sent to {email}',
      bodyPending: 'Enter the six-digit code we sent to your inbox, or resend a new code below.',
      resendCountdown: 'Resend code in {seconds}s',
      resendLabel: 'Resend code',
      wrongEmailHelper: 'Wrong email?',
      backToLoginLabel: 'Back to sign in',
      backToSignupLabel: 'Back to sign up',
    },
    legal: {
      footnotePrefix: 'By requesting access, you agree to our',
      footnoteConjunction: 'and',
      termsLabel: 'Terms',
      termsHref: '/en/terms',
      privacyLabel: 'Privacy Policy',
      privacyHref: '/en/privacy-policy',
    },
    resendSeconds: 45,
    ssoEnabled: false,
  }
}

function mergePortalAuthContent(
  block: ReturnType<typeof resolvePortalAuthBlockForLocale>,
  resendSeconds: number,
  ssoEnabled: boolean,
): PortalAuthContent {
  const defaults = getDefaultPortalAuthContent()
  return {
    shell: {
      backToWebsiteLabel: block.shell?.backToWebsiteLabel?.trim() || defaults.shell.backToWebsiteLabel,
      backToWebsiteHref: block.shell?.backToWebsiteHref?.trim() || defaults.shell.backToWebsiteHref,
    },
    login: {
      title: block.login?.title?.trim() || defaults.login.title,
      body: block.login?.body?.trim() || defaults.login.body,
      emailLabel: block.login?.emailLabel?.trim() || defaults.login.emailLabel,
      submitLabel: block.login?.submitLabel?.trim() || defaults.login.submitLabel,
      helperText: block.login?.helperText?.trim() || defaults.login.helperText,
      switchLabel: block.login?.switchLabel?.trim() || defaults.login.switchLabel,
      orSeparator: block.login?.orSeparator?.trim() || defaults.login.orSeparator,
      ssoGoogleLabel: block.login?.ssoGoogleLabel?.trim() || defaults.login.ssoGoogleLabel,
      ssoAppleLabel: block.login?.ssoAppleLabel?.trim() || defaults.login.ssoAppleLabel,
      ssoGoogleIconSrc: block.login?.ssoGoogleIconSrc?.trim() || defaults.login.ssoGoogleIconSrc,
      ssoAppleIconSrc: block.login?.ssoAppleIconSrc?.trim() || defaults.login.ssoAppleIconSrc,
    },
    signup: {
      title: block.signup?.title?.trim() || defaults.signup.title,
      body: block.signup?.body?.trim() || defaults.signup.body,
      submitLabel: block.signup?.submitLabel?.trim() || defaults.signup.submitLabel,
      helperText: block.signup?.helperText?.trim() || defaults.signup.helperText,
      switchLabel: block.signup?.switchLabel?.trim() || defaults.signup.switchLabel,
    },
    verify: {
      loginTitle: block.verify?.loginTitle?.trim() || defaults.verify.loginTitle,
      signupTitle: block.verify?.signupTitle?.trim() || defaults.verify.signupTitle,
      bodySent: block.verify?.bodySent?.trim() || defaults.verify.bodySent,
      bodyPending: block.verify?.bodyPending?.trim() || defaults.verify.bodyPending,
      resendCountdown: block.verify?.resendCountdown?.trim() || defaults.verify.resendCountdown,
      resendLabel: block.verify?.resendLabel?.trim() || defaults.verify.resendLabel,
      wrongEmailHelper: block.verify?.wrongEmailHelper?.trim() || defaults.verify.wrongEmailHelper,
      backToLoginLabel: block.verify?.backToLoginLabel?.trim() || defaults.verify.backToLoginLabel,
      backToSignupLabel: block.verify?.backToSignupLabel?.trim() || defaults.verify.backToSignupLabel,
    },
    legal: {
      footnotePrefix: block.legal?.footnotePrefix?.trim() || defaults.legal.footnotePrefix,
      footnoteConjunction: block.legal?.footnoteConjunction?.trim() || defaults.legal.footnoteConjunction,
      termsLabel: block.legal?.termsLabel?.trim() || defaults.legal.termsLabel,
      termsHref: block.legal?.termsHref?.trim() || defaults.legal.termsHref,
      privacyLabel: block.legal?.privacyLabel?.trim() || defaults.legal.privacyLabel,
      privacyHref: block.legal?.privacyHref?.trim() || defaults.legal.privacyHref,
    },
    resendSeconds,
    ssoEnabled,
  }
}

export async function getPortalAuthContent(
  locale: Locale = PORTAL_AUTH_RUNTIME_LOCALE,
): Promise<PortalAuthContent> {
  try {
    const row = await prisma.globalSettings.findFirst({ select: { portalAuthJson: true } })
    const parsed = parsePortalAuthStorage(row?.portalAuthJson ?? null)
    const resendSeconds =
      parsed.kind === 'v2' && parsed.doc.resendSeconds ? parsed.doc.resendSeconds : 45
    const ssoEnabled = parsed.kind === 'v2' && parsed.doc.ssoEnabled === true
    const block = resolvePortalAuthBlockForLocale(parsed, locale)
    return mergePortalAuthContent(block, resendSeconds, ssoEnabled)
  } catch (e) {
    console.error('[getPortalAuthContent]', e)
    return getDefaultPortalAuthContent()
  }
}

/** Remplace `{key}` dans les templates CMS (ex. `{email}`, `{seconds}`). */
export function interpolatePortalAuthTemplate(
  template: string,
  vars: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = vars[key]
    return value === undefined || value === null ? '' : String(value)
  })
}

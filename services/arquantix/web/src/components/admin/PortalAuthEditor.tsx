'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LocaleCompletenessStrip } from '@/components/admin/LocaleCompletenessStrip'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { computePortalAuthLocalesCompleteness } from '@/lib/admin/portalAuthLocaleCompleteness'
import { getDefaultPortalAuthContent } from '@/lib/cms/portal-auth'
import type { PortalAuthLocaleBlock } from '@/lib/cms/portalAuthSchema'
import { supportedLocales, type Locale } from '@/config/locales'
import { cn } from '@/lib/utils'

const LOCALE_LABEL: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

type TabId = 'shell' | 'login' | 'signup' | 'verify' | 'legal' | 'settings'

const TABS: { id: TabId; label: string }[] = [
  { id: 'shell', label: 'Shell' },
  { id: 'login', label: 'Login' },
  { id: 'signup', label: 'Sign up' },
  { id: 'verify', label: 'Code OTP' },
  { id: 'legal', label: 'Mentions légales' },
  { id: 'settings', label: 'Paramètres' },
]

export type PortalAuthFormState = {
  shellBackLabel: string
  shellBackHref: string
  loginTitle: string
  loginBody: string
  loginEmailLabel: string
  loginSubmitLabel: string
  loginHelperText: string
  loginSwitchLabel: string
  loginOrSeparator: string
  loginSsoGoogleLabel: string
  loginSsoAppleLabel: string
  loginSsoGoogleIconSrc: string
  loginSsoAppleIconSrc: string
  signupTitle: string
  signupBody: string
  signupSubmitLabel: string
  signupHelperText: string
  signupSwitchLabel: string
  verifyLoginTitle: string
  verifySignupTitle: string
  verifyBodySent: string
  verifyBodyPending: string
  verifyResendCountdown: string
  verifyResendLabel: string
  verifyWrongEmailHelper: string
  verifyBackToLoginLabel: string
  verifyBackToSignupLabel: string
  legalFootnotePrefix: string
  legalFootnoteConjunction: string
  legalTermsLabel: string
  legalTermsHref: string
  legalPrivacyLabel: string
  legalPrivacyHref: string
}

function initialPortalAuthForm(): PortalAuthFormState {
  const d = getDefaultPortalAuthContent()
  return {
    shellBackLabel: d.shell.backToWebsiteLabel,
    shellBackHref: d.shell.backToWebsiteHref,
    loginTitle: d.login.title,
    loginBody: d.login.body,
    loginEmailLabel: d.login.emailLabel,
    loginSubmitLabel: d.login.submitLabel,
    loginHelperText: d.login.helperText,
    loginSwitchLabel: d.login.switchLabel,
    loginOrSeparator: d.login.orSeparator,
    loginSsoGoogleLabel: d.login.ssoGoogleLabel,
    loginSsoAppleLabel: d.login.ssoAppleLabel,
    loginSsoGoogleIconSrc: d.login.ssoGoogleIconSrc,
    loginSsoAppleIconSrc: d.login.ssoAppleIconSrc,
    signupTitle: d.signup.title,
    signupBody: d.signup.body,
    signupSubmitLabel: d.signup.submitLabel,
    signupHelperText: d.signup.helperText,
    signupSwitchLabel: d.signup.switchLabel,
    verifyLoginTitle: d.verify.loginTitle,
    verifySignupTitle: d.verify.signupTitle,
    verifyBodySent: d.verify.bodySent,
    verifyBodyPending: d.verify.bodyPending,
    verifyResendCountdown: d.verify.resendCountdown,
    verifyResendLabel: d.verify.resendLabel,
    verifyWrongEmailHelper: d.verify.wrongEmailHelper,
    verifyBackToLoginLabel: d.verify.backToLoginLabel,
    verifyBackToSignupLabel: d.verify.backToSignupLabel,
    legalFootnotePrefix: d.legal.footnotePrefix,
    legalFootnoteConjunction: d.legal.footnoteConjunction,
    legalTermsLabel: d.legal.termsLabel,
    legalTermsHref: d.legal.termsHref,
    legalPrivacyLabel: d.legal.privacyLabel,
    legalPrivacyHref: d.legal.privacyHref,
  }
}

function blockToForm(block: PortalAuthLocaleBlock): PortalAuthFormState {
  const base = initialPortalAuthForm()
  return {
    shellBackLabel: block.shell?.backToWebsiteLabel ?? base.shellBackLabel,
    shellBackHref: block.shell?.backToWebsiteHref ?? base.shellBackHref,
    loginTitle: block.login?.title ?? base.loginTitle,
    loginBody: block.login?.body ?? base.loginBody,
    loginEmailLabel: block.login?.emailLabel ?? base.loginEmailLabel,
    loginSubmitLabel: block.login?.submitLabel ?? base.loginSubmitLabel,
    loginHelperText: block.login?.helperText ?? base.loginHelperText,
    loginSwitchLabel: block.login?.switchLabel ?? base.loginSwitchLabel,
    loginOrSeparator: block.login?.orSeparator ?? base.loginOrSeparator,
    loginSsoGoogleLabel: block.login?.ssoGoogleLabel ?? base.loginSsoGoogleLabel,
    loginSsoAppleLabel: block.login?.ssoAppleLabel ?? base.loginSsoAppleLabel,
    loginSsoGoogleIconSrc: block.login?.ssoGoogleIconSrc ?? base.loginSsoGoogleIconSrc,
    loginSsoAppleIconSrc: block.login?.ssoAppleIconSrc ?? base.loginSsoAppleIconSrc,
    signupTitle: block.signup?.title ?? base.signupTitle,
    signupBody: block.signup?.body ?? base.signupBody,
    signupSubmitLabel: block.signup?.submitLabel ?? base.signupSubmitLabel,
    signupHelperText: block.signup?.helperText ?? base.signupHelperText,
    signupSwitchLabel: block.signup?.switchLabel ?? base.signupSwitchLabel,
    verifyLoginTitle: block.verify?.loginTitle ?? base.verifyLoginTitle,
    verifySignupTitle: block.verify?.signupTitle ?? base.verifySignupTitle,
    verifyBodySent: block.verify?.bodySent ?? base.verifyBodySent,
    verifyBodyPending: block.verify?.bodyPending ?? base.verifyBodyPending,
    verifyResendCountdown: block.verify?.resendCountdown ?? base.verifyResendCountdown,
    verifyResendLabel: block.verify?.resendLabel ?? base.verifyResendLabel,
    verifyWrongEmailHelper: block.verify?.wrongEmailHelper ?? base.verifyWrongEmailHelper,
    verifyBackToLoginLabel: block.verify?.backToLoginLabel ?? base.verifyBackToLoginLabel,
    verifyBackToSignupLabel: block.verify?.backToSignupLabel ?? base.verifyBackToSignupLabel,
    legalFootnotePrefix: block.legal?.footnotePrefix ?? base.legalFootnotePrefix,
    legalFootnoteConjunction: block.legal?.footnoteConjunction ?? base.legalFootnoteConjunction,
    legalTermsLabel: block.legal?.termsLabel ?? base.legalTermsLabel,
    legalTermsHref: block.legal?.termsHref ?? base.legalTermsHref,
    legalPrivacyLabel: block.legal?.privacyLabel ?? base.legalPrivacyLabel,
    legalPrivacyHref: block.legal?.privacyHref ?? base.legalPrivacyHref,
  }
}

function formToBlock(form: PortalAuthFormState): PortalAuthLocaleBlock {
  const trim = (s: string) => s.trim()
  return {
    shell: {
      backToWebsiteLabel: trim(form.shellBackLabel) || undefined,
      backToWebsiteHref: trim(form.shellBackHref) || undefined,
    },
    login: {
      title: trim(form.loginTitle) || undefined,
      body: trim(form.loginBody) || undefined,
      emailLabel: trim(form.loginEmailLabel) || undefined,
      submitLabel: trim(form.loginSubmitLabel) || undefined,
      helperText: trim(form.loginHelperText) || undefined,
      switchLabel: trim(form.loginSwitchLabel) || undefined,
      orSeparator: trim(form.loginOrSeparator) || undefined,
      ssoGoogleLabel: trim(form.loginSsoGoogleLabel) || undefined,
      ssoAppleLabel: trim(form.loginSsoAppleLabel) || undefined,
      ssoGoogleIconSrc: trim(form.loginSsoGoogleIconSrc) || undefined,
      ssoAppleIconSrc: trim(form.loginSsoAppleIconSrc) || undefined,
    },
    signup: {
      title: trim(form.signupTitle) || undefined,
      body: trim(form.signupBody) || undefined,
      submitLabel: trim(form.signupSubmitLabel) || undefined,
      helperText: trim(form.signupHelperText) || undefined,
      switchLabel: trim(form.signupSwitchLabel) || undefined,
    },
    verify: {
      loginTitle: trim(form.verifyLoginTitle) || undefined,
      signupTitle: trim(form.verifySignupTitle) || undefined,
      bodySent: trim(form.verifyBodySent) || undefined,
      bodyPending: trim(form.verifyBodyPending) || undefined,
      resendCountdown: trim(form.verifyResendCountdown) || undefined,
      resendLabel: trim(form.verifyResendLabel) || undefined,
      wrongEmailHelper: trim(form.verifyWrongEmailHelper) || undefined,
      backToLoginLabel: trim(form.verifyBackToLoginLabel) || undefined,
      backToSignupLabel: trim(form.verifyBackToSignupLabel) || undefined,
    },
    legal: {
      footnotePrefix: trim(form.legalFootnotePrefix) || undefined,
      footnoteConjunction: trim(form.legalFootnoteConjunction) || undefined,
      termsLabel: trim(form.legalTermsLabel) || undefined,
      termsHref: trim(form.legalTermsHref) || undefined,
      privacyLabel: trim(form.legalPrivacyLabel) || undefined,
      privacyHref: trim(form.legalPrivacyHref) || undefined,
    },
  }
}

function emptyLocalesMap(): Record<Locale, PortalAuthFormState> {
  return {
    fr: initialPortalAuthForm(),
    en: initialPortalAuthForm(),
    it: initialPortalAuthForm(),
  }
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-gray-900">{label}</span>
      {hint ? <p className="text-xs text-gray-500">{hint}</p> : null}
      {children}
    </label>
  )
}

const inputClass =
  'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500'

export function PortalAuthEditor() {
  const router = useRouter()
  const [activeLocale, setActiveLocale] = useState<Locale>('en')
  const [defaultLocaleState, setDefaultLocaleState] = useState<Locale>('en')
  const [resendSeconds, setResendSeconds] = useState(45)
  const [ssoEnabled, setSsoEnabled] = useState(false)
  const [localesMap, setLocalesMap] = useState<Record<Locale, PortalAuthFormState>>(emptyLocalesMap)
  const [form, setForm] = useState<PortalAuthFormState>(() => initialPortalAuthForm())
  const [activeTab, setActiveTab] = useState<TabId>('login')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const loadPayload = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/portal-auth')
      const data = await res.json()
      if (data.error === 'Unauthorized') {
        router.push('/admin/login')
        return
      }
      if (!data.locales || typeof data.locales !== 'object') {
        toastError('Réponse portail auth inattendue')
        return
      }

      const dl = (data.defaultLocale as Locale) ?? 'en'
      setDefaultLocaleState(supportedLocales.includes(dl) ? dl : 'en')
      setResendSeconds(typeof data.resendSeconds === 'number' ? data.resendSeconds : 45)
      setSsoEnabled(Boolean(data.ssoEnabled))

      const nextMap = emptyLocalesMap()
      for (const loc of supportedLocales) {
        nextMap[loc] = blockToForm((data.locales[loc] as PortalAuthLocaleBlock) ?? {})
      }
      setLocalesMap(nextMap)
      setActiveLocale('en')
      setForm(structuredClone(nextMap.en))
    } catch (e) {
      console.error(e)
      toastError('Impossible de charger le portail auth')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    void loadPayload()
  }, [loadPayload])

  const completeness = useMemo(() => {
    const blocks = Object.fromEntries(
      supportedLocales.map((loc) => [loc, formToBlock(localesMap[loc])]),
    ) as Record<Locale, PortalAuthLocaleBlock>
    return computePortalAuthLocalesCompleteness(blocks)
  }, [localesMap])

  const handleLocaleChange = (next: Locale) => {
    if (next === activeLocale) return
    setLocalesMap((prev) => {
      const merged = { ...prev, [activeLocale]: structuredClone(form) }
      setActiveLocale(next)
      setForm(structuredClone(merged[next]))
      return merged
    })
  }

  const handleCopyFromDefault = () => {
    if (defaultLocaleState === activeLocale) {
      toastError('Sélectionnez une autre langue que la langue de secours.')
      return
    }
    setForm(structuredClone(localesMap[defaultLocaleState]))
    toastSuccess(`Contenu copié depuis ${LOCALE_LABEL[defaultLocaleState]}.`)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const mergedMap = { ...localesMap, [activeLocale]: structuredClone(form) }
      const res = await fetch('/api/admin/portal-auth', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'locale',
          locale: activeLocale,
          defaultLocale: defaultLocaleState,
          resendSeconds,
          ssoEnabled,
          block: formToBlock(mergedMap[activeLocale]),
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Erreur lors de la sauvegarde')
        return
      }
      setLocalesMap(mergedMap)
      toastSuccess('Portail auth enregistré.')
    } catch (e) {
      console.error(e)
      toastError('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Chargement…</p>
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Portail Auth</h2>
        <p className="text-sm text-gray-600">
          Copy des écrans login, création de compte et code OTP. Affichage runtime en{' '}
          <strong>EN</strong> pour l’instant ; les autres langues sont préparables ici. Hero =
          section homepage CMS (inchangé).
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {supportedLocales.map((loc) => (
          <button
            key={loc}
            type="button"
            onClick={() => handleLocaleChange(loc)}
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              activeLocale === loc
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
            )}
          >
            {LOCALE_LABEL[loc]}
          </button>
        ))}
        <LocaleCompletenessStrip levels={completeness} variant="inline" />
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          Langue de secours
          <select
            value={defaultLocaleState}
            onChange={(e) => setDefaultLocaleState(e.target.value as Locale)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            {supportedLocales.map((loc) => (
              <option key={loc} value={loc}>
                {LOCALE_LABEL[loc]}
              </option>
            ))}
          </select>
        </label>
        <Button type="button" variant="outline" size="sm" onClick={handleCopyFromDefault}>
          <Copy className="mr-2 h-4 w-4" />
          Copier depuis {LOCALE_LABEL[defaultLocaleState]}
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium',
              activeTab === tab.id
                ? 'bg-indigo-100 text-indigo-900'
                : 'text-gray-600 hover:bg-gray-100',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
        {activeTab === 'shell' ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Lien retour site — libellé">
              <input
                className={inputClass}
                value={form.shellBackLabel}
                onChange={(e) => setForm((f) => ({ ...f, shellBackLabel: e.target.value }))}
              />
            </Field>
            <Field label="Lien retour site — URL" hint="Ex. /en">
              <input
                className={inputClass}
                value={form.shellBackHref}
                onChange={(e) => setForm((f) => ({ ...f, shellBackHref: e.target.value }))}
              />
            </Field>
          </div>
        ) : null}

        {activeTab === 'login' ? (
          <div className="grid gap-4">
            <Field label="Titre">
              <input
                className={inputClass}
                value={form.loginTitle}
                onChange={(e) => setForm((f) => ({ ...f, loginTitle: e.target.value }))}
              />
            </Field>
            <Field label="Introduction">
              <textarea
                className={inputClass}
                rows={3}
                value={form.loginBody}
                onChange={(e) => setForm((f) => ({ ...f, loginBody: e.target.value }))}
              />
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Label email">
                <input
                  className={inputClass}
                  value={form.loginEmailLabel}
                  onChange={(e) => setForm((f) => ({ ...f, loginEmailLabel: e.target.value }))}
                />
              </Field>
              <Field label="Bouton principal">
                <input
                  className={inputClass}
                  value={form.loginSubmitLabel}
                  onChange={(e) => setForm((f) => ({ ...f, loginSubmitLabel: e.target.value }))}
                />
              </Field>
              <Field label="Texte helper">
                <input
                  className={inputClass}
                  value={form.loginHelperText}
                  onChange={(e) => setForm((f) => ({ ...f, loginHelperText: e.target.value }))}
                />
              </Field>
              <Field label="Lien bascule (signup)">
                <input
                  className={inputClass}
                  value={form.loginSwitchLabel}
                  onChange={(e) => setForm((f) => ({ ...f, loginSwitchLabel: e.target.value }))}
                />
              </Field>
              <Field label="Séparateur OR" hint="Visible uniquement si SSO activé (Paramètres).">
                <input
                  className={inputClass}
                  value={form.loginOrSeparator}
                  onChange={(e) => setForm((f) => ({ ...f, loginOrSeparator: e.target.value }))}
                />
              </Field>
            </div>

            <section className="space-y-4 rounded-lg border border-slate-200 bg-slate-50/60 p-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Connexion SSO (Google + Apple)</h3>
                <p className="mt-1 text-xs text-gray-500">
                  Libellés et icônes utilisés lorsque l’option « Afficher Google et Apple » est activée
                  dans Paramètres.
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Bouton Google">
                  <input
                    className={inputClass}
                    value={form.loginSsoGoogleLabel}
                    onChange={(e) => setForm((f) => ({ ...f, loginSsoGoogleLabel: e.target.value }))}
                  />
                </Field>
                <Field label="Bouton Apple">
                  <input
                    className={inputClass}
                    value={form.loginSsoAppleLabel}
                    onChange={(e) => setForm((f) => ({ ...f, loginSsoAppleLabel: e.target.value }))}
                  />
                </Field>
                <Field label="Icône Google (URL)" hint="Chemin public, ex. /brand/.../sso-google.svg">
                  <input
                    className={inputClass}
                    value={form.loginSsoGoogleIconSrc}
                    onChange={(e) => setForm((f) => ({ ...f, loginSsoGoogleIconSrc: e.target.value }))}
                  />
                </Field>
                <Field label="Icône Apple (URL)">
                  <input
                    className={inputClass}
                    value={form.loginSsoAppleIconSrc}
                    onChange={(e) => setForm((f) => ({ ...f, loginSsoAppleIconSrc: e.target.value }))}
                  />
                </Field>
              </div>
            </section>
          </div>
        ) : null}

        {activeTab === 'signup' ? (
          <div className="grid gap-4">
            <Field label="Titre">
              <input
                className={inputClass}
                value={form.signupTitle}
                onChange={(e) => setForm((f) => ({ ...f, signupTitle: e.target.value }))}
              />
            </Field>
            <Field label="Introduction">
              <textarea
                className={inputClass}
                rows={3}
                value={form.signupBody}
                onChange={(e) => setForm((f) => ({ ...f, signupBody: e.target.value }))}
              />
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Bouton principal">
                <input
                  className={inputClass}
                  value={form.signupSubmitLabel}
                  onChange={(e) => setForm((f) => ({ ...f, signupSubmitLabel: e.target.value }))}
                />
              </Field>
              <Field label="Texte helper">
                <input
                  className={inputClass}
                  value={form.signupHelperText}
                  onChange={(e) => setForm((f) => ({ ...f, signupHelperText: e.target.value }))}
                />
              </Field>
              <Field label="Lien bascule (login)">
                <input
                  className={inputClass}
                  value={form.signupSwitchLabel}
                  onChange={(e) => setForm((f) => ({ ...f, signupSwitchLabel: e.target.value }))}
                />
              </Field>
            </div>
          </div>
        ) : null}

        {activeTab === 'verify' ? (
          <div className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Titre (login)">
                <input
                  className={inputClass}
                  value={form.verifyLoginTitle}
                  onChange={(e) => setForm((f) => ({ ...f, verifyLoginTitle: e.target.value }))}
                />
              </Field>
              <Field label="Titre (signup)">
                <input
                  className={inputClass}
                  value={form.verifySignupTitle}
                  onChange={(e) => setForm((f) => ({ ...f, verifySignupTitle: e.target.value }))}
                />
              </Field>
            </div>
            <Field label="Message code envoyé" hint="Placeholder {email}">
              <input
                className={inputClass}
                value={form.verifyBodySent}
                onChange={(e) => setForm((f) => ({ ...f, verifyBodySent: e.target.value }))}
              />
            </Field>
            <Field label="Message en attente">
              <textarea
                className={inputClass}
                rows={2}
                value={form.verifyBodyPending}
                onChange={(e) => setForm((f) => ({ ...f, verifyBodyPending: e.target.value }))}
              />
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Compte à rebours renvoi" hint="Placeholder {seconds}">
                <input
                  className={inputClass}
                  value={form.verifyResendCountdown}
                  onChange={(e) => setForm((f) => ({ ...f, verifyResendCountdown: e.target.value }))}
                />
              </Field>
              <Field label="Bouton renvoi">
                <input
                  className={inputClass}
                  value={form.verifyResendLabel}
                  onChange={(e) => setForm((f) => ({ ...f, verifyResendLabel: e.target.value }))}
                />
              </Field>
              <Field label="Helper mauvais email">
                <input
                  className={inputClass}
                  value={form.verifyWrongEmailHelper}
                  onChange={(e) => setForm((f) => ({ ...f, verifyWrongEmailHelper: e.target.value }))}
                />
              </Field>
              <Field label="Retour login">
                <input
                  className={inputClass}
                  value={form.verifyBackToLoginLabel}
                  onChange={(e) => setForm((f) => ({ ...f, verifyBackToLoginLabel: e.target.value }))}
                />
              </Field>
              <Field label="Retour signup">
                <input
                  className={inputClass}
                  value={form.verifyBackToSignupLabel}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, verifyBackToSignupLabel: e.target.value }))
                  }
                />
              </Field>
            </div>
          </div>
        ) : null}

        {activeTab === 'legal' ? (
          <div className="grid gap-4">
            <Field label="Préfixe footnote">
              <input
                className={inputClass}
                value={form.legalFootnotePrefix}
                onChange={(e) => setForm((f) => ({ ...f, legalFootnotePrefix: e.target.value }))}
              />
            </Field>
            <Field label="Conjonction (and)">
              <input
                className={inputClass}
                value={form.legalFootnoteConjunction}
                onChange={(e) =>
                  setForm((f) => ({ ...f, legalFootnoteConjunction: e.target.value }))
                }
              />
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Terms — libellé">
                <input
                  className={inputClass}
                  value={form.legalTermsLabel}
                  onChange={(e) => setForm((f) => ({ ...f, legalTermsLabel: e.target.value }))}
                />
              </Field>
              <Field label="Terms — URL" hint="Page CMS ou lien externe">
                <input
                  className={inputClass}
                  value={form.legalTermsHref}
                  onChange={(e) => setForm((f) => ({ ...f, legalTermsHref: e.target.value }))}
                />
              </Field>
              <Field label="Privacy — libellé">
                <input
                  className={inputClass}
                  value={form.legalPrivacyLabel}
                  onChange={(e) => setForm((f) => ({ ...f, legalPrivacyLabel: e.target.value }))}
                />
              </Field>
              <Field label="Privacy — URL">
                <input
                  className={inputClass}
                  value={form.legalPrivacyHref}
                  onChange={(e) => setForm((f) => ({ ...f, legalPrivacyHref: e.target.value }))}
                />
              </Field>
            </div>
          </div>
        ) : null}

        {activeTab === 'settings' ? (
          <div className="space-y-6">
            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-slate-50/60 p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-gray-300"
                checked={ssoEnabled}
                onChange={(e) => setSsoEnabled(e.target.checked)}
              />
              <span className="space-y-1">
                <span className="block text-sm font-medium text-gray-900">
                  Afficher Google et Apple (login + signup)
                </span>
                <span className="block text-xs text-gray-500">
                  Si activé : séparateur « or » + les deux boutons SSO. Si désactivé : tout le bloc
                  est masqué sur le parcours auth.
                </span>
              </span>
            </label>

            <Field
              label="Délai entre deux renvois OTP (secondes)"
              hint="Global — identique pour toutes les langues. Min 15, max 300."
            >
              <input
                type="number"
                min={15}
                max={300}
                className={`${inputClass} max-w-[160px]`}
                value={resendSeconds}
                onChange={(e) => setResendSeconds(Number(e.target.value) || 45)}
              />
            </Field>
          </div>
        ) : null}
      </div>

      <div className="flex justify-end">
        <Button type="button" onClick={() => void handleSave()} disabled={saving}>
          {saving ? 'Enregistrement…' : 'Enregistrer'}
        </Button>
      </div>
    </div>
  )
}

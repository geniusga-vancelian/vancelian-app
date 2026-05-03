'use client'

import * as React from 'react'
import Link from 'next/link'
import {
  ExternalLink,
  Palette,
  Type as TypeIcon,
  Component as ComponentIcon,
  Mail,
} from 'lucide-react'
import {
  EmailShell,
  EmailHeader,
  EmailFooter,
  EmailEyebrow,
  EmailSectionRule,
  EmailPrimaryButton,
  EmailSecondaryButton,
  EmailWordmark,
  NewsletterExample,
  emailDsColors,
  emailDsFonts,
  emailDsGradient,
  emailDsLayout,
  emailDsRadius,
  emailDsType,
} from '@/email-ds'

const colorEntries: Array<[string, string]> = Object.entries(emailDsColors).map(
  ([k, v]) => [k, String(v)],
)

const typeEntries = Object.entries(emailDsType) as Array<
  [keyof typeof emailDsType, (typeof emailDsType)[keyof typeof emailDsType]]
>

type SectionId =
  | 'overview'
  | 'tokens'
  | 'typography'
  | 'atoms'
  | 'headers'
  | 'footers'
  | 'newsletter'
  | 'mjml'

const SECTIONS: Array<{ id: SectionId; label: string; icon: React.ElementType }> =
  [
    { id: 'overview', label: 'Overview', icon: Mail },
    { id: 'tokens', label: 'Tokens', icon: Palette },
    { id: 'typography', label: 'Typography', icon: TypeIcon },
    { id: 'atoms', label: 'Atoms (buttons, eyebrow, rule)', icon: ComponentIcon },
    { id: 'headers', label: 'Headers L1 / L2 / L3', icon: ComponentIcon },
    { id: 'footers', label: 'Footer', icon: ComponentIcon },
    { id: 'newsletter', label: 'Newsletter (React preview)', icon: Mail },
    { id: 'mjml', label: 'MJML templates (production)', icon: Mail },
  ]

const MJML_TEMPLATES: Array<{ id: string; description: string }> = [
  { id: 'newsletter-quarterly', description: 'Lettre éditoriale (hero L1 + cards + dark CTA)' },
  { id: 'otp-login', description: 'Code OTP de connexion (transactionnel critique)' },
  { id: 'transaction-confirmation', description: 'Confirmation d’opération (souscription, retrait…)' },
  { id: 'welcome', description: 'Email de bienvenue après inscription validée' },
]

function SwatchCard({ name, value }: { name: string; value: string }) {
  const isAlpha = value.startsWith('rgba') || value.startsWith('hsla')
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        overflow: 'hidden',
        background: '#fff',
      }}
    >
      <div
        style={{
          height: 72,
          background: value,
          backgroundImage: isAlpha
            ? 'repeating-conic-gradient(#f3f4f6 0 25%, #ffffff 0 50%) 0 0/16px 16px, ' +
              `linear-gradient(${value}, ${value})`
            : undefined,
        }}
      />
      <div style={{ padding: '10px 12px' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#111827' }}>
          {name}
        </div>
        <div style={{ fontSize: 11, color: '#6b7280', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
          {value}
        </div>
      </div>
    </div>
  )
}

function Panel({
  title,
  subtitle,
  children,
  id,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  id?: string
}) {
  return (
    <section
      id={id}
      className="bg-white border border-gray-200 rounded-xl p-6 scroll-mt-24"
    >
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          {subtitle ? (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          ) : null}
        </div>
      </div>
      {children}
    </section>
  )
}

function PreviewCanvas({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: '#f5f5f7',
        padding: 24,
        borderRadius: 12,
        border: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      {children}
    </div>
  )
}

export function EmailDesignSystemShowcase() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Email Design System
          </h1>
          <p className="text-sm text-gray-500 mt-1 max-w-2xl">
            DS dédié au rendu HTML e‑mail (découplé du DS site et de l’app).
            Styles inline, largeur canonique 600 px, compatibles clients mail
            majeurs (Gmail, Apple Mail, Outlook). Assets statiques :{' '}
            <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">
              public/email-ds/
            </code>
            .
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/preview/email/newsletter"
            target="_blank"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <ExternalLink className="w-4 h-4" />
            Preview plein écran
          </Link>
          <Link
            href="/admin/email-modules"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
          >
            <Mail className="w-4 h-4" />
            Email Modules (DB)
          </Link>
        </div>
      </div>

      {/* Table of contents */}
      <nav className="bg-white border border-gray-200 rounded-xl p-4 flex flex-wrap gap-2">
        {SECTIONS.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-full border border-gray-200 text-gray-700 hover:bg-gray-50"
          >
            <s.icon className="w-3.5 h-3.5" />
            {s.label}
          </a>
        ))}
      </nav>

      {/* Overview */}
      <Panel
        id="overview"
        title="Architecture"
        subtitle="Pourquoi un DS e‑mail séparé"
      >
        <ul className="text-sm text-gray-700 space-y-2 list-disc pl-5">
          <li>
            <strong>Séparé</strong> du DS site/app (
            <code>src/components/design-system/</code>) pour éviter toute
            dépendance CSS globale — les clients mail ignorent la plupart du CSS
            externe.
          </li>
          <li>
            <strong>Inline-only</strong> : tous les composants écrivent leurs
            styles en inline (<code>style=&#123;&#123;…&#125;&#125;</code>).
          </li>
          <li>
            <strong>Tokens dédiés</strong> : <code>emailDsColors</code>,{' '}
            <code>emailDsFonts</code>, <code>emailDsType</code>,{' '}
            <code>emailDsLayout</code>, <code>emailDsRadius</code>.
          </li>
          <li>
            <strong>Assets</strong> : <code>emailDsAssetUrl(file, origin?)</code>{' '}
            pour préfixer par une origine absolue au moment de l’envoi (ESP,
            SMTP).
          </li>
          <li>
            <strong>Mappage EmailModule</strong> : HEADER → <code>EmailHeader</code>
            , BODY STARTER → bloc d’intro + CTA, FOOTER → <code>EmailFooter</code>
            .
          </li>
        </ul>
      </Panel>

      {/* Tokens */}
      <Panel
        id="tokens"
        title="Couleurs & tokens"
        subtitle="emailDsColors · emailDsGradient · emailDsLayout · emailDsRadius"
      >
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {colorEntries.map(([name, value]) => (
            <SwatchCard key={name} name={name} value={value} />
          ))}
        </div>

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div
            style={{
              height: 72,
              borderRadius: 10,
              backgroundImage: emailDsGradient,
            }}
          />
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm">
            <div className="font-semibold text-gray-900 mb-1">Layout</div>
            <div className="text-gray-600">
              contentWidthPx: {emailDsLayout.contentWidthPx}
              <br />
              padX: {emailDsLayout.padX} · padY: {emailDsLayout.padY}
            </div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm">
            <div className="font-semibold text-gray-900 mb-1">Radius</div>
            <div className="text-gray-600">
              pill: {emailDsRadius.pill} · card: {emailDsRadius.card} · chip:{' '}
              {emailDsRadius.chip}
            </div>
          </div>
        </div>
      </Panel>

      {/* Typography */}
      <Panel
        id="typography"
        title="Typographie"
        subtitle="emailDsType · emailDsFonts (stacks e‑mail safe + fallbacks système)"
      >
        <div className="space-y-4">
          {typeEntries.map(([name, def]) => {
            const lh = 'lineHeight' in def ? def.lineHeight : undefined
            const ls = 'letterSpacing' in def ? def.letterSpacing : undefined
            return (
              <div
                key={name}
                className="flex flex-wrap items-baseline justify-between gap-4 border-b border-gray-100 pb-3"
              >
                <div
                  style={{
                    fontFamily:
                      name === 'tinyCaps' || name === 'meta'
                        ? emailDsFonts.eyebrow
                        : emailDsFonts.display,
                    fontSize: def.fontSize,
                    fontWeight: def.fontWeight,
                    lineHeight: lh,
                    letterSpacing: ls,
                    color: emailDsColors.ink,
                    textTransform: name === 'tinyCaps' ? 'uppercase' : undefined,
                  }}
                >
                  The quick brown fox ({name})
                </div>
                <code className="text-xs text-gray-500 font-mono">
                  {def.fontSize}px · weight {def.fontWeight}
                  {lh !== undefined ? ` · lh ${lh}` : ''}
                  {ls !== undefined ? ` · ls ${ls}` : ''}
                </code>
              </div>
            )
          })}
        </div>
      </Panel>

      {/* Atoms */}
      <Panel
        id="atoms"
        title="Atoms"
        subtitle="Boutons · Eyebrow · Rule · Wordmark"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-5 bg-white space-y-4">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              EmailPrimaryButton / Secondary (light)
            </div>
            <div className="flex flex-wrap gap-3">
              <EmailPrimaryButton href="#">Read the letter</EmailPrimaryButton>
              <EmailSecondaryButton href="#">Learn more</EmailSecondaryButton>
            </div>
          </div>

          <div
            className="border border-gray-200 rounded-lg p-5 space-y-4"
            style={{ background: emailDsColors.charcoal }}
          >
            <div
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'rgba(255,255,255,0.6)' }}
            >
              EmailPrimaryButton / Secondary (dark)
            </div>
            <div className="flex flex-wrap gap-3">
              <EmailPrimaryButton href="#" dark>
                Read the letter
              </EmailPrimaryButton>
              <EmailSecondaryButton href="#" onDark>
                Learn more
              </EmailSecondaryButton>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-5 bg-white space-y-4">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              EmailEyebrow
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <EmailEyebrow>Quarterly Letter</EmailEyebrow>
              <EmailEyebrow variant="solid">Solid</EmailEyebrow>
            </div>
            <div
              className="p-4 rounded"
              style={{ background: emailDsColors.ink }}
            >
              <EmailEyebrow variant="light">On dark</EmailEyebrow>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-5 bg-white space-y-4">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              EmailSectionRule · EmailWordmark
            </div>
            <EmailSectionRule />
            <div className="flex items-center gap-6 pt-2">
              <EmailWordmark heightPx={22} />
              <div
                className="p-3 rounded"
                style={{ background: emailDsColors.black }}
              >
                <EmailWordmark heightPx={22} invert />
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* Headers */}
      <Panel
        id="headers"
        title="Headers — 3 niveaux"
        subtitle="L1 Hero · L2 Standard · L3 Minimal (exports Newsletter.zip)"
      >
        <div className="space-y-6">
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Level 1 — Hero
            </div>
            <PreviewCanvas>
              <EmailShell>
                <EmailHeader
                  level={1}
                  heroImageUrl="https://images.unsplash.com/photo-1494949360228-4e9bde560065?auto=format&fit=crop&w=1600&q=80"
                  eyebrow="Quarterly Letter"
                  title="The new architecture of private assets."
                  kicker="Q2 · 2026 · 6 min read"
                />
              </EmailShell>
            </PreviewCanvas>
          </div>

          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Level 2 — Standard (wordmark + nav)
            </div>
            <PreviewCanvas>
              <EmailShell>
                <EmailHeader
                  level={2}
                  navLinks={[
                    { label: 'Vaults', href: '#' },
                    { label: 'Offers', href: '#' },
                    { label: 'About', href: '#' },
                  ]}
                />
              </EmailShell>
            </PreviewCanvas>
          </div>

          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Level 3 — Minimal
            </div>
            <PreviewCanvas>
              <EmailShell>
                <EmailHeader level={3} />
              </EmailShell>
            </PreviewCanvas>
          </div>
        </div>
      </Panel>

      {/* Footer */}
      <Panel id="footers" title="Footer" subtitle="EmailFooter — social, copyright, préférences">
        <PreviewCanvas>
          <EmailShell>
            <EmailFooter />
          </EmailShell>
        </PreviewCanvas>
      </Panel>

      {/* Newsletter */}
      <Panel
        id="newsletter"
        title="Newsletter — preview React (DS inline)"
        subtitle="Pour itérer rapidement en navigateur. Rendu d'envoi : voir section MJML ci-dessous."
      >
        <PreviewCanvas>
          <NewsletterExample />
        </PreviewCanvas>
        <p className="text-xs text-gray-500 mt-3">
          Rendu chrome‑free à la taille réelle sur{' '}
          <Link
            href="/preview/email/newsletter"
            target="_blank"
            className="underline text-gray-800"
          >
            /preview/email/newsletter
          </Link>
          .
        </p>
      </Panel>

      {/* MJML production templates */}
      <Panel
        id="mjml"
        title="MJML templates (rendu d'envoi)"
        subtitle="Compilés depuis emails/mjml/templates/. Pipeline production strict (validation MJML + Zod)."
      >
        <ul className="space-y-3">
          {MJML_TEMPLATES.map((t) => (
            <li
              key={t.id}
              className="flex items-center justify-between gap-4 border border-gray-200 rounded-lg p-4 bg-white"
            >
              <div>
                <div className="font-mono text-sm font-semibold text-gray-900">
                  {t.id}
                </div>
                <div className="text-sm text-gray-500 mt-0.5">{t.description}</div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Link
                  href={`/preview/email/${t.id}?locale=fr`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700"
                >
                  Preview FR
                </Link>
                <Link
                  href={`/preview/email/${t.id}?locale=en`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700"
                >
                  Preview EN
                </Link>
                <Link
                  href={`/api/admin/email/preview?templateId=${t.id}&locale=fr`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700 font-mono"
                >
                  JSON
                </Link>
                <Link
                  href={`/api/admin/email/preview?templateId=${t.id}&locale=fr&inline=1`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700 font-mono"
                >
                  HTML
                </Link>
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
              Build local
            </div>
            <code className="font-mono text-xs">npm run emails:build</code>
            <p className="text-xs text-gray-500 mt-2">
              Compile chaque template × locale dans <code>emails/rendered/</code>.
            </p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
              Server preview
            </div>
            <code className="font-mono text-xs">npm run emails:preview</code>
            <p className="text-xs text-gray-500 mt-2">
              Mini serveur sur <code>localhost:5757</code> (rendu chrome-free).
            </p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
              Validate strict
            </div>
            <code className="font-mono text-xs">npm run emails:validate</code>
            <p className="text-xs text-gray-500 mt-2">
              Compile chaque template avec sa fixture + MJML strict + Zod.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  )
}

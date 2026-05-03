import type { Metadata } from 'next'
import { headers } from 'next/headers'
import { notFound } from 'next/navigation'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { renderTemplate, EMAIL_TEMPLATES } from '@/lib/email'
import {
  EMAIL_TEMPLATE_IDS,
  SUPPORTED_EMAIL_LOCALES,
  type EmailTemplateId,
  type EmailLocale,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'

/**
 * Reconstruit l'origin de la requête courante (ex. `http://localhost:3001`).
 *
 * Utilisé pour override `assetOrigin` dans les fixtures, qui pointent vers le
 * host de prod (`https://www.arquantix.com`) — non joignable en dev. Ainsi les
 * assets `/email-ds/*.png` sont chargés depuis la même app Next (`public/`).
 */
function currentOriginFromHeaders(): string {
  const h = headers()
  const host = h.get('x-forwarded-host') ?? h.get('host') ?? 'localhost:3001'
  const proto =
    h.get('x-forwarded-proto') ??
    (host.startsWith('localhost') || host.startsWith('127.') ? 'http' : 'https')
  return `${proto}://${host}`
}

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Email preview',
  robots: { index: false, follow: false },
}

interface PageProps {
  params: { template: string }
  searchParams?: { locale?: string }
}

async function loadFixtureVars(templateId: EmailTemplateId) {
  const file = path.join(MJML_PATHS.fixtures, `${templateId}.json`)
  try {
    const raw = await fs.readFile(file, 'utf8')
    const fx = JSON.parse(raw) as { vars: Record<string, unknown> }
    return fx.vars
  } catch {
    return null
  }
}

/**
 * Aperçu plein écran d’un template MJML rendu en HTML, dans une `<iframe srcDoc>`.
 * L’iframe **isole** entièrement le DOM/CSS de la page Next, ce qui reproduit
 * fidèlement le rendu d’un client mail.
 */
export default async function EmailTemplatePreview({ params, searchParams }: PageProps) {
  const candidate = params.template
  if (!(EMAIL_TEMPLATE_IDS as readonly string[]).includes(candidate)) {
    notFound()
  }
  const templateId = candidate as EmailTemplateId
  const localeParam = searchParams?.locale ?? 'fr'
  const locale = (SUPPORTED_EMAIL_LOCALES as readonly string[]).includes(localeParam)
    ? (localeParam as EmailLocale)
    : ('fr' as EmailLocale)

  const fixtureVars = await loadFixtureVars(templateId)
  if (!fixtureVars) {
    return (
      <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif' }}>
        <h1>Fixture manquante</h1>
        <p>
          Aucune fixture trouvée pour <code>{templateId}</code> à l’emplacement
          <br />
          <code>emails/fixtures/{templateId}.json</code>
        </p>
      </div>
    )
  }

  const localOrigin = currentOriginFromHeaders()

  let html: string
  let subject: string
  let renderError: string | null = null
  try {
    const r = await renderTemplate({
      templateId,
      locale,
      vars: { ...fixtureVars, locale, assetOrigin: localOrigin },
      beautify: true,
    })
    html = r.html
    subject = r.subject
  } catch (err) {
    html = ''
    subject = ''
    renderError = err instanceof Error ? err.message : String(err)
  }

  const description = EMAIL_TEMPLATES[templateId].description
  const localeLinks = SUPPORTED_EMAIL_LOCALES.map((l) => ({ l, active: l === locale }))

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f5f5f7',
        padding: 24,
        boxSizing: 'border-box',
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      }}
    >
      <header
        style={{
          maxWidth: 720,
          margin: '0 auto 16px',
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: 12,
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Template MJML</div>
          <div style={{ fontWeight: 600, color: '#101113' }}>{templateId}</div>
          <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{description}</div>
          {subject ? (
            <div style={{ fontSize: 13, color: '#101113', marginTop: 6 }}>
              <strong>Subject:</strong> {subject}
            </div>
          ) : null}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {localeLinks.map(({ l, active }) => (
            <a
              key={l}
              href={`/preview/email/${templateId}?locale=${l}`}
              style={{
                padding: '6px 10px',
                borderRadius: 999,
                fontSize: 12,
                textDecoration: 'none',
                color: active ? '#fff' : '#101113',
                background: active ? '#101113' : '#f3f4f6',
                border: '1px solid #e5e7eb',
              }}
            >
              {l.toUpperCase()}
            </a>
          ))}
        </div>
      </header>

      {renderError ? (
        <div
          style={{
            maxWidth: 720,
            margin: '0 auto',
            background: '#fee2e2',
            color: '#7f1d1d',
            border: '1px solid #fca5a5',
            borderRadius: 12,
            padding: 16,
            whiteSpace: 'pre-wrap',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 12,
          }}
        >
          {renderError}
        </div>
      ) : (
        <iframe
          title={`email-preview-${templateId}`}
          srcDoc={html}
          style={{
            width: '100%',
            maxWidth: 680,
            display: 'block',
            margin: '0 auto',
            height: 'calc(100vh - 160px)',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: 12,
          }}
        />
      )}
    </div>
  )
}

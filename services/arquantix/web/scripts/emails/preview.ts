/**
 * Mini serveur HTTP local de prévisualisation des templates MJML.
 *
 * Usage :  npm run emails:preview
 *  → http://localhost:5757/                      → index
 *  → http://localhost:5757/<templateId>?locale=fr → preview
 */
import http from 'node:http'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { renderTemplate } from '@/lib/email'
import {
  EMAIL_TEMPLATE_IDS,
  SUPPORTED_EMAIL_LOCALES,
  type EmailLocale,
  type EmailTemplateId,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'
import { EMAIL_TEMPLATES } from '@/lib/email/templateRegistry'

const PORT = Number(process.env.EMAIL_PREVIEW_PORT || 5757)

async function loadFixture(templateId: EmailTemplateId): Promise<{ vars: Record<string, unknown> } | null> {
  try {
    const raw = await fs.readFile(
      path.join(MJML_PATHS.fixtures, `${templateId}.json`),
      'utf8',
    )
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function indexHtml(): string {
  const items = EMAIL_TEMPLATE_IDS.map((id) => {
    const links = SUPPORTED_EMAIL_LOCALES.map(
      (l) => `<a href="/${id}?locale=${l}">${l}</a>`,
    ).join(' · ')
    return `<li><strong>${id}</strong> — ${EMAIL_TEMPLATES[id].description} <br/> ${links}</li>`
  }).join('')

  return `<!doctype html>
<html><head><meta charset="utf-8"><title>Email previews</title>
<style>
  body { font-family: -apple-system, system-ui, Segoe UI, Roboto, sans-serif; padding: 32px; max-width: 720px; margin: 0 auto; color:#101113; }
  h1 { margin-bottom: 4px; }
  p.lead { color: #62656E; margin-top: 0; }
  ul { list-style: none; padding: 0; }
  li { padding: 14px 0; border-bottom: 1px solid #EAEAEA; }
  a { color: #0F62FE; text-decoration: none; margin-right: 6px; }
</style></head>
<body>
<h1>Email previews</h1>
<p class="lead">Templates MJML rendus depuis <code>emails/mjml/templates/</code> avec les fixtures de <code>emails/fixtures/</code>.</p>
<ul>${items}</ul>
</body></html>`
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? '/', `http://localhost:${PORT}`)
  const pathname = url.pathname

  if (pathname === '/' || pathname === '/index.html') {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
    res.end(indexHtml())
    return
  }

  // Asset proxy : /assets/<file> → public/email-ds/<file>
  if (pathname.startsWith('/assets/')) {
    const file = pathname.replace(/^\/assets\//, '')
    const abs = path.join(process.cwd(), 'public', 'email-ds', file)
    try {
      const data = await fs.readFile(abs)
      const ext = path.extname(file).toLowerCase()
      const ct =
        ext === '.svg' ? 'image/svg+xml' :
        ext === '.png' ? 'image/png' :
        ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' :
        'application/octet-stream'
      res.writeHead(200, { 'content-type': ct })
      res.end(data)
      return
    } catch {
      res.writeHead(404).end('Asset not found')
      return
    }
  }

  const id = pathname.replace(/^\//, '') as EmailTemplateId
  if (!EMAIL_TEMPLATE_IDS.includes(id)) {
    res.writeHead(404, { 'content-type': 'text/plain' })
    res.end(`Unknown template "${id}". Available: ${EMAIL_TEMPLATE_IDS.join(', ')}`)
    return
  }
  const localeParam = (url.searchParams.get('locale') as EmailLocale | null) ?? 'fr'
  const locale = (SUPPORTED_EMAIL_LOCALES as readonly string[]).includes(localeParam)
    ? localeParam
    : ('fr' as EmailLocale)

  try {
    const fixture = await loadFixture(id)
    if (!fixture) {
      res.writeHead(404, { 'content-type': 'text/plain' })
      res.end(`No fixture for template ${id} (expected emails/fixtures/${id}.json)`)
      return
    }
    const vars = { ...fixture.vars, locale }
    const rendered = await renderTemplate({ templateId: id, locale, vars, beautify: true })
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
    res.end(rendered.html)
  } catch (err) {
    res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
    res.end(`Render error: ${err instanceof Error ? err.message : String(err)}`)
  }
})

server.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`📨  Email preview ready → http://localhost:${PORT}/`)
})

import { NextResponse, type NextRequest } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import {
  interpolate,
  loadEmailPartials,
  renderMjmlString,
  MjmlValidationError,
} from '@/lib/email'
import {
  EMAIL_COMPONENTS,
  getEmailComponent,
} from '@/lib/email/componentCatalog'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * Rend un **composant MJML standalone** dans un mini document HTML, prêt à
 * afficher dans une `<iframe srcDoc>` côté admin.
 *
 * - Pour les composants `section` : on enveloppe avec `<mjml><mj-body>{{> X}}</mj-body></mjml>`.
 * - Pour les composants `inline` (boutons, eyebrow…) : on enveloppe avec une
 *   section/colonne (`<mjml><mj-body><mj-section><mj-column>{{> X}}</mj-column></mj-section></mj-body></mjml>`).
 *
 * Variables : par défaut on utilise l’exemple du catalogue. Si le client passe
 * `?vars=<json>` (encoded), on utilise ces variables (validation très souple).
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const session = await getSessionFromCookie()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const entry = getEmailComponent(params.id)
  if (!entry) {
    return NextResponse.json(
      { error: `Unknown component: ${params.id}`, available: EMAIL_COMPONENTS.map((c) => c.id) },
      { status: 404 },
    )
  }

  const url = new URL(request.url)
  const customVarsRaw = url.searchParams.get('vars')
  let vars: Record<string, unknown> = entry.vars
  if (customVarsRaw) {
    try {
      const parsed = JSON.parse(customVarsRaw) as Record<string, unknown>
      vars = { ...entry.vars, ...parsed }
    } catch {
      return NextResponse.json({ error: 'Invalid `vars` JSON in querystring' }, { status: 400 })
    }
  }

  const wrapped = wrapStandalone(entry.id, entry.kind)

  try {
    const partials = await loadEmailPartials()
    const interpolated = interpolate(wrapped, vars, partials)
    const { html } = await renderMjmlString(interpolated, {
      validationLevel: 'strict',
      beautify: true,
    })
    return new NextResponse(html, {
      status: 200,
      headers: { 'content-type': 'text/html; charset=utf-8' },
    })
  } catch (err) {
    if (err instanceof MjmlValidationError) {
      return new NextResponse(
        `<!doctype html><html><body style="font:13px ui-monospace,Menlo,monospace;color:#7f1d1d;background:#fee2e2;padding:16px;white-space:pre-wrap;">MJML strict failed for ${entry.id}:\n${err.message}</body></html>`,
        { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' } },
      )
    }
    const msg = err instanceof Error ? err.message : String(err)
    return new NextResponse(
      `<!doctype html><html><body style="font:13px ui-monospace,Menlo,monospace;color:#7f1d1d;background:#fee2e2;padding:16px;white-space:pre-wrap;">${escapeHtml(msg)}</body></html>`,
      { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' } },
    )
  }
}

function wrapStandalone(id: string, kind: 'section' | 'inline'): string {
  const head = `{{> head}}`
  if (kind === 'section') {
    return `<mjml>${head}<mj-body background-color="#FFFFFF" width="600px">{{> ${id}}}</mj-body></mjml>`
  }
  // inline → on enveloppe d’un section/column
  return `<mjml>${head}<mj-body background-color="#FFFFFF" width="600px"><mj-section padding="24px 32px"><mj-column>{{> ${id}}}</mj-column></mj-section></mj-body></mjml>`
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

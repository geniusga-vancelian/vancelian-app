import { NextResponse, type NextRequest } from 'next/server'
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { z } from 'zod'
import { getSessionFromCookie } from '@/lib/auth'
import { renderTemplate, SUPPORTED_EMAIL_LOCALES } from '@/lib/email'
import {
  EMAIL_TEMPLATE_IDS,
  type EmailLocale,
  type EmailTemplateId,
} from '@/lib/email/types'
import { MJML_PATHS } from '@/lib/email/mjmlRender'
import {
  EmailTemplateVarsError,
} from '@/lib/email/interpolate'
import { MjmlValidationError } from '@/lib/email/mjmlRender'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const querySchema = z.object({
  templateId: z.enum(EMAIL_TEMPLATE_IDS),
  locale: z.enum(SUPPORTED_EMAIL_LOCALES).default('fr'),
  /** `inline=1` → renvoie le HTML directement (text/html) pour <iframe>. */
  inline: z.union([z.literal('1'), z.literal('true'), z.string()]).optional(),
})

/**
 * Rend un template MJML avec sa fixture canonique.
 *
 * - `GET`  : utilise la fixture par défaut (`emails/fixtures/<id>.json`).
 * - `POST` : permet de fournir des `vars` ad-hoc dans le body (JSON).
 *
 * Réponses :
 * - JSON `{ subject, html, text, locale, templateId }` par défaut
 * - HTML brut (`text/html`) si `?inline=1` (utile pour <iframe srcDoc/src>)
 */
export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const url = new URL(request.url)
  const parsed = querySchema.safeParse({
    templateId: url.searchParams.get('templateId'),
    locale: url.searchParams.get('locale') ?? undefined,
    inline: url.searchParams.get('inline') ?? undefined,
  })
  if (!parsed.success) {
    return NextResponse.json(
      { error: 'Invalid query params', issues: parsed.error.issues },
      { status: 400 },
    )
  }
  const { templateId, locale, inline } = parsed.data

  const fixture = await loadFixture(templateId)
  if (!fixture) {
    return NextResponse.json(
      { error: `Fixture manquante pour ${templateId}.` },
      { status: 404 },
    )
  }

  return doRender({ templateId, locale, vars: { ...fixture.vars, locale }, inline: !!inline })
}

const postBodySchema = z.object({
  templateId: z.enum(EMAIL_TEMPLATE_IDS),
  locale: z.enum(SUPPORTED_EMAIL_LOCALES).default('fr'),
  vars: z.record(z.string(), z.unknown()),
  inline: z.boolean().optional(),
})

export async function POST(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }
  const parsed = postBodySchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json(
      { error: 'Invalid body', issues: parsed.error.issues },
      { status: 400 },
    )
  }
  const { templateId, locale, vars, inline } = parsed.data
  return doRender({ templateId, locale, vars: { ...vars, locale }, inline: !!inline })
}

async function doRender(args: {
  templateId: EmailTemplateId
  locale: EmailLocale
  vars: Record<string, unknown>
  inline: boolean
}) {
  try {
    const rendered = await renderTemplate({
      templateId: args.templateId,
      locale: args.locale,
      vars: args.vars,
      beautify: true,
    })
    if (args.inline) {
      return new NextResponse(rendered.html, {
        status: 200,
        headers: { 'content-type': 'text/html; charset=utf-8' },
      })
    }
    return NextResponse.json(rendered)
  } catch (err) {
    if (err instanceof EmailTemplateVarsError) {
      return NextResponse.json(
        { error: err.message, code: 'INVALID_VARS', issues: err.zodError.issues },
        { status: 400 },
      )
    }
    if (err instanceof MjmlValidationError) {
      return NextResponse.json(
        { error: err.message, code: 'MJML_INVALID', issues: err.errors },
        { status: 400 },
      )
    }
    console.error('[email/preview] render error:', err)
    const message = err instanceof Error ? err.message : 'Internal error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

async function loadFixture(
  templateId: EmailTemplateId,
): Promise<{ vars: Record<string, unknown> } | null> {
  try {
    const raw = await fs.readFile(
      path.join(MJML_PATHS.fixtures, `${templateId}.json`),
      'utf8',
    )
    return JSON.parse(raw)
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') return null
    throw e
  }
}


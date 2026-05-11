/**
 * GET (lire) / PUT (mettre à jour) / POST (créer) un fichier `.md` du wiki.
 * Paramètre `path` : chemin relatif à la racine wiki (ex. `faq/savings/foo.md`).
 */
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import {
  createWikiFile,
  readWikiFile,
  writeWikiFile,
} from '@/lib/admin/assistanceWikiFs'

export const dynamic = 'force-dynamic'

const postSchema = z.object({
  path: z.string().min(1),
  content: z.string(),
})

export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const p = request.nextUrl.searchParams.get('path')
  if (!p) {
    return NextResponse.json({ error: 'missing_path' }, { status: 400 })
  }

  const res = await readWikiFile(p)
  if ('error' in res && res.error === 'not_found') {
    return NextResponse.json({ error: 'not_found' }, { status: 404 })
  }
  if ('error' in res) {
    return NextResponse.json({ error: res.error }, { status: 400 })
  }
  return NextResponse.json({ path: p, content: res.content })
}

export async function PUT(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const p = request.nextUrl.searchParams.get('path')
  if (!p) {
    return NextResponse.json({ error: 'missing_path' }, { status: 400 })
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 })
  }
  const parsed = z.object({ content: z.string() }).safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid_body' }, { status: 400 })
  }

  const res = await writeWikiFile(p, parsed.data.content)
  if ('error' in res) {
    const status = res.error === 'invalid_path' ? 400 : 500
    return NextResponse.json({ error: res.error }, { status })
  }
  return NextResponse.json({ ok: true })
}

export async function POST(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 })
  }

  const parsed = postSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid_body' }, { status: 400 })
  }

  const res = await createWikiFile(parsed.data.path, parsed.data.content)
  if ('error' in res) {
    const err = res.error
    const status =
      err === 'already_exists'
        ? 409
        : err === 'invalid_path' ||
            err === 'invalid_faq_category' ||
            err === 'invalid_faq_path'
          ? 400
          : 500
    return NextResponse.json({ error: err }, { status })
  }
  return NextResponse.json({ ok: true, path: parsed.data.path })
}

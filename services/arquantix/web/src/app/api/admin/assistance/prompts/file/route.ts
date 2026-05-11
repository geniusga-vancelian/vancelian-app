/**
 * Contenu d'un fichier Markdown de prompt assistance (lecture seule).
 * Query : `?path=relative/path.md` sous `api/services/assistance/prompts/`.
 */
import { NextResponse } from 'next/server'

import {
  assistancePromptsRootExists,
  getAssistancePromptsRoot,
  readPromptFile,
} from '@/lib/admin/assistancePromptsFs'
import { getSessionFromCookie } from '@/lib/auth'

export const dynamic = 'force-dynamic'

export async function GET(req: Request) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { searchParams } = new URL(req.url)
  const rel = searchParams.get('path') ?? ''
  const ok = await assistancePromptsRootExists()
  if (!ok) {
    return NextResponse.json(
      {
        error: 'prompts_root_missing',
        root: getAssistancePromptsRoot(),
        message:
          'Dossier prompts introuvable. Définissez ASSISTANCE_PROMPTS_ROOT ou ouvrez depuis le monorepo (../api/services/assistance/prompts).',
      },
      { status: 503 }
    )
  }

  const data = await readPromptFile(rel)
  if (!data) {
    return NextResponse.json({ error: 'not_found_or_invalid_path' }, { status: 404 })
  }

  return NextResponse.json({
    path: rel,
    root: getAssistancePromptsRoot(),
    content: data.content,
    bytes: Buffer.byteLength(data.content, 'utf-8'),
  })
}

/**
 * Liste les fichiers `.md` disponibles sous `prompts/` (vérif concordance avec le disque).
 */
import { NextResponse } from 'next/server'

import {
  assistancePromptsRootExists,
  getAssistancePromptsRoot,
  listPromptMarkdownFiles,
} from '@/lib/admin/assistancePromptsFs'
import { getSessionFromCookie } from '@/lib/auth'

export const dynamic = 'force-dynamic'

export async function GET() {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const root = getAssistancePromptsRoot()
  const exists = await assistancePromptsRootExists()
  if (!exists) {
    return NextResponse.json(
      {
        error: 'prompts_root_missing',
        root,
        files: [] as string[],
        message:
          'Dossier prompts introuvable. Définissez ASSISTANCE_PROMPTS_ROOT ou ouvrez depuis le monorepo.',
      },
      { status: 503 }
    )
  }

  const files = await listPromptMarkdownFiles()
  return NextResponse.json({ root, files })
}

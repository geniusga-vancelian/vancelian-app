/**
 * Liste l’arborescence du wiki Markdown assistance (fichiers .md sous la racine
 * configurée — par défaut `../api/services/assistance/data/wiki`).
 */
import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { listWikiTree, wikiRootExists } from '@/lib/admin/assistanceWikiFs'

export const dynamic = 'force-dynamic'

export async function GET() {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const exists = await wikiRootExists()
  if (!exists) {
    return NextResponse.json(
      {
        error: 'wiki_root_missing',
        root: null,
        nodes: [],
        message:
          'Dossier wiki introuvable. Définissez WIKI_MARKDOWN_ROOT ou clonez le dépôt avec api/services/assistance/data/wiki.',
      },
      { status: 503 }
    )
  }

  const { root, nodes } = await listWikiTree()
  return NextResponse.json({ root, nodes })
}

import { NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { EMAIL_COMPONENTS } from '@/lib/email/componentCatalog'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

/**
 * Liste tous les **composants MJML** disponibles avec leurs métadonnées :
 * - id (= clé Mustache : `{{> id}}`)
 * - kind (`section` | `inline`)
 * - description courte
 * - exemple de variables (pour la preview et la doc IA)
 */
export async function GET() {
  const session = await getSessionFromCookie()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  return NextResponse.json({ items: EMAIL_COMPONENTS })
}

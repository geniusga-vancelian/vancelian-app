/**
 * Proxy admin : `GET` détail d'une conversation IA.
 * Read-only. Cf. `services/assistance/admin_conversations_router.py`.
 */
import { NextRequest } from 'next/server'
import { forwardConversationsRequest } from '@/lib/assistance-conversations-proxy'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ conversationId: string }> },
) {
  const { conversationId } = await params
  return forwardConversationsRequest(`/${encodeURIComponent(conversationId)}`)
}

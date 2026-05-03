/** Proxy admin : compteurs par topic. */
import { forwardKnowledgeRequest } from '@/lib/assistance-knowledge-proxy'

export const dynamic = 'force-dynamic'

export async function GET() {
  return forwardKnowledgeRequest('/summary', 'GET')
}

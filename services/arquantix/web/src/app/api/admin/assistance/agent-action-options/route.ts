/**
 * Proxy admin : GET catalogue options agent ``action``.
 */
import { forwardAgentActionOptionsGet } from '@/lib/assistance-agent-action-options-proxy'

export const dynamic = 'force-dynamic'

export async function GET() {
  return forwardAgentActionOptionsGet()
}

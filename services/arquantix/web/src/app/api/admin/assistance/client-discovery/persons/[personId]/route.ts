/**
 * Proxy admin : `GET` snapshot courant des projets discovery + paramètres
 * flottants pour une personne (Cognitive Bot v4 — Lot 7).
 *
 * Read-only. Cf. `services/assistance/admin_client_discovery_router.py`.
 */
import { NextRequest } from 'next/server'
import { forwardClientDiscoveryRequest } from '@/lib/assistance-client-discovery-proxy'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ personId: string }> },
) {
  const { personId } = await params
  return forwardClientDiscoveryRequest(
    `/persons/${encodeURIComponent(personId)}`,
  )
}

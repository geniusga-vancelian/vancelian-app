import { NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const res = await portalUpstreamFetch('/api/app/profile', {
      signal: AbortSignal.timeout(15000),
    })
    // Session amont invalide → 401 pour laisser le client rediriger vers login.
    if (res.status === 401) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }
    const profile = await res.json().catch(() => null)
    if (!res.ok) {
      // Fail-soft : 200 + payload partiel pour ne pas masquer les sections indépendantes
      // (wallets, délégation, réseau) qui ne dépendent pas du profil.
      return NextResponse.json({ profile: null, partial: true })
    }
    return NextResponse.json({ profile })
  } catch (error) {
    console.error('[api/portal/profile GET]', error)
    return NextResponse.json({ profile: null, partial: true })
  }
}

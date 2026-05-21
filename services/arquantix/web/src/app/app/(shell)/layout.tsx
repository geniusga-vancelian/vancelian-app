import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { resolvePortalProfileInitials } from '@/lib/portal/resolveProfileInitials'
import { PortalShell } from '@/components/portal/PortalShell'
import { getSiteBrandLogo } from '@/lib/cms/site-footer'

async function readPortalInitials(): Promise<string | undefined> {
  const token = await readPortalAccessToken()
  if (!token) return undefined
  try {
    const res = await portalUpstreamFetch('/api/app/profile', {
      signal: AbortSignal.timeout(8000),
    })
    if (!res.ok) return undefined
    const profile = await res.json().catch(() => null)
    const initials = resolvePortalProfileInitials(profile)
    return initials || undefined
  } catch {
    return undefined
  }
}

export default async function PortalShellLayout({ children }: { children: React.ReactNode }) {
  const [initials, brand] = await Promise.all([readPortalInitials(), getSiteBrandLogo('fr')])
  return (
    <PortalShell initials={initials} brand={brand}>
      {children}
    </PortalShell>
  )
}

import type { PortalDashboardProfile } from '@/lib/portal/dashboardTypes'

export function resolvePortalProfileInitials(
  profile: PortalDashboardProfile | null | undefined,
): string {
  const fromProfile = profile?.initials?.trim()
  if (fromProfile) return fromProfile.slice(0, 2).toUpperCase()
  const first = profile?.personal?.first_name?.trim().charAt(0) ?? ''
  const last = profile?.personal?.last_name?.trim().charAt(0) ?? ''
  const combined = `${first}${last}`.toUpperCase()
  if (combined) return combined
  const email = profile?.email?.trim()
  if (email) return email.charAt(0).toUpperCase()
  return ''
}

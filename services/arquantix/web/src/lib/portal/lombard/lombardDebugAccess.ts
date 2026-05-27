import { prisma } from '@/lib/prisma'

/** Non-production runtime (local dev, staging builds with NODE_ENV != production). */
export function isLombardNonProductionRuntime(): boolean {
  return process.env.NODE_ENV !== 'production'
}

export async function isPortalPersonLinkedToAdmin(personId: string): Promise<boolean> {
  const person = await prisma.persons.findUnique({
    where: { id: personId },
    select: { adminUser: { select: { id: true } } },
  })
  return Boolean(person?.adminUser)
}

/** QA debug panel — visible in non-prod or for portal persons linked to an admin user. */
export async function canShowLombardDebugPanel(personId: string): Promise<boolean> {
  if (isLombardNonProductionRuntime()) return true
  if (process.env.LOMBARD_V1_DEBUG_PANEL_FOR_ADMINS === 'false') return false
  return isPortalPersonLinkedToAdmin(personId)
}

/** Client-side hint only — production admin visibility is confirmed via `/api/portal/lombard/qa-context`. */
export function isLombardDebugPanelClientHintVisible(): boolean {
  return process.env.NODE_ENV !== 'production'
}

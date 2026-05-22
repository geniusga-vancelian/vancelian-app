import { redirect } from 'next/navigation'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Racine portail : redirige vers login ou dashboard selon la session. */
export default function PortalRootPage() {
  redirect(PORTAL_ROUTES.login)
}

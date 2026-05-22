import { PortalAuthBootstrapShell } from '@/components/portal/PortalAuthBootstrapShell'
import { PortalAuthLoginSkeleton } from '@/components/portal/PortalAuthLoginSkeleton'

export default function PortalLoginLoading() {
  return (
    <PortalAuthBootstrapShell>
      <PortalAuthLoginSkeleton />
    </PortalAuthBootstrapShell>
  )
}

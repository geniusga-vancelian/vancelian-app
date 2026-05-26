import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export function bundleLockStatusLabel(status: string | undefined): string {
  switch (status) {
    case 'pending_signature':
      return 'Signature en attente…'
    case 'signature_requested':
      return 'Signature en attente…'
    case 'submitted':
      return 'Transaction en cours…'
    case 'pending_confirmation':
      return 'Transaction en cours…'
    case 'finalizing':
      return 'Finalisation…'
    case 'partial_pending':
      return 'Investissement en cours…'
    default:
      return 'Investissement en cours…'
  }
}

export function bundleExecutionPhaseLabel(phase: SwapExecutionPhase): string {
  switch (phase) {
    case 'preparing':
      return 'Investissement en cours…'
    case 'approving':
      return 'Investissement en cours…'
    case 'signing':
      return 'Signature en attente…'
    case 'submitting':
      return 'Transaction en cours…'
    case 'bridging':
      return 'Finalisation…'
    case 'completed':
      return 'Terminé'
    case 'failed':
      return 'Échec'
    default:
      return 'Investissement en cours…'
  }
}

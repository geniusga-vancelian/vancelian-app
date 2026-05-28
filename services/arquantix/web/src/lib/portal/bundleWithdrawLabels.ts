import type { BundleWithdrawDisplayPhase } from '@/lib/portal/bundleWithdrawFormat'

export function bundleWithdrawPhaseLabel(phase: BundleWithdrawDisplayPhase): string {
  switch (phase) {
    case 'WITHDRAW_REQUESTED':
      return 'Demande enregistrée'
    case 'UNWINDING':
      return 'Vente des actifs en cours…'
    case 'PARTIALLY_UNWOUND':
      return 'Débouclage partiel'
    case 'READY_TO_RELEASE':
      return 'Prêt à transférer vers Mon Trading'
    case 'RELEASED':
      return 'Transféré vers Mon Trading'
    case 'FAILED_PARTIAL':
      return 'Échec partiel — valeur restée dans le bundle'
    default:
      return 'Retrait en cours…'
  }
}

export function bundleWithdrawLockStatusLabel(status: string | undefined): string {
  switch (status) {
    case 'withdraw_requested':
      return 'Demande enregistrée'
    case 'unwinding':
    case 'pending_signature':
    case 'signature_requested':
      return 'Signature en attente…'
    case 'submitted':
    case 'pending_confirmation':
      return 'Confirmation on-chain…'
    case 'partially_unwound':
      return 'Débouclage partiel'
    case 'ready_to_release':
    case 'finalizing':
      return 'Transfert comptable…'
    case 'released':
      return 'Terminé'
    case 'failed_partial':
      return 'Échec partiel'
    default:
      return 'Retrait en cours…'
  }
}

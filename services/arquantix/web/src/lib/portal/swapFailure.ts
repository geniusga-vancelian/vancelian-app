import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  isPortalWalletRequestExpiredError,
  isPortalWalletUserRejectedError,
  isPortalWalletTransferFromFailedError,
} from '@/lib/wallet/portalWalletErrors'

export type SwapFailureCode =
  | 'user_rejected_signature'
  | 'user_rejected_approval'
  | 'user_abandoned'
  | 'wallet_error'
  | 'wallet_mismatch'
  | 'rpc_error'
  | 'lifi_error'
  | 'quote_expired'
  | 'insufficient_funds'
  | 'price_changed'
  | 'unknown_error'

export type SwapFailurePhase =
  | 'quote'
  | 'confirm_execute'
  | 'approval'
  | 'signing'
  | 'submitting'
  | 'polling'
  | 'settlement'

const USER_MESSAGES: Record<SwapFailureCode, string> = {
  user_rejected_signature: 'Signature refusée dans le wallet.',
  user_rejected_approval: 'Approbation refusée dans le wallet.',
  user_abandoned: 'Échange annulé.',
  wallet_error: 'Erreur wallet — réessayez ou reconnectez votre wallet.',
  wallet_mismatch:
    'Le wallet connecté ne correspond plus au devis — refaites une estimation.',
  rpc_error: 'Réseau blockchain indisponible — réessayez dans quelques instants.',
  lifi_error: "Route d'échange indisponible — refaites une estimation.",
  quote_expired: 'Devis expiré — refaites une estimation.',
  insufficient_funds: 'Solde insuffisant pour cet échange.',
  price_changed: 'Le prix a changé — vérifiez le récapitulatif.',
  unknown_error: 'Échange impossible — réessayez.',
}

export class SwapExecutionError extends Error {
  readonly code: SwapFailureCode
  readonly failurePhase: SwapFailurePhase
  readonly technicalMessage: string
  readonly userMessage: string

  constructor(params: {
    code: SwapFailureCode
    failurePhase: SwapFailurePhase
    technicalMessage: string
    userMessage?: string
  }) {
    super(params.userMessage ?? USER_MESSAGES[params.code])
    this.name = 'SwapExecutionError'
    this.code = params.code
    this.failurePhase = params.failurePhase
    this.technicalMessage = params.technicalMessage
    this.userMessage = params.userMessage ?? USER_MESSAGES[params.code]
  }
}

export function executionPhaseToFailurePhase(phase: SwapExecutionPhase): SwapFailurePhase {
  switch (phase) {
    case 'verifying_price':
    case 'preparing':
      return 'confirm_execute'
    case 'approving':
      return 'approval'
    case 'signing':
      return 'signing'
    case 'submitting':
      return 'submitting'
    case 'bridging':
      return 'polling'
    default:
      return 'quote'
  }
}

function messageOf(error: unknown): string {
  if (error instanceof Error) return error.message
  return String(error)
}

export function classifySwapError(
  error: unknown,
  failurePhase: SwapFailurePhase,
  context?: { approvalPhase?: boolean },
): SwapExecutionError {
  if (error instanceof SwapExecutionError) {
    return error
  }

  const technical = messageOf(error)
  const haystack = technical.toLowerCase()

  if (haystack.includes('wallet connecté ne correspond') || haystack.includes('wallet_mismatch')) {
    return new SwapExecutionError({
      code: 'wallet_mismatch',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (haystack.includes('quote expirée') || haystack.includes('swap.expired') || /quote expired/i.test(haystack)) {
    return new SwapExecutionError({
      code: 'quote_expired',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (haystack.includes('price_changed') || haystack.includes('légèrement changé')) {
    return new SwapExecutionError({
      code: 'price_changed',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (isPortalWalletUserRejectedError(error)) {
    const code: SwapFailureCode =
      context?.approvalPhase || failurePhase === 'approval'
        ? 'user_rejected_approval'
        : 'user_rejected_signature'
    return new SwapExecutionError({
      code,
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (isPortalWalletRequestExpiredError(error)) {
    return new SwapExecutionError({
      code: 'quote_expired',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (
    isPortalWalletTransferFromFailedError(error) ||
    haystack.includes('insuffisant') ||
    haystack.includes('insufficient')
  ) {
    return new SwapExecutionError({
      code: 'insufficient_funds',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (
    haystack.includes('fetch') ||
    haystack.includes('network') ||
    haystack.includes('timeout') ||
    haystack.includes('timed out') ||
    haystack.includes('signal timed out') ||
    haystack.includes('econnrefused')
  ) {
    return new SwapExecutionError({
      code: 'rpc_error',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (haystack.includes('lifi') || haystack.includes('route') || haystack.includes('502')) {
    return new SwapExecutionError({
      code: 'lifi_error',
      failurePhase,
      technicalMessage: technical,
    })
  }

  if (haystack.includes('wallet') || haystack.includes('privy') || haystack.includes('metamask')) {
    return new SwapExecutionError({
      code: 'wallet_error',
      failurePhase,
      technicalMessage: technical,
    })
  }

  return new SwapExecutionError({
    code: 'unknown_error',
    failurePhase,
    technicalMessage: technical,
  })
}

export function userMessageForSwapFailureCode(code: SwapFailureCode): string {
  return USER_MESSAGES[code]
}

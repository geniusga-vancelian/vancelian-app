import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'

const LOMBARD_CODE_MESSAGES: Record<string, string> = {
  'lombard.disabled': 'Produit temporairement indisponible.',
  'lombard.capacity_failed': 'Impossible de calculer la capacité d’emprunt. Réessayez.',
  'lombard.quote_failed': 'Impossible de calculer le devis. Réessayez.',
  'lombard.balance_changed':
    'Solde de garantie insuffisant. Actualisez le montant ou réessayez dans quelques secondes.',
  'lombard.base_rpc_busy': formatBaseRpcUserMessage(),
  unauthorized: 'Session expirée. Reconnectez-vous pour continuer.',
}

/** Erreurs API Lombard — ne pas réutiliser parsePortalExchangeError (auth OTP). */
export function parseLombardApiError(data: unknown, status: number): string {
  if (status === 401 || status === 403) {
    return LOMBARD_CODE_MESSAGES.unauthorized
  }

  if (data && typeof data === 'object') {
    const row = data as Record<string, unknown>
    const code = typeof row.code === 'string' ? row.code : undefined
    const message = typeof row.message === 'string' ? row.message : undefined
    const error = typeof row.error === 'string' ? row.error : undefined

    if (status === 400) {
      const issues = row.issues
      if (Array.isArray(issues)) {
        const first = issues[0]
        if (first && typeof first === 'object' && typeof (first as { message?: string }).message === 'string') {
          const issueMessage = (first as { message: string }).message.trim()
          if (issueMessage.toLowerCase().includes('borrow amount')) {
            return 'Montant emprunté invalide. Saisissez un nombre (ex. 1000 ou 1 000).'
          }
          return issueMessage
        }
      }
      if (error === 'Invalid request data') {
        return 'Requête invalide. Vérifiez le montant emprunté et réessayez.'
      }
    }

    if (code && LOMBARD_CODE_MESSAGES[code]) {
      return LOMBARD_CODE_MESSAGES[code]
    }
    if (message?.trim()) {
      if (isBaseRpcTransientError(message)) return formatBaseRpcUserMessage(message)
      return message.trim()
    }
    if (error === 'unauthorized') {
      return LOMBARD_CODE_MESSAGES.unauthorized
    }
    if (typeof row.detail === 'string' && row.detail.trim()) {
      return row.detail.trim()
    }
  }

  return 'Service temporairement indisponible. Réessayez dans quelques secondes.'
}

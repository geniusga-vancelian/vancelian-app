/** Chemins BFF / backend — réconciliation on-chain admin (Phase 5A–10). */

export const ONCHAIN_RECONCILIATION_BFF_BASE = '/api/admin/onchain-reconciliation'

export function buildDiscrepanciesListUrl(params: Record<string, string | undefined>): string {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== '') qs.set(key, value)
  }
  const query = qs.toString()
  return `${ONCHAIN_RECONCILIATION_BFF_BASE}/discrepancies${query ? `?${query}` : ''}`
}

export function discrepancyDetailUrl(id: string): string {
  return `${ONCHAIN_RECONCILIATION_BFF_BASE}/discrepancies/${id}`
}

export function discrepancyActionUrl(id: string, action: string): string {
  return `${ONCHAIN_RECONCILIATION_BFF_BASE}/discrepancies/${id}/${action}`
}

export function correctionActionUrl(correctionId: string, action: string): string {
  return `${ONCHAIN_RECONCILIATION_BFF_BASE}/corrections/${correctionId}/${action}`
}

export function buildExportCsvUrl(params: Record<string, string | undefined>): string {
  const qs = new URLSearchParams()
  qs.set('export_type', params.export_type || 'audit')
  for (const [key, value] of Object.entries(params)) {
    if (key === 'export_type' || value == null || value === '') continue
    qs.set(key, value)
  }
  return `${ONCHAIN_RECONCILIATION_BFF_BASE}/export.csv?${qs.toString()}`
}

export const PHASE_5A_DISCREPANCY_ACTIONS = [
  'acknowledge',
  'ignore',
  'resolve-manually',
  'preview-correction',
  'request-correction',
] as const

export type Phase5ADiscrepancyAction = (typeof PHASE_5A_DISCREPANCY_ACTIONS)[number]

export function isPhase5AAction(action: string): action is Phase5ADiscrepancyAction {
  return (PHASE_5A_DISCREPANCY_ACTIONS as readonly string[]).includes(action)
}

export const FORBIDDEN_UI_ACTIONS = ['apply', 'apply-correction', 'rebuild-balances'] as const

export function hasForbiddenApplyAction(actions: string[]): boolean {
  return actions.some((a) =>
    (FORBIDDEN_UI_ACTIONS as readonly string[]).includes(a as (typeof FORBIDDEN_UI_ACTIONS)[number]),
  )
}

export const APPLY_DISABLED_NO_RAW_MESSAGE =
  'Apply disabled: missing raw on-chain event proof'

export const APPLY_DEPOSIT_WARNING =
  'This will create a ledger deposit from a verified raw on-chain event'

export function severityBadgeClass(severity: string): string {
  switch (severity?.toUpperCase()) {
    case 'P0':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'P1':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'P2':
    default:
      return 'bg-amber-100 text-amber-900 border-amber-200'
  }
}

export function autoFixRiskBadgeClass(level: string): string {
  switch (level) {
    case 'safe_auto_link_possible':
      return 'bg-emerald-100 text-emerald-900 border-emerald-200'
    case 'potential_double_credit_risk':
      return 'bg-red-100 text-red-900 border-red-200'
    case 'manual_review_required':
    default:
      return 'bg-amber-100 text-amber-950 border-amber-200'
  }
}

export function statusBadgeClass(status: string): string {
  switch (status?.toLowerCase()) {
    case 'open':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'acknowledged':
      return 'bg-sky-100 text-sky-800 border-sky-200'
    case 'resolved':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'ignored':
      return 'bg-gray-100 text-gray-700 border-gray-200'
    default:
      return 'bg-slate-100 text-slate-800 border-slate-200'
  }
}

export function correctionStatusBadgeClass(status: string): string {
  switch (status?.toLowerCase()) {
    case 'approved':
      return 'bg-emerald-100 text-emerald-900 border-emerald-200'
    case 'requested':
      return 'bg-amber-100 text-amber-950 border-amber-200'
    case 'applied':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'rejected':
      return 'bg-red-100 text-red-900 border-red-200'
    default:
      return 'bg-slate-100 text-slate-800 border-slate-200'
  }
}

'use client'

import { AlertTriangle, CheckCircle2, Loader2, MinusCircle, XCircle } from 'lucide-react'

import { cn } from '@/lib/utils'

export type AdminProgressStepStatus = 'pending' | 'running' | 'success' | 'warning' | 'error'

export type AdminProgressStep = {
  id: string
  label: string
  detail?: string
  status: AdminProgressStepStatus
}

export type AdminOperationProgressModalProps = {
  open: boolean
  title: string
  subtitle?: string
  /** running = opération en cours (fermeture désactivée) */
  phase: 'running' | 'success' | 'error'
  steps: AdminProgressStep[]
  summaryLines: string[]
  errorMessage?: string
  /** Texte discret sous le résumé (ex. lien vers rapport existant sur la page) */
  footerHint?: string
  onClose: () => void
}

function StepIcon({ status }: { status: AdminProgressStepStatus }) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-indigo-600" aria-hidden />
    case 'success':
      return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
    case 'warning':
      return <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" aria-hidden />
    case 'error':
      return <XCircle className="h-4 w-4 shrink-0 text-red-600" aria-hidden />
    default:
      return <MinusCircle className="h-4 w-4 shrink-0 text-slate-300" aria-hidden />
  }
}

/**
 * Modale bloquante centrée pour opérations admin longues (analyse, correction, auto-trad…).
 * Fermeture désactivée tant que `phase === 'running'`.
 */
export function AdminOperationProgressModal({
  open,
  title,
  subtitle,
  phase,
  steps,
  summaryLines,
  errorMessage,
  footerHint,
  onClose,
}: AdminOperationProgressModalProps) {
  if (!open) return null

  const busy = phase === 'running'

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-op-progress-title"
      aria-busy={busy}
    >
      <div
        className="absolute inset-0 bg-black/55 backdrop-blur-[1px]"
        aria-hidden
      />
      <div
        className="relative z-10 flex max-h-[min(85vh,720px)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 id="admin-op-progress-title" className="text-base font-semibold text-slate-900">
            {title}
          </h2>
          {subtitle ? (
            <p className="mt-1 text-xs leading-snug text-slate-500">{subtitle}</p>
          ) : null}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {busy && steps.length === 0 ? (
            <div className="flex items-center gap-3 rounded-lg border border-indigo-100 bg-indigo-50/60 px-3 py-3 text-sm text-indigo-950">
              <Loader2 className="h-5 w-5 shrink-0 animate-spin text-indigo-600" aria-hidden />
              <span>Traitement en cours…</span>
            </div>
          ) : (
            <ul className="space-y-2">
              {steps.map((s) => (
                <li
                  key={s.id}
                  className={cn(
                    'flex gap-3 rounded-lg border px-3 py-2.5 text-left text-sm',
                    s.status === 'error' && 'border-red-200 bg-red-50/80',
                    s.status === 'warning' && 'border-amber-200 bg-amber-50/60',
                    s.status === 'success' && 'border-emerald-100 bg-emerald-50/40',
                    s.status === 'running' && 'border-indigo-200 bg-indigo-50/50',
                    s.status === 'pending' && 'border-slate-100 bg-slate-50/50 text-slate-500',
                  )}
                >
                  <span className="mt-0.5">
                    <StepIcon status={s.status} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="font-medium text-slate-900">{s.label}</span>
                    {s.detail ? (
                      <span className="mt-0.5 block text-xs text-slate-600 leading-snug">{s.detail}</span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {phase === 'error' && errorMessage ? (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
              {errorMessage}
            </div>
          ) : null}

          {(phase === 'success' || phase === 'error') && summaryLines.length > 0 ? (
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50/90 px-3 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Résumé
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-800">
                {summaryLines.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
              {footerHint ? (
                <p className="mt-3 text-[11px] leading-snug text-slate-500">{footerHint}</p>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-5 py-3">
          {busy ? (
            <p className="mr-auto text-[11px] text-slate-500">Ne fermez pas cette fenêtre.</p>
          ) : null}
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className={cn(
              'inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium',
              busy
                ? 'cursor-not-allowed bg-slate-100 text-slate-400'
                : 'bg-slate-900 text-white hover:bg-slate-800',
            )}
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  )
}

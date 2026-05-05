/**
 * Drawer latéral pour afficher le détail d'un tool call (audit Karpathy).
 *
 * Affiche : tool name, agent, autonomy, durée, error_code, arguments JSON,
 * result_summary JSON, reasoning summary, target ids, correlation id.
 * Read-only.
 */
'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X, AlertTriangle } from 'lucide-react'

export interface AgentDecision {
  id: string
  conversation_id: string
  message_id: string | null
  agent_id: string
  iteration: number
  tool_name: string
  autonomy_level: string
  arguments: Record<string, unknown>
  result_summary: Record<string, unknown> | null
  proposed_action: string | null
  target_client_id: string | null
  target_person_id: string | null
  reasoning_summary: string | null
  review_status: string
  duration_ms: number | null
  error_code: string | null
  correlation_id: string | null
  created_at: string | null
}

const AGENT_COLORS: Record<string, string> = {
  router: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  product: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  compliance: 'bg-amber-100 text-amber-700 border-amber-200',
  advisor: 'bg-violet-100 text-violet-700 border-violet-200',
  market: 'bg-cyan-100 text-cyan-700 border-cyan-200',
}

export function agentColor(agentId: string): string {
  return (
    AGENT_COLORS[agentId] ?? 'bg-slate-100 text-slate-700 border-slate-200'
  )
}

interface Props {
  decision: AgentDecision | null
  onClose: () => void
}

function formatJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function AssistanceToolCallDetailDrawer({ decision, onClose }: Props) {
  if (!decision) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden
      />
      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Détail tool call"
        className="fixed right-0 top-0 z-50 h-screen w-full sm:w-[640px] bg-white shadow-xl border-l border-slate-200 flex flex-col"
      >
        {/* Header */}
        <header className="border-b border-slate-200 bg-slate-50 px-5 py-4 flex items-start justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                variant="outline"
                className={`text-[10px] uppercase tracking-wide font-medium ${agentColor(decision.agent_id)}`}
              >
                {decision.agent_id}
              </Badge>
              <code className="text-sm font-semibold text-slate-800">
                {decision.tool_name}
              </code>
              <Badge
                variant="outline"
                className="text-[10px] font-normal text-slate-500"
              >
                {decision.autonomy_level}
              </Badge>
              {decision.error_code && (
                <Badge
                  variant="destructive"
                  className="text-[10px] font-normal bg-red-100 text-red-700 hover:bg-red-100 border-red-200"
                >
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  {decision.error_code}
                </Badge>
              )}
            </div>
            <div className="text-xs text-slate-500 flex items-center gap-3 flex-wrap">
              <span>iteration {decision.iteration}</span>
              {decision.duration_ms !== null && (
                <span>· {decision.duration_ms} ms</span>
              )}
              {decision.created_at && (
                <span>
                  ·{' '}
                  {new Date(decision.created_at).toLocaleString('fr-FR', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    fractionalSecondDigits: 3,
                  })}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Fermer</span>
          </Button>
        </header>

        {/* Body scrollable */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-sm">
          {/* Arguments */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
              Arguments
            </h3>
            <pre className="text-xs bg-slate-900 text-slate-100 rounded-md p-3 overflow-x-auto max-h-72">
              {formatJson(decision.arguments)}
            </pre>
          </section>

          {/* Result */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
              Résultat (summary)
            </h3>
            {decision.result_summary ? (
              <pre className="text-xs bg-slate-900 text-slate-100 rounded-md p-3 overflow-x-auto max-h-96">
                {formatJson(decision.result_summary)}
              </pre>
            ) : (
              <p className="text-xs text-slate-400 italic">
                Pas de résumé persisté pour cet appel.
              </p>
            )}
          </section>

          {/* Reasoning */}
          {decision.reasoning_summary && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
                Reasoning summary
              </h3>
              <p className="text-xs text-slate-700 bg-slate-50 border border-slate-100 rounded-md p-3 whitespace-pre-wrap">
                {decision.reasoning_summary}
              </p>
            </section>
          )}

          {/* Meta */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
              Métadonnées
            </h3>
            <dl className="text-xs grid grid-cols-3 gap-y-1.5 text-slate-600">
              <dt className="col-span-1 font-medium">Review status</dt>
              <dd className="col-span-2">{decision.review_status}</dd>

              {decision.proposed_action && (
                <>
                  <dt className="col-span-1 font-medium">Proposed action</dt>
                  <dd className="col-span-2">{decision.proposed_action}</dd>
                </>
              )}

              {decision.target_client_id && (
                <>
                  <dt className="col-span-1 font-medium">Target client</dt>
                  <dd className="col-span-2 font-mono text-[11px]">
                    {decision.target_client_id}
                  </dd>
                </>
              )}

              {decision.target_person_id && (
                <>
                  <dt className="col-span-1 font-medium">Target person</dt>
                  <dd className="col-span-2 font-mono text-[11px]">
                    {decision.target_person_id}
                  </dd>
                </>
              )}

              {decision.message_id && (
                <>
                  <dt className="col-span-1 font-medium">Message</dt>
                  <dd className="col-span-2 font-mono text-[11px]">
                    {decision.message_id}
                  </dd>
                </>
              )}

              {decision.correlation_id && (
                <>
                  <dt className="col-span-1 font-medium">Correlation</dt>
                  <dd className="col-span-2 font-mono text-[11px]">
                    {decision.correlation_id}
                  </dd>
                </>
              )}

              <dt className="col-span-1 font-medium">Decision id</dt>
              <dd className="col-span-2 font-mono text-[11px]">
                {decision.id}
              </dd>
            </dl>
          </section>
        </div>
      </aside>
    </>
  )
}

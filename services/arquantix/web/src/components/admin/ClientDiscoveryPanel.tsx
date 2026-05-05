/**
 * Panneau admin **Projets client / Goals** (Cognitive Bot v4 — Lot 7).
 *
 * Affiche l'**état COURANT** du discovery pour une personne donnée :
 *   * projets identifiés (achat maison, retraite, vacances…) avec
 *     statut (active / paused / completed / abandoned), confidence,
 *     paramètres adossés (horizon, montant initial, apport récurrent,
 *     appétit risque, …),
 *   * paramètres flottants en attente d'attribution à un projet.
 *
 * ⚠ État courant uniquement, pas de snapshot historique par tour. Pour
 * voir « ce que le bot a vu au tour N », l'admin doit s'appuyer sur le
 * diagramme de synthèse cognitive (champ
 * `arguments_json.client_discovery_block`, Lot 7 V1.2).
 *
 * Source : `GET /api/admin/assistance/client-discovery/persons/{personId}`.
 */
'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Loader2, Target, AlertCircle } from 'lucide-react'

// ─────────────────────────── Types ──────────────────────────────

interface DiscoveryProject {
  id: string
  label: string
  status: string
  confidence: number | null
  parameters: Record<string, unknown>
  notes: string | null
  conversation_id_source: string | null
  created_at_turn: number | null
  last_touched_at_turn: number | null
  created_at: string | null
  updated_at: string | null
}

interface FloatingParameter {
  id: string
  parameter_kind: string
  parameter_value: Record<string, unknown>
  status: string
  attributed_project_id: string | null
  conversation_id: string
  created_at_turn: number | null
  created_at: string | null
  resolved_at: string | null
}

interface ClientDiscoveryState {
  person_id: string
  projects: DiscoveryProject[]
  floating_parameters: FloatingParameter[]
  project_count_active: number
  project_count_total: number
  floating_count_pending: number
}

interface Props {
  personId: string
  /** Filtre optionnel : si fourni, met en évidence le projet originaire
   *  de cette conversation. Ne masque pas les autres. */
  highlightConversationId?: string
}

// ─────────────────────────── Helpers ──────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'paused':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'completed':
      return 'bg-cyan-50 text-cyan-700 border-cyan-200'
    case 'abandoned':
      return 'bg-slate-50 text-slate-600 border-slate-200'
    case 'pending_attribution':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'attributed':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'discarded':
      return 'bg-slate-50 text-slate-600 border-slate-200'
    default:
      return 'bg-slate-50 text-slate-700 border-slate-200'
  }
}

function formatConfidence(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(0)}%`
}

function formatParam(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  if (typeof value === 'number') return String(value)
  if (typeof value === 'boolean') return value ? 'oui' : 'non'
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

// ─────────────────────────── Sub-components ───────────────────────

function ProjectCard({
  project,
  highlighted,
}: {
  project: DiscoveryProject
  highlighted: boolean
}) {
  const paramKeys = Object.keys(project.parameters || {})
  return (
    <div
      className={`rounded-md border p-2.5 space-y-1.5 ${
        highlighted
          ? 'border-violet-300 bg-violet-50/40 ring-1 ring-violet-200'
          : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-sm font-semibold text-slate-800">
          {project.label}
        </span>
        <Badge
          variant="outline"
          className={`text-[10px] py-0 px-1.5 font-normal ${statusColor(project.status)}`}
        >
          {project.status}
        </Badge>
        {project.confidence !== null && (
          <span className="text-[10px] text-slate-500 font-mono">
            conf {formatConfidence(project.confidence)}
          </span>
        )}
        {project.created_at_turn !== null && (
          <span className="text-[10px] text-slate-400">
            créé T{project.created_at_turn}
          </span>
        )}
        {project.last_touched_at_turn !== null &&
          project.last_touched_at_turn !== project.created_at_turn && (
            <span className="text-[10px] text-slate-400">
              maj T{project.last_touched_at_turn}
            </span>
          )}
      </div>

      {paramKeys.length > 0 && (
        <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[11px]">
          {paramKeys.slice(0, 8).map((k) => (
            <div key={k} className="flex items-baseline gap-1.5">
              <span className="text-slate-500 font-medium">{k}:</span>
              <span className="text-slate-800 font-mono truncate">
                {formatParam(project.parameters[k])}
              </span>
            </div>
          ))}
          {paramKeys.length > 8 && (
            <span className="col-span-2 text-[10px] text-slate-400">
              +{paramKeys.length - 8} autre{paramKeys.length - 8 > 1 ? 's' : ''} param
            </span>
          )}
        </div>
      )}

      {project.notes && (
        <p className="text-[11px] text-slate-600 italic">« {project.notes} »</p>
      )}
    </div>
  )
}

function FloatingParameterCard({ param }: { param: FloatingParameter }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50/30 p-2 text-[11px] space-y-0.5">
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="font-semibold text-slate-800">
          {param.parameter_kind}
        </span>
        <Badge
          variant="outline"
          className={`text-[10px] py-0 px-1.5 font-normal ${statusColor(param.status)}`}
        >
          {param.status}
        </Badge>
        {param.created_at_turn !== null && (
          <span className="text-[10px] text-slate-400">
            T{param.created_at_turn}
          </span>
        )}
      </div>
      <div className="text-slate-700 font-mono break-all">
        {formatParam(param.parameter_value)}
      </div>
    </div>
  )
}

// ─────────────────────────── Main component ──────────────────────

export function ClientDiscoveryPanel({
  personId,
  highlightConversationId,
}: Props) {
  const [state, setState] = useState<ClientDiscoveryState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!personId) return
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    fetch(
      `/api/admin/assistance/client-discovery/persons/${encodeURIComponent(
        personId,
      )}`,
      { cache: 'no-store', signal: ctrl.signal },
    )
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return (await r.json()) as ClientDiscoveryState
      })
      .then((data) => {
        setState(data)
        setLoading(false)
      })
      .catch((err: unknown) => {
        if ((err as Error).name === 'AbortError') return
        setError(err instanceof Error ? err.message : 'Erreur inconnue')
        setLoading(false)
      })
    return () => ctrl.abort()
  }, [personId])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-500 p-2">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Chargement des projets…</span>
      </div>
    )
  }
  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-red-600 p-2">
        <AlertCircle className="h-3 w-3" />
        <span>Erreur : {error}</span>
      </div>
    )
  }
  if (!state) return null

  const hasAny =
    state.projects.length > 0 || state.floating_parameters.length > 0
  if (!hasAny) {
    return (
      <p className="text-xs text-slate-400 p-2 italic">
        Aucun projet client identifié pour cette personne (bot
        n&apos;a encore extrait aucun goal).
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-slate-500 font-medium px-1">
        <Target className="h-3 w-3 text-violet-500" />
        <span>
          {state.project_count_active}/{state.project_count_total} projets actifs
          · {state.floating_count_pending} param. en attente
        </span>
      </div>

      {state.projects.length > 0 && (
        <div className="space-y-1.5">
          {state.projects.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              highlighted={
                Boolean(highlightConversationId) &&
                p.conversation_id_source === highlightConversationId
              }
            />
          ))}
        </div>
      )}

      {state.floating_parameters.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wide text-slate-500 font-medium px-1">
            Paramètres flottants ({state.floating_parameters.length})
          </p>
          {state.floating_parameters.slice(0, 8).map((f) => (
            <FloatingParameterCard key={f.id} param={f} />
          ))}
          {state.floating_parameters.length > 8 && (
            <p className="text-[10px] text-slate-400 px-1">
              +{state.floating_parameters.length - 8} autre
              {state.floating_parameters.length - 8 > 1 ? 's' : ''}
            </p>
          )}
        </div>
      )}

      <p className="text-[10px] text-slate-400 italic px-1 pt-1 border-t border-slate-100">
        ⚠ État courant (pas de snapshot par tour). Pour l&apos;historique,
        voir le bloc <code className="text-slate-500">CLIENT DISCOVERY</code>{' '}
        dans le diagramme de synthèse.
      </p>
    </div>
  )
}

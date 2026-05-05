/**
 * Page **détail d'une conversation IA** (admin monitoring v1).
 *
 * Route : `/admin/customers/[personId]/assistance/conversations/[conversationId]`
 *
 * Layout 4 colonnes (depuis 2026-05-05, Lot 7 V1.1) :
 *   1. Timeline (gauche)        — 1 ligne / turn, filtres, sélection synchro.
 *   2. Chat (centre-gauche)     — exactement ce que voit le client (rôles + embeds).
 *   3. Synthèse cognitive       — Cognitive Bot v4 : input + cognitive_state
 *      (intention user) + objective (objectif réponse bot) + router decision
 *      + agent_chain. Sections vides masquées (best-effort).
 *   4. Workflow trace (droite)  — pour le turn sélectionné, arbre des tool
 *      calls avec durée, erreurs, lien drawer détail.
 *
 * Read-only. Snapshot à l'ouverture + bouton refresh + export JSON debug.
 * Cf. `services/assistance/admin_conversations_router.py`.
 */
'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ArrowLeft,
  Download,
  RefreshCw,
  AlertTriangle,
  User,
  Bot,
  Wrench,
  Box,
  ChevronRight,
} from 'lucide-react'
import {
  AssistanceToolCallDetailDrawer,
  agentColor,
  type AgentDecision,
} from '@/components/admin/AssistanceToolCallDetailDrawer'
import { CognitiveTurnDiagram } from '@/components/admin/CognitiveTurnDiagram'
import { ClientDiscoveryPanel } from '@/components/admin/ClientDiscoveryPanel'

// ────────────────────────── Types ──────────────────────────

interface CurrentTopic {
  kind?: string
  product_code?: string
  agent_owner?: string
  [key: string]: unknown
}

interface MessageRead {
  id: string
  turn_index: number
  role: 'user' | 'assistant' | string
  content: string
  agent_used: string | null
  message_type: string
  message_payload: Record<string, unknown> | null
  created_at: string | null
}

interface ConversationDetail {
  id: string
  client_id: string
  title: string | null
  status: string
  created_at: string | null
  updated_at: string | null
  last_message_at: string | null
  last_assistant_message_at: string | null
  last_read_at: string | null
  conversation_summary: string | null
  conversation_facts: Array<Record<string, unknown>>
  summarized_until_turn: number | null
  summary_updated_at: string | null
  current_topic: CurrentTopic | null
  messages: MessageRead[]
  message_count: number
  tool_call_count: number
  tool_error_count: number
}

interface DecisionsResponse {
  decisions: AgentDecision[]
  total: number
}

interface TimelineFilters {
  showUser: boolean
  showAssistant: boolean
  showTools: boolean
  errorsOnly: boolean
}

// ────────────────────────── Helpers ──────────────────────────

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function renderTopic(topic: CurrentTopic | null): string | null {
  if (!topic) return null
  const parts: string[] = []
  if (topic.kind) parts.push(String(topic.kind))
  if (topic.product_code) parts.push(String(topic.product_code))
  if (topic.agent_owner) parts.push(`@${topic.agent_owner}`)
  return parts.length > 0 ? parts.join(' / ') : null
}

/**
 * Groupe les decisions par message_id quand renseigné, sinon par
 * proximité au turn assistant suivant. Hot path : on parcourt les
 * messages assistant ordonnés par turn_index, et on associe les
 * decisions dont l'iteration est `<` celle du prochain assistant.
 *
 * Heuristique pragmatique : la persistance actuelle ne lie pas
 * toujours `message_id` à toutes les decisions (un tool call qui
 * échoue ou qui est un dedup hit n'a pas de message_id). On
 * regroupe donc par fenêtres d'iteration, ancrées sur les turns
 * assistant consécutifs.
 */
function groupDecisionsByTurn(
  messages: MessageRead[],
  decisions: AgentDecision[],
): Map<number, AgentDecision[]> {
  const map = new Map<number, AgentDecision[]>()

  // Cas simple : message_id fourni → on retrouve le turn directement.
  const byMessageId = new Map<string, MessageRead>()
  for (const m of messages) byMessageId.set(m.id, m)

  const unassigned: AgentDecision[] = []
  for (const d of decisions) {
    if (d.message_id && byMessageId.has(d.message_id)) {
      const turn = byMessageId.get(d.message_id)!.turn_index
      if (!map.has(turn)) map.set(turn, [])
      map.get(turn)!.push(d)
    } else {
      unassigned.push(d)
    }
  }

  // Cas où message_id est absent → on rattache par contiguïté à
  // l'assistant le plus proche par ordre d'iteration croissante.
  if (unassigned.length > 0) {
    const assistantTurns = messages
      .filter((m) => m.role === 'assistant')
      .map((m) => m.turn_index)
      .sort((a, b) => a - b)

    for (const d of unassigned) {
      // On choisit le turn assistant le plus proche en après — le
      // tool call précède toujours la réponse assistant qu'il génère.
      let target = assistantTurns[0]
      for (const t of assistantTurns) {
        target = t
        if (t >= d.iteration) break
      }
      const key = target ?? -1
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(d)
    }
  }

  // Tri des decisions de chaque turn par iteration croissante.
  for (const arr of map.values()) {
    arr.sort((a, b) => a.iteration - b.iteration)
  }

  return map
}

// ────────────────────────── Page ──────────────────────────

export default function ConversationDetailPage() {
  const router = useRouter()
  const params = useParams()
  const personId = (params?.personId as string | undefined) ?? ''
  const conversationId = (params?.conversationId as string | undefined) ?? ''

  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [decisions, setDecisions] = useState<AgentDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTurn, setSelectedTurn] = useState<number | null>(null)
  const [drawerDecision, setDrawerDecision] = useState<AgentDecision | null>(
    null,
  )
  const [filters, setFilters] = useState<TimelineFilters>({
    showUser: true,
    showAssistant: true,
    showTools: true,
    errorsOnly: false,
  })

  const load = useCallback(async () => {
    if (!conversationId) return
    setLoading(true)
    setError(null)
    try {
      const [detailRes, decisionsRes] = await Promise.all([
        fetch(
          `/api/admin/assistance/conversations/${encodeURIComponent(
            conversationId,
          )}`,
          { cache: 'no-store' },
        ),
        fetch(
          `/api/admin/assistance/conversations/${encodeURIComponent(
            conversationId,
          )}/decisions`,
          { cache: 'no-store' },
        ),
      ])
      if (!detailRes.ok) throw new Error(`detail HTTP ${detailRes.status}`)
      if (!decisionsRes.ok)
        throw new Error(`decisions HTTP ${decisionsRes.status}`)
      const detailJson = (await detailRes.json()) as ConversationDetail
      const decisionsJson = (await decisionsRes.json()) as DecisionsResponse
      setDetail(detailJson)
      setDecisions(decisionsJson.decisions || [])
      // Sélection initiale = dernier turn (les plus récents en bas).
      const lastTurn = detailJson.messages.at(-1)?.turn_index
      setSelectedTurn(lastTurn ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  useEffect(() => {
    void load()
  }, [load])

  const decisionsByTurn = useMemo<Map<number, AgentDecision[]>>(
    () =>
      detail
        ? groupDecisionsByTurn(detail.messages, decisions)
        : new Map<number, AgentDecision[]>(),
    [detail, decisions],
  )

  const filteredMessages = useMemo(() => {
    if (!detail) return []
    return detail.messages.filter((m) => {
      if (m.role === 'user' && !filters.showUser) return false
      if (m.role === 'assistant' && !filters.showAssistant) return false
      return true
    })
  }, [detail, filters])

  const onExport = () => {
    if (!detail) return
    const payload = {
      conversation: detail,
      decisions,
      exported_at: new Date().toISOString(),
      exported_for_admin_monitoring: true,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `assistance-conversation-${conversationId.slice(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ────────────────────────── Render ──────────────────────────

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            router.push(
              `/admin/customers/${encodeURIComponent(personId)}/assistance/conversations`,
            )
          }
        >
          <ArrowLeft className="h-4 w-4 mr-1" /> Retour liste
        </Button>
        <div className="mt-4 flex items-center gap-2 text-red-600">
          <AlertTriangle className="h-4 w-4" />
          <span>Erreur de chargement : {error}</span>
        </div>
      </div>
    )
  }

  if (loading || !detail) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <p className="text-xs text-slate-500">Chargement…</p>
      </div>
    )
  }

  const topic = renderTopic(detail.current_topic)

  return (
    <div className="space-y-3 p-4 lg:p-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              router.push(
                `/admin/customers/${encodeURIComponent(personId)}/assistance/conversations`,
              )
            }
          >
            <ArrowLeft className="h-4 w-4 mr-1" /> Retour
          </Button>
          <h1 className="text-base font-semibold text-slate-900">
            {detail.title || 'Conversation sans titre'}
          </h1>
          <Badge
            variant="outline"
            className="text-[10px] uppercase tracking-wide font-normal"
          >
            {detail.status}
          </Badge>
          <Badge variant="secondary" className="text-[10px] font-normal">
            {detail.message_count} turns · {detail.tool_call_count} tools
          </Badge>
          {detail.tool_error_count > 0 && (
            <Badge
              variant="destructive"
              className="text-[10px] font-normal bg-red-100 text-red-700 hover:bg-red-100"
            >
              <AlertTriangle className="h-3 w-3 mr-1" />
              {detail.tool_error_count} err
            </Badge>
          )}
          {topic && (
            <Badge
              variant="secondary"
              className="text-[10px] font-normal bg-indigo-50 text-indigo-700 hover:bg-indigo-50"
            >
              {topic}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onExport}>
            <Download className="h-4 w-4 mr-1.5" /> Export JSON
          </Button>
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Meta */}
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="py-3 text-xs text-slate-600 grid grid-cols-2 lg:grid-cols-4 gap-2">
          <span>Créée : {formatDateTime(detail.created_at)}</span>
          <span>Dernier message : {formatDateTime(detail.last_message_at)}</span>
          {detail.summarized_until_turn !== null && (
            <span>Summary jusqu&apos;au turn {detail.summarized_until_turn}</span>
          )}
          {detail.conversation_facts.length > 0 && (
            <span>{detail.conversation_facts.length} fact(s) mémorisé(s)</span>
          )}
        </CardContent>
      </Card>

      {/* 4 colonnes (3+4+3+2 = 12) */}
      <div className="grid grid-cols-12 gap-3 min-h-[60vh]">
        {/* TIMELINE */}
        <Card className="col-span-12 lg:col-span-3 border-slate-200 shadow-sm flex flex-col max-h-[80vh]">
          <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-wide text-slate-800 uppercase">
              Timeline
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2 overflow-y-auto flex-1 space-y-1">
            {/* Filtres */}
            <div className="flex flex-wrap gap-1.5 px-1 py-2 border-b border-slate-100 mb-1">
              {(
                [
                  ['showUser', 'user'],
                  ['showAssistant', 'assistant'],
                ] as const
              ).map(([k, label]) => (
                <Badge
                  key={k}
                  variant={filters[k] ? 'default' : 'outline'}
                  onClick={() =>
                    setFilters((f) => ({ ...f, [k]: !f[k] }))
                  }
                  className="cursor-pointer text-[10px] font-normal"
                >
                  {label}
                </Badge>
              ))}
            </div>
            {/* Liste */}
            {detail.messages.map((m) => {
              const decisionsForTurn =
                decisionsByTurn.get(m.turn_index) ?? []
              const errorCount = decisionsForTurn.filter(
                (d) => d.error_code,
              ).length
              const isSelected = selectedTurn === m.turn_index
              const visible =
                (m.role === 'user' && filters.showUser) ||
                (m.role === 'assistant' && filters.showAssistant)
              if (!visible) return null
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setSelectedTurn(m.turn_index)}
                  className={`w-full text-left px-2 py-1.5 rounded-md border transition-colors ${
                    isSelected
                      ? 'bg-indigo-50 border-indigo-300'
                      : 'border-transparent hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2 text-[11px] font-medium">
                    <span className="text-slate-400 font-mono">
                      T{m.turn_index}
                    </span>
                    {m.role === 'user' ? (
                      <User className="h-3 w-3 text-slate-500" />
                    ) : (
                      <Bot className="h-3 w-3 text-slate-500" />
                    )}
                    <span className="text-slate-700">{m.role}</span>
                    {m.agent_used && (
                      <Badge
                        variant="outline"
                        className={`text-[9px] py-0 px-1 ${agentColor(
                          m.agent_used,
                        )}`}
                      >
                        {m.agent_used}
                      </Badge>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                    {m.content || '(empty)'}
                  </p>
                  {decisionsForTurn.length > 0 && (
                    <div className="mt-1 flex items-center gap-1.5 text-[10px]">
                      <Wrench className="h-3 w-3 text-slate-400" />
                      <span className="text-slate-500">
                        {decisionsForTurn.length} tool
                        {decisionsForTurn.length > 1 ? 's' : ''}
                      </span>
                      {errorCount > 0 && (
                        <span className="text-red-600 font-medium">
                          · {errorCount} err
                        </span>
                      )}
                    </div>
                  )}
                </button>
              )
            })}
          </CardContent>
        </Card>

        {/* CHAT */}
        <Card className="col-span-12 lg:col-span-4 border-slate-200 shadow-sm flex flex-col max-h-[80vh]">
          <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-wide text-slate-800 uppercase flex items-center justify-between">
              <span>Conversation</span>
              <span className="text-[9px] text-slate-400 font-normal normal-case tracking-normal">
                clic = sélection
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 overflow-y-auto flex-1 space-y-3">
            {filteredMessages.map((m) => {
              const isSelected = selectedTurn === m.turn_index
              return (
                <article
                  key={m.id}
                  id={`turn-${m.turn_index}`}
                  onClick={() => setSelectedTurn(m.turn_index)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelectedTurn(m.turn_index)
                    }
                  }}
                  aria-pressed={isSelected}
                  className={`rounded-lg p-3 border transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-300 ${
                    m.role === 'user'
                      ? 'bg-slate-50 border-slate-200 ml-0 mr-6 hover:bg-slate-100'
                      : 'bg-white border-slate-100 ml-6 mr-0 hover:bg-slate-50'
                  } ${isSelected ? 'ring-2 ring-indigo-300' : ''}`}
                >
                  <header className="flex items-center gap-2 text-[11px] text-slate-500 mb-1">
                    {m.role === 'user' ? (
                      <User className="h-3 w-3" />
                    ) : (
                      <Bot className="h-3 w-3" />
                    )}
                    <span className="font-semibold uppercase tracking-wide">
                      {m.role}
                    </span>
                    {m.agent_used && (
                      <Badge
                        variant="outline"
                        className={`text-[9px] py-0 px-1.5 ${agentColor(
                          m.agent_used,
                        )}`}
                      >
                        {m.agent_used}
                      </Badge>
                    )}
                    <span>·</span>
                    <span>T{m.turn_index}</span>
                    <span>· {formatTime(m.created_at)}</span>
                    {m.message_type !== 'text' && (
                      <Badge
                        variant="secondary"
                        className="text-[9px] py-0 px-1.5"
                      >
                        {m.message_type}
                      </Badge>
                    )}
                  </header>
                  <div className="text-sm text-slate-800 whitespace-pre-wrap break-words">
                    {m.content || (
                      <span className="text-slate-400 italic">
                        (contenu vide)
                      </span>
                    )}
                  </div>
                  {m.message_payload &&
                    Object.keys(m.message_payload).length > 0 && (
                      <details
                        className="mt-2 text-xs text-slate-600"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <summary className="cursor-pointer flex items-center gap-1.5 hover:text-slate-800">
                          <Box className="h-3 w-3" />
                          UI payload (
                          {(m.message_payload as { kind?: string }).kind ??
                            'embed'}
                          )
                        </summary>
                        <pre className="mt-1.5 text-[11px] bg-slate-900 text-slate-100 rounded p-2 overflow-x-auto max-h-48">
                          {JSON.stringify(m.message_payload, null, 2)}
                        </pre>
                      </details>
                    )}
                </article>
              )
            })}
          </CardContent>
        </Card>

        {/* SYNTHÈSE COGNITIVE — Cognitive Bot v4, Lot 7 V1.1 (2026-05-05) */}
        <Card className="col-span-12 lg:col-span-3 border-slate-200 shadow-sm flex flex-col max-h-[80vh]">
          <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-wide text-slate-800 uppercase">
              Synthèse cognitive
              {selectedTurn !== null && (
                <span className="ml-2 text-slate-500 font-normal normal-case">
                  · turn {selectedTurn}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2 overflow-y-auto flex-1 space-y-3">
            <CognitiveTurnDiagram
              selectedTurn={selectedTurn}
              messages={detail.messages}
              decisions={decisions}
              context={{
                conversation_summary: detail.conversation_summary,
                summarized_until_turn: detail.summarized_until_turn,
                total_messages: detail.message_count,
              }}
            />

            {/* Lot 7 — Projets client / goals (état courant cross-conv) */}
            <div className="border-t border-slate-100 pt-3 mt-3">
              <p className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold px-1 mb-1.5">
                Projets client (Lot 7)
              </p>
              {personId ? (
                <ClientDiscoveryPanel
                  personId={personId}
                  highlightConversationId={conversationId}
                />
              ) : (
                <p className="text-xs text-slate-400 p-1 italic">
                  person_id manquant.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* WORKFLOW TRACE */}
        <Card className="col-span-12 lg:col-span-2 border-slate-200 shadow-sm flex flex-col max-h-[80vh]">
          <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-wide text-slate-800 uppercase">
              Workflow trace
              {selectedTurn !== null && (
                <span className="ml-2 text-slate-500 font-normal normal-case">
                  · turn {selectedTurn}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2 overflow-y-auto flex-1">
            {selectedTurn === null ? (
              <p className="text-xs text-slate-400 p-2">
                Sélectionne un turn dans la timeline pour voir l&apos;arbre des
                décisions.
              </p>
            ) : (
              <WorkflowTraceForTurn
                turnDecisions={decisionsByTurn.get(selectedTurn) ?? []}
                onPickDecision={setDrawerDecision}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer mémoire / facts */}
      {(detail.conversation_summary ||
        detail.conversation_facts.length > 0) && (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-wide text-slate-800 uppercase">
              Mémoire & facts
            </CardTitle>
          </CardHeader>
          <CardContent className="py-3 space-y-3 text-sm">
            {detail.conversation_summary && (
              <div>
                <p className="text-[11px] font-semibold uppercase text-slate-500 mb-1">
                  Summary{' '}
                  {detail.summarized_until_turn !== null
                    ? `(jusqu'au turn ${detail.summarized_until_turn})`
                    : ''}
                </p>
                <p className="text-sm text-slate-700 bg-slate-50 border border-slate-100 rounded-md p-3 whitespace-pre-wrap">
                  {detail.conversation_summary}
                </p>
              </div>
            )}
            {detail.conversation_facts.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold uppercase text-slate-500 mb-1">
                  Facts ({detail.conversation_facts.length})
                </p>
                <pre className="text-[11px] bg-slate-900 text-slate-100 rounded p-3 overflow-x-auto max-h-48">
                  {JSON.stringify(detail.conversation_facts, null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Drawer détail tool call */}
      <AssistanceToolCallDetailDrawer
        decision={drawerDecision}
        onClose={() => setDrawerDecision(null)}
      />
    </div>
  )
}

// ────────────────────────── Sub-components ──────────────────────────

function WorkflowTraceForTurn({
  turnDecisions,
  onPickDecision,
}: {
  turnDecisions: AgentDecision[]
  onPickDecision: (d: AgentDecision) => void
}) {
  if (turnDecisions.length === 0) {
    return (
      <p className="text-xs text-slate-400 p-2">
        Aucun tool call enregistré pour ce turn.
      </p>
    )
  }
  // Groupe par agent_id pour rendu en arbre.
  const byAgent = new Map<string, AgentDecision[]>()
  for (const d of turnDecisions) {
    if (!byAgent.has(d.agent_id)) byAgent.set(d.agent_id, [])
    byAgent.get(d.agent_id)!.push(d)
  }
  return (
    <ul className="space-y-2 text-xs">
      {Array.from(byAgent.entries()).map(([agentId, list]) => (
        <li
          key={agentId}
          className="border border-slate-100 rounded-md overflow-hidden"
        >
          <div
            className={`px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide border-b border-slate-100 ${agentColor(
              agentId,
            )}`}
          >
            {agentId}
            <span className="ml-1.5 font-normal normal-case opacity-75">
              · {list.length} call{list.length > 1 ? 's' : ''}
            </span>
          </div>
          <ul>
            {list.map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => onPickDecision(d)}
                  className="w-full text-left px-2.5 py-2 hover:bg-slate-50 flex items-start gap-2 border-b border-slate-50 last:border-0"
                >
                  <span className="text-slate-400 font-mono text-[10px] mt-0.5 flex-shrink-0">
                    #{d.iteration}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-800 font-medium truncate flex items-center gap-1.5">
                      <Wrench className="h-3 w-3 text-slate-400 flex-shrink-0" />
                      {d.tool_name}
                      <Badge
                        variant="outline"
                        className="text-[9px] py-0 px-1 font-normal text-slate-500"
                      >
                        {d.autonomy_level}
                      </Badge>
                      {d.error_code && (
                        <Badge
                          variant="destructive"
                          className="text-[9px] py-0 px-1 bg-red-100 text-red-700 hover:bg-red-100"
                        >
                          err
                        </Badge>
                      )}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5 truncate">
                      {d.duration_ms !== null && <>{d.duration_ms} ms · </>}
                      {Object.keys(d.arguments).length > 0 && (
                        <>
                          args:{' '}
                          {Object.keys(d.arguments).slice(0, 3).join(', ')}
                          {Object.keys(d.arguments).length > 3 && '…'}
                        </>
                      )}
                    </p>
                  </div>
                  <ChevronRight className="h-3 w-3 text-slate-400 mt-1 flex-shrink-0" />
                </button>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}

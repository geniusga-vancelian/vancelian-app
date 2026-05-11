/**
 * Page **détail d'une conversation IA** (admin monitoring v1).
 *
 * Route : `/admin/customers/[personId]/assistance/conversations/[conversationId]`
 *
 * Layout 4 colonnes (depuis 2026-05-05, Lot 7 V1.1) :
 *   1. Timeline (gauche)        — 1 ligne / turn, badge policy PR3 si gap.
 *   2. Chat (centre-gauche)     — exactement ce que voit le client ;
 *      badges routage cognitif (agent · intention · objectif) au-dessus
 *      des bulles assistant ; payload UI + metadata en repliables.
 *   3. Synthèse cognitive       — Cognitive Bot + **orchestration** + **conversation_state**
 *      (persistés router) + **policy data need** (PR3) + Wiki + client discovery.
 *   4. Workflow trace (droite)  — outils du tour ; lignes policy en surbrillance.
 *
 * Bandeau : IDs conv/client, dates lifecycle, current_topic JSON, liens Observabilité / Funnel.
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
  BookMarked,
  ExternalLink,
  Eye,
  LineChart,
  BarChart3,
} from 'lucide-react'
import {
  AssistanceToolCallDetailDrawer,
  agentColor,
  type AgentDecision,
} from '@/components/admin/AssistanceToolCallDetailDrawer'
import { AssistanceMessageRoutingTags } from '@/components/admin/AssistanceMessageRoutingTags'
import { CognitiveTurnDiagram } from '@/components/admin/CognitiveTurnDiagram'
import { ClientDiscoveryPanel } from '@/components/admin/ClientDiscoveryPanel'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  adminWikiEditorUrl,
  extractWikiRefsFromDecisions,
  extractWikiPreloadFromAssistantPayload,
  type WikiPipelinePreloadRef,
  type WikiRefsForTurn,
} from '@/lib/admin/assistanceWikiRefs'
import { extractAssistantRoutingTags } from '@/lib/admin/assistanceAssistantTags'
import remarkGfm from 'remark-gfm'
import ReactMarkdown from 'react-markdown'

// ────────────────────────── Types ──────────────────────────

interface CurrentTopic {
  kind?: string
  product_code?: string
  agent_owner?: string
  [key: string]: unknown
}

interface WikiMarkdownPreviewSelection {
  path: string
  title: string
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

/** Parse ISO admin → ms ; null si invalide (aligné sur CognitiveTurnDiagram). */
function parseIsoMsAdmin(iso: string | null | undefined): number | null {
  if (!iso) return null
  const n = Date.parse(iso)
  return Number.isNaN(n) ? null : n
}

/**
 * Groupe les decisions par `message_id` quand renseigné, sinon par
 * **fenêtre temporelle** entre le message précédent et le message
 * assistant du tour (les tool calls du runtime sont persistés sans
 * `message_id` — cf. `agent_loop.persist_decision`).
 *
 * L’ancienne heuristique qui comparait `iteration` du LLM aux
 * `turn_index` des messages était **fausse** (scopes d’iteration
 * différents) : tous les tours après le premier retombaient sur le
 * mauvais assistant dans la timeline / workflow trace.
 */
function groupDecisionsByTurn(
  messages: MessageRead[],
  decisions: AgentDecision[],
): Map<number, AgentDecision[]> {
  const map = new Map<number, AgentDecision[]>()

  const byMessageId = new Map<string, MessageRead>()
  for (const m of messages) byMessageId.set(m.id, m)

  const sortedMsgs = [...messages].sort((a, b) => a.turn_index - b.turn_index)

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

  let lastAssistantTurn: number | null = null
  for (const m of sortedMsgs) {
    if (m.role === 'assistant') lastAssistantTurn = m.turn_index
  }

  for (const d of unassigned) {
    const td = parseIsoMsAdmin(d.created_at)
    let targetTurn: number | null = null

    if (td !== null) {
      for (let i = 0; i < sortedMsgs.length; i++) {
        const m = sortedMsgs[i]
        if (m.role !== 'assistant') continue
        const prev = sortedMsgs[i - 1]
        if (!prev) continue
        const tPrev = parseIsoMsAdmin(prev.created_at)
        const tAsst = parseIsoMsAdmin(m.created_at)
        if (tPrev === null || tAsst === null) continue
        if (td >= tPrev && td <= tAsst) {
          targetTurn = m.turn_index
          break
        }
      }
    }

    if (targetTurn === null && lastAssistantTurn !== null) {
      targetTurn = lastAssistantTurn
    }
    if (targetTurn === null) {
      targetTurn = -1
    }
    if (!map.has(targetTurn)) map.set(targetTurn, [])
    map.get(targetTurn)!.push(d)
  }

  for (const arr of map.values()) {
    arr.sort(
      (a, b) =>
        a.iteration - b.iteration ||
        (parseIsoMsAdmin(a.created_at) ?? 0) -
          (parseIsoMsAdmin(b.created_at) ?? 0),
    )
  }

  return map
}

/**
 * Turn assistant associé à la sélection timeline (un clic user emporte
 * la réponse assistant suivante — même convention que CognitiveTurnDiagram).
 */
function resolveAssistantTurnForSelection(
  selectedTurn: number | null,
  messages: MessageRead[],
): number | null {
  if (selectedTurn === null) return null
  const sorted = [...messages].sort((a, b) => a.turn_index - b.turn_index)
  const idx = sorted.findIndex((m) => m.turn_index === selectedTurn)
  if (idx < 0) return null
  const selected = sorted[idx]
  if (selected.role === 'assistant') return selectedTurn
  for (let i = idx + 1; i < sorted.length; i++) {
    if (sorted[i].role === 'assistant') return sorted[i].turn_index
  }
  return null
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
  const [wikiPreview, setWikiPreview] = useState<WikiMarkdownPreviewSelection | null>(
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

  /** Turn dont la trace outils / wiki reflète la réponse : assistant courant ou assistant suivant si sélection user. */
  const workflowTraceTurn = useMemo(() => {
    if (!detail || selectedTurn === null) return null
    return resolveAssistantTurnForSelection(selectedTurn, detail.messages)
  }, [detail, selectedTurn])

  const wikiRefsForSynthèse = useMemo<WikiRefsForTurn>(() => {
    if (!detail || workflowTraceTurn === null) {
      return { reads: [], selectCandidates: [] }
    }
    return extractWikiRefsFromDecisions(
      decisionsByTurn.get(workflowTraceTurn) ?? [],
    )
  }, [detail, workflowTraceTurn, decisionsByTurn])

  const wikiPreloadsForSynthèse = useMemo<WikiPipelinePreloadRef[]>(() => {
    if (!detail || workflowTraceTurn === null) return []
    const asst = detail.messages.find(
      (m) => m.role === 'assistant' && m.turn_index === workflowTraceTurn,
    )
    return extractWikiPreloadFromAssistantPayload(asst?.message_payload ?? null)
  }, [detail, workflowTraceTurn])

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
          <Button variant="outline" size="sm" asChild>
            <Link
              href={`/admin/assistance/conversations/${encodeURIComponent(conversationId)}/runtime-debug`}
              title="Timeline cognitive, récap Agent Action, diffs draft, attributions (infer)"
            >
              <Eye className="h-4 w-4 mr-1.5" /> Runtime debug
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/admin/assistance/observability" title="KPI & gaps agrégés">
              <LineChart className="h-4 w-4 mr-1.5" /> Observabilité
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/admin/assistance/cognitive-funnel" title="Funnel cognitif">
              <BarChart3 className="h-4 w-4 mr-1.5" /> Funnel cognitif
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={onExport}>
            <Download className="h-4 w-4 mr-1.5" /> Export JSON
          </Button>
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Meta — identifiants, lifecycle summary, liens analyse */}
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="py-3 text-xs text-slate-600 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-1.5">
            <span>
              <span className="text-slate-400 font-medium">ID conversation</span>
              <br />
              <code className="text-[10px] break-all">{detail.id}</code>
            </span>
            <span>
              <span className="text-slate-400 font-medium">Client (pe_clients)</span>
              <br />
              <code className="text-[10px] break-all">{detail.client_id}</code>
            </span>
            <span>Créée : {formatDateTime(detail.created_at)}</span>
            <span>Mise à jour : {formatDateTime(detail.updated_at)}</span>
            <span>Dernier message : {formatDateTime(detail.last_message_at)}</span>
            <span>
              Dernier assistant :{' '}
              {formatDateTime(detail.last_assistant_message_at)}
            </span>
            <span>Lu (client) : {formatDateTime(detail.last_read_at)}</span>
            {detail.summary_updated_at && (
              <span>
                Summary MAJ : {formatDateTime(detail.summary_updated_at)}
              </span>
            )}
            {detail.summarized_until_turn !== null && (
              <span>
                Summary jusqu&apos;au turn {detail.summarized_until_turn}
              </span>
            )}
            {detail.conversation_facts.length > 0 && (
              <span>{detail.conversation_facts.length} fact(s) mémorisé(s)</span>
            )}
          </div>
          {detail.current_topic && Object.keys(detail.current_topic).length > 0 && (
            <details className="rounded-md border border-slate-100 bg-slate-50/80 px-2 py-1.5">
              <summary className="cursor-pointer text-[11px] font-medium text-slate-700">
                current_topic (JSON)
              </summary>
              <pre className="mt-2 text-[10px] text-slate-700 overflow-x-auto max-h-36 whitespace-pre-wrap">
                {JSON.stringify(detail.current_topic, null, 2)}
              </pre>
            </details>
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
              const policyGapCount = decisionsForTurn.filter(
                (d) => d.tool_name === 'policy_data_need_reads',
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
                      {policyGapCount > 0 && (
                        <Badge
                          variant="outline"
                          className="text-[9px] py-0 px-1 bg-amber-50 text-amber-800 border-amber-200"
                          title="Gap policy data need (PR3)"
                        >
                          policy {policyGapCount}
                        </Badge>
                      )}
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
                  {m.role === 'assistant' && (
                    <AssistanceMessageRoutingTags
                      tags={extractAssistantRoutingTags(
                        m.turn_index,
                        detail.messages,
                        decisionsByTurn,
                      )}
                    />
                  )}
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
                  {m.role === 'assistant' && (
                    <AssistantWikiRefsSection
                      assistantPayload={m.message_payload ?? null}
                      decisions={decisionsByTurn.get(m.turn_index) ?? []}
                      onOpenWikiPreview={(path, title) =>
                        setWikiPreview({ path, title })
                      }
                    />
                  )}
                  {m.message_payload &&
                  m.message_payload.metadata &&
                  typeof m.message_payload.metadata === 'object' &&
                  !Array.isArray(m.message_payload.metadata) &&
                  Object.keys(m.message_payload.metadata as object).length > 0 ? (
                    <details
                      className="mt-2 text-xs text-slate-600"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <summary className="cursor-pointer flex items-center gap-1.5 hover:text-slate-800">
                        <Box className="h-3 w-3" />
                        metadata (chaîne agents / extras)
                      </summary>
                      <pre className="mt-1.5 text-[11px] bg-slate-900 text-slate-100 rounded p-2 overflow-x-auto max-h-40">
                        {JSON.stringify(m.message_payload.metadata, null, 2)}
                      </pre>
                    </details>
                  ) : null}
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

            <PolicyDataNeedPanel
              turnDecisions={
                workflowTraceTurn !== null
                  ? decisionsByTurn.get(workflowTraceTurn) ?? []
                  : []
              }
              onInspect={setDrawerDecision}
            />

            {workflowTraceTurn !== null && (
              <div className="border-t border-emerald-100/70 pt-3 mt-1">
                <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-900/85 mb-2 px-1">
                  <BookMarked className="h-3 w-3 shrink-0" />
                  Wiki (tour assistant T{workflowTraceTurn})
                </div>
                <SynthèseWikiConsultation
                  pipelinePreloads={wikiPreloadsForSynthèse}
                  reads={wikiRefsForSynthèse.reads}
                  selectCandidates={wikiRefsForSynthèse.selectCandidates}
                  onOpenWikiPreview={(path, title) =>
                    setWikiPreview({ path, title })
                  }
                />
              </div>
            )}

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
              {workflowTraceTurn !== null && (
                <span className="ml-2 text-slate-500 font-normal normal-case">
                  · assistant T{workflowTraceTurn}
                  {selectedTurn !== workflowTraceTurn && selectedTurn !== null
                    ? ` (clic sur T${selectedTurn})`
                    : ''}
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
            ) : workflowTraceTurn === null ? (
              <p className="text-xs text-slate-400 p-2">
                Pas encore de réponse assistant après ce tour utilisateur — la
                trace outils apparaîtra une fois le tour complété.
              </p>
            ) : (
              <WorkflowTraceForTurn
                turnDecisions={decisionsByTurn.get(workflowTraceTurn) ?? []}
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
      <WikiMarkdownPreviewSheet
        selection={wikiPreview}
        onOpenChange={(open) => {
          if (!open) setWikiPreview(null)
        }}
      />
    </div>
  )
}

// ────────────────────────── Sub-components ──────────────────────────

/** PR3 — avertissements policy_data_need_reads pour le tour assistant sélectionné. */
function PolicyDataNeedPanel({
  turnDecisions,
  onInspect,
}: {
  turnDecisions: AgentDecision[]
  onInspect: (d: AgentDecision) => void
}) {
  const gaps = turnDecisions.filter(
    (d) => d.tool_name === 'policy_data_need_reads',
  )
  if (gaps.length === 0) return null

  return (
    <div className="border-t border-amber-100 pt-3 mt-1 space-y-2">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900/90 px-1">
        <AlertTriangle className="h-3 w-3 shrink-0" />
        Policy data need (audit soft)
      </div>
      {gaps.map((d) => {
        const args = (d.arguments ?? {}) as Record<string, unknown>
        const need =
          typeof args.data_need === 'string' ? args.data_need : '—'
        const seqRaw = args.tools_called_this_tour
        const seq = Array.isArray(seqRaw)
          ? seqRaw.map((x) => String(x)).join(', ') || '(aucun)'
          : '—'
        const expRaw = args.expected_read_tools
        const expected = Array.isArray(expRaw)
          ? expRaw.map((x) => String(x)).join(', ')
          : '—'

        return (
          <div
            key={d.id}
            className="rounded-md border border-amber-200/90 bg-amber-50/60 px-2.5 py-2 text-[11px] space-y-1.5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-2 flex-wrap">
                <span className="text-slate-500 text-[10px] uppercase">
                  data_need
                </span>
                <Badge
                  variant="outline"
                  className="text-[9px] py-0 bg-amber-100/80 border-amber-300 text-amber-900"
                >
                  {need}
                </Badge>
                {d.agent_id && (
                  <Badge
                    variant="secondary"
                    className={`text-[9px] py-0 ${agentColor(d.agent_id)}`}
                  >
                    agent {d.agent_id}
                  </Badge>
                )}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 text-[10px] px-2"
                onClick={() => onInspect(d)}
              >
                Détail JSON
              </Button>
            </div>
            <p className="text-[10px] text-slate-700 leading-snug">
              <span className="text-slate-500 font-medium">
                Outils appelés ce tour :{' '}
              </span>
              <span className="font-mono text-[10px] break-words">{seq}</span>
            </p>
            <p className="text-[10px] text-slate-700 leading-snug">
              <span className="text-slate-500 font-medium">
                Lectures métier attendues :{' '}
              </span>
              <span className="font-mono text-[10px] break-words">
                {expected.length > 160
                  ? `${expected.slice(0, 158)}…`
                  : expected}
              </span>
            </p>
          </div>
        )
      })}
    </div>
  )
}

// ────────────────────────── Fiches wiki (pipeline + outils read / select) ──────────────────────────

function WikiMarkdownPreviewSheet({
  selection,
  onOpenChange,
}: {
  selection: WikiMarkdownPreviewSelection | null
  onOpenChange: (open: boolean) => void
}) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetchErr, setFetchErr] = useState<string | null>(null)

  const open = selection !== null

  useEffect(() => {
    if (!selection) {
      setContent(null)
      setFetchErr(null)
      return
    }
    let cancelled = false
    const path = selection.path
    setLoading(true)
    setFetchErr(null)
    setContent(null)
    void fetch(
      `/api/admin/assistance/wiki/item?path=${encodeURIComponent(path)}`,
      { cache: 'no-store' },
    )
      .then(async (r) => {
        if (!r.ok) {
          const j = (await r.json().catch(() => null)) as { error?: string } | null
          throw new Error(j?.error || `HTTP ${r.status}`)
        }
        return r.json() as Promise<{ content?: string }>
      })
      .then((j) => {
        if (cancelled) return
        setContent(typeof j.content === 'string' ? j.content : '')
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setFetchErr(e instanceof Error ? e.message : 'fetch_failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [selection])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-[min(720px,calc(100vw-48px))] max-w-none flex-col gap-0 p-0 sm:max-w-none"
      >
        <SheetHeader className="border-b border-slate-100 bg-slate-50/90 px-4 py-3 pr-14">
          <SheetTitle className="text-base line-clamp-2">
            {selection?.title ?? 'Fiche wiki'}
          </SheetTitle>
          <SheetDescription asChild>
            <p className="font-mono text-[11px] text-slate-500 truncate">
              {selection?.path}
            </p>
          </SheetDescription>
          {selection && (
            <Link
              href={adminWikiEditorUrl(selection.path)}
              className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-700 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Ouvrir dans l&apos;éditeur wiki admin
            </Link>
          )}
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {loading && (
            <p className="text-sm text-slate-500">Chargement du Markdown…</p>
          )}
          {fetchErr && !loading && (
            <p className="text-sm text-red-600">Erreur : {fetchErr}</p>
          )}
          {!loading && !fetchErr && content !== null && (
            <article className="prose prose-slate prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </article>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

function WikiAdminFicheLine({
  title,
  relativePath,
  hintSuffix,
  titleClassName,
  onOpenPreview,
}: {
  title: string
  relativePath: string
  hintSuffix: string
  titleClassName: string
  onOpenPreview?: (relativePath: string, title: string) => void
}) {
  return (
    <li className="text-[11px] leading-snug">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
        {onOpenPreview ? (
          <button
            type="button"
            className={`text-left font-medium hover:underline underline-offset-2 ${titleClassName}`}
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              onOpenPreview(relativePath, title)
            }}
          >
            <Eye className="inline h-3 w-3 mr-0.5 opacity-70 translate-y-[1px]" />
            {title}
          </button>
        ) : (
          <Link
            href={adminWikiEditorUrl(relativePath)}
            className={`font-medium hover:underline underline-offset-2 ${titleClassName}`}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            {title}
          </Link>
        )}
        <Link
          href={adminWikiEditorUrl(relativePath)}
          className="text-slate-500 hover:text-slate-800 inline-flex items-center gap-0.5 text-[10px] shrink-0"
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-3 w-3" />
          éditeur
        </Link>
      </div>
      <span className="text-slate-500 font-mono text-[10px] block truncate">
        {relativePath}
        <span className="text-slate-400">{hintSuffix}</span>
      </span>
    </li>
  )
}

function AssistantWikiRefsSection({
  assistantPayload,
  decisions,
  onOpenWikiPreview,
}: {
  assistantPayload: Record<string, unknown> | null
  decisions: AgentDecision[]
  onOpenWikiPreview?: (relativePath: string, title: string) => void
}) {
  const pipelinePreloads = extractWikiPreloadFromAssistantPayload(assistantPayload)
  const { reads, selectCandidates } = extractWikiRefsFromDecisions(decisions)
  const readKeys = new Set(reads.map((r) => `${r.category}/${r.slug}`))
  const selectOnly = selectCandidates.filter(
    (c) => !readKeys.has(`${c.category}/${c.slug}`),
  )

  if (
    pipelinePreloads.length === 0 &&
    reads.length === 0 &&
    selectCandidates.length === 0
  ) {
    return null
  }

  return (
    <div className="mt-2.5 space-y-2" onClick={(e) => e.stopPropagation()}>
      {pipelinePreloads.length > 0 && (
        <div className="pt-2.5 border-t border-violet-100/90 bg-violet-50/50 rounded-md px-2.5 py-2 -mx-0.5">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-violet-900/85 mb-1.5">
            <BookMarked className="h-3 w-3 shrink-0" />
            Wiki injecté (pipeline Pass 1)
          </div>
          <ul className="space-y-1 mb-1">
            {pipelinePreloads.map((p) => (
              <WikiAdminFicheLine
                key={`pp-${p.category}/${p.slug}`}
                hintSuffix=" · contenu vu par le modèle (tronqué dans le prompt)"
                relativePath={p.relativePath}
                title={p.title}
                titleClassName="text-violet-950"
                onOpenPreview={onOpenWikiPreview}
              />
            ))}
          </ul>
        </div>
      )}

      {(reads.length > 0 || selectOnly.length > 0) && (
        <div
          className={
            pipelinePreloads.length > 0
              ? 'pt-2 border-t border-violet-50/70'
              : 'pt-2.5 border-t border-emerald-100/80'
          }
        >
          <div className="rounded-md px-2.5 py-2 bg-emerald-50/40 border border-emerald-100/80 -mx-0.5">
            <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-800/90 mb-1.5">
              <Wrench className="h-3 w-3 shrink-0 opacity-70" />
              Fiches wiki (outils retrieval)
            </div>

            {reads.length > 0 && (
              <ul className="space-y-1 mb-2">
                {reads.map((r) => (
                  <WikiAdminFicheLine
                    key={`${r.category}/${r.slug}`}
                    hintSuffix=" · lu via read_wiki_page"
                    relativePath={r.relativePath}
                    title={r.title}
                    titleClassName="text-emerald-900"
                    onOpenPreview={onOpenWikiPreview}
                  />
                ))}
              </ul>
            )}

            {selectOnly.length > 0 && (
              <details className="text-[11px]">
                <summary className="cursor-pointer text-slate-600 hover:text-slate-800">
                  Pré-sélection select_wiki_pages ({selectOnly.length} candidat
                  {selectOnly.length > 1 ? 's' : ''} hors lectures)
                </summary>
                <ul className="mt-1.5 pl-4 space-y-1 border-l border-emerald-100 ml-1">
                  {selectOnly.map((c) => (
                    <WikiAdminFicheLine
                      key={`sel-${c.category}/${c.slug}`}
                      hintSuffix={
                        c.score != null
                          ? ` · score ${c.score.toFixed(2)}`
                          : ' · select_wiki_pages'
                      }
                      relativePath={c.relativePath}
                      title={c.title}
                      titleClassName="text-slate-700"
                      onOpenPreview={onOpenWikiPreview}
                    />
                  ))}
                </ul>
              </details>
            )}

            {reads.length === 0 && selectCandidates.length > 0 && (
              <p className="text-[10px] text-amber-800/90 italic">
                Aucune lecture complète (read_wiki_page) sur ce tour — seulement un
                classement candidats. Ouvrez la trace outils pour le détail.
              </p>
            )}
          </div>
        </div>
      )}

      {pipelinePreloads.length > 0 && reads.length === 0 && selectCandidates.length === 0 && (
        <p className="text-[10px] text-slate-600 px-1">
          Pas d&apos;appel{' '}
          <code className="text-[10px] bg-slate-100 px-1 rounded">read_wiki_page</code> /
          <code className="text-[10px] bg-slate-100 px-1 rounded">select_wiki_pages</code>{' '}
          sur ce tour — la réponse peut reposer uniquement sur le bloc wiki pré-chargé.
        </p>
      )}
    </div>
  )
}

/** Bloc wiki en colonne synthèse : affiche toujours un état (y compris vide). */
function SynthèseWikiConsultation({
  pipelinePreloads = [],
  reads,
  selectCandidates,
  onOpenWikiPreview,
}: WikiRefsForTurn & {
  pipelinePreloads?: WikiPipelinePreloadRef[]
  onOpenWikiPreview?: (relativePath: string, title: string) => void
}) {
  const readKeys = new Set(reads.map((r) => `${r.category}/${r.slug}`))
  const selectOnly = selectCandidates.filter(
    (c) => !readKeys.has(`${c.category}/${c.slug}`),
  )

  if (
    reads.length === 0 &&
    selectCandidates.length === 0 &&
    pipelinePreloads.length === 0
  ) {
    return (
      <p className="text-[11px] text-slate-600 bg-slate-50 border border-slate-100 rounded-md px-2.5 py-2 leading-snug">
        <span className="font-medium text-slate-700">
          Aucune fiche wiki identifiée sur ce tour.
        </span>{' '}
        Pas de préchargement pipeline persisté ni d&apos;appel{' '}
        <code className="text-[10px] bg-slate-100 px-1 rounded">read_wiki_page</code> /{' '}
        <code className="text-[10px] bg-slate-100 px-1 rounded">select_wiki_pages</code>{' '}
        — la réponse peut reposer sur le compte, le modèle seul ou un ancien flux sans
        métadonnée de précharge.
      </p>
    )
  }

  return (
    <div className="space-y-3 text-[11px]">
      {pipelinePreloads.length > 0 && (
        <div className="space-y-1 text-[11px] bg-violet-50/55 border border-violet-100/90 rounded-md px-2.5 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-violet-900/85 mb-1">
            Préchargé dans le prompt (pipeline)
          </div>
          <ul className="space-y-1">
            {pipelinePreloads.map((p) => (
              <WikiAdminFicheLine
                key={`syn-pp-${p.category}/${p.slug}`}
                hintSuffix=""
                relativePath={p.relativePath}
                title={p.title}
                titleClassName="text-violet-950"
                onOpenPreview={onOpenWikiPreview}
              />
            ))}
          </ul>
        </div>
      )}
      {(reads.length > 0 || selectOnly.length > 0) && (
        <div className="space-y-2 bg-emerald-50/35 border border-emerald-100/80 rounded-md px-2.5 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-900/85">
            Retrieval (outils)
          </div>
          {reads.length > 0 && (
            <ul className="space-y-1">
              {reads.map((r) => (
                <WikiAdminFicheLine
                  key={`syn-read-${r.category}/${r.slug}`}
                  hintSuffix=" · read_wiki_page"
                  relativePath={r.relativePath}
                  title={r.title}
                  titleClassName="text-emerald-900"
                  onOpenPreview={onOpenWikiPreview}
                />
              ))}
            </ul>
          )}
          {selectOnly.length > 0 && (
            <details>
              <summary className="cursor-pointer text-slate-600 hover:text-slate-800">
                select_wiki_pages ({selectOnly.length} candidat
                {selectOnly.length > 1 ? 's' : ''} sans lecture complète)
              </summary>
              <ul className="mt-1.5 pl-3 space-y-1 border-l border-emerald-200">
                {selectOnly.map((c) => (
                  <WikiAdminFicheLine
                    key={`syn-sel-${c.category}/${c.slug}`}
                    hintSuffix={
                      c.score != null ? ` · ${c.score.toFixed(2)}` : ' · select'
                    }
                    relativePath={c.relativePath}
                    title={c.title}
                    titleClassName="text-slate-700"
                    onOpenPreview={onOpenWikiPreview}
                  />
                ))}
              </ul>
            </details>
          )}
          {reads.length === 0 && selectCandidates.length > 0 && (
            <p className="text-[10px] text-amber-800/90 italic">
              Seulement des candidats classés — aucune lecture complète de fiche.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

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
            {list.map((d) => {
              const isPolicyGap = d.tool_name === 'policy_data_need_reads'
              return (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => onPickDecision(d)}
                  className={`w-full text-left px-2.5 py-2 hover:bg-slate-50 flex items-start gap-2 border-b border-slate-50 last:border-0 ${
                    isPolicyGap ? 'bg-amber-50/40 hover:bg-amber-50/60' : ''
                  }`}
                >
                  <span className="text-slate-400 font-mono text-[10px] mt-0.5 flex-shrink-0">
                    #{d.iteration}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-800 font-medium truncate flex items-center gap-1.5">
                      {isPolicyGap ? (
                        <AlertTriangle className="h-3 w-3 text-amber-600 flex-shrink-0" />
                      ) : (
                        <Wrench className="h-3 w-3 text-slate-400 flex-shrink-0" />
                      )}
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
              )
            })}
          </ul>
        </li>
      ))}
    </ul>
  )
}

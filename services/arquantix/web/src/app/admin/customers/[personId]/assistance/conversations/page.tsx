/**
 * Page liste des conversations IA d'un client (admin monitoring v1).
 *
 * Route : `/admin/customers/[personId]/assistance/conversations`
 * Source : `GET /api/admin/assistance/conversations?person_id=…`
 *
 * Read-only. Filtres : status (active/closed/all). Pagination simple.
 * Cf. `services/assistance/admin_conversations_router.py`.
 */
'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeft,
  ArrowRight,
  RefreshCw,
  AlertTriangle,
  MessageCircle,
} from 'lucide-react'

interface CurrentTopic {
  kind?: string
  product_code?: string
  agent_owner?: string
  [key: string]: unknown
}

interface ConversationListItem {
  id: string
  client_id: string
  title: string | null
  status: string
  created_at: string | null
  updated_at: string | null
  last_message_at: string | null
  last_assistant_message_at: string | null
  summarized_until_turn: number | null
  current_topic: CurrentTopic | null
  message_count: number
  tool_call_count: number
  tool_error_count: number
}

interface ListResponse {
  items: ConversationListItem[]
  total: number
  limit: number
  offset: number
  total_messages: number
  total_tool_calls: number
  total_tool_errors: number
  last_activity_at: string | null
}

const PAGE_SIZE = 20

function formatDate(iso: string | null): string {
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

export default function ConversationsListPage() {
  const router = useRouter()
  const params = useParams()
  const personId = (params?.personId as string | undefined) ?? ''

  const [data, setData] = useState<ListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'closed'>(
    'all',
  )
  const [page, setPage] = useState(0)

  const offset = page * PAGE_SIZE

  const load = useCallback(async () => {
    if (!personId) return
    setLoading(true)
    setError(null)
    try {
      const sp = new URLSearchParams()
      sp.set('person_id', personId)
      sp.set('limit', String(PAGE_SIZE))
      sp.set('offset', String(offset))
      if (statusFilter !== 'all') sp.set('status', statusFilter)
      const res = await fetch(
        `/api/admin/assistance/conversations?${sp.toString()}`,
        { cache: 'no-store' },
      )
      if (!res.ok) {
        if (res.status === 404) {
          setData({
            items: [],
            total: 0,
            limit: PAGE_SIZE,
            offset,
            total_messages: 0,
            total_tool_calls: 0,
            total_tool_errors: 0,
            last_activity_at: null,
          })
          return
        }
        throw new Error(`HTTP ${res.status}`)
      }
      const json = (await res.json()) as ListResponse
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [personId, statusFilter, offset])

  useEffect(() => {
    void load()
  }, [load])

  const totalPages = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1),
    [data],
  )

  return (
    <div className="space-y-4 p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              router.push(`/admin/customers/${encodeURIComponent(personId)}`)
            }
          >
            <ArrowLeft className="h-4 w-4 mr-1" /> Retour fiche client
          </Button>
          <h1 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
            <MessageCircle className="h-5 w-5 text-slate-500" />
            Conversations IA
          </h1>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </Button>
      </div>

      {/* Filtres */}
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="py-3 flex items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-500 font-semibold">
            Statut :
          </span>
          {(['all', 'active', 'closed'] as const).map((opt) => (
            <Button
              key={opt}
              size="sm"
              variant={statusFilter === opt ? 'default' : 'outline'}
              onClick={() => {
                setStatusFilter(opt)
                setPage(0)
              }}
              className="h-7 text-xs"
            >
              {opt === 'all' ? 'Toutes' : opt}
            </Button>
          ))}
          {data && (
            <span className="ml-auto text-xs text-slate-500">
              {data.total} résultat{data.total > 1 ? 's' : ''} ·{' '}
              {data.total_messages} msg · {data.total_tool_calls} tool
              {data.total_tool_errors > 0 && (
                <span className="text-red-600">
                  {' '}
                  · {data.total_tool_errors} err
                </span>
              )}
            </span>
          )}
        </CardContent>
      </Card>

      {/* Liste */}
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-3">
          <CardTitle className="text-sm font-semibold tracking-wide text-slate-800 uppercase">
            Conversations
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {error ? (
            <div className="flex items-center gap-2 text-red-600 text-sm p-6">
              <AlertTriangle className="h-4 w-4" />
              <span>Erreur de chargement : {error}</span>
            </div>
          ) : loading && !data ? (
            <p className="text-xs text-slate-500 p-6">Chargement…</p>
          ) : !data || data.items.length === 0 ? (
            <p className="text-xs text-slate-500 p-6">Aucune conversation.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.items.map((item) => {
                const topic = renderTopic(item.current_topic)
                return (
                  <li key={item.id}>
                    <Link
                      href={`/admin/customers/${encodeURIComponent(
                        personId,
                      )}/assistance/conversations/${item.id}`}
                      className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
                    >
                      <span
                        className={`mt-1.5 inline-block h-2.5 w-2.5 rounded-full flex-shrink-0 ${
                          item.status === 'active'
                            ? 'bg-emerald-500'
                            : 'bg-slate-300'
                        }`}
                        title={item.status}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <p className="text-sm font-medium text-slate-800 truncate max-w-md">
                            {item.title || 'Conversation sans titre'}
                          </p>
                          <Badge
                            variant="outline"
                            className="text-[10px] uppercase tracking-wide font-normal"
                          >
                            {item.status}
                          </Badge>
                          {topic && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] font-normal bg-indigo-50 text-indigo-700 hover:bg-indigo-50"
                            >
                              {topic}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          {formatDate(item.last_message_at)} ·{' '}
                          {item.message_count} turn
                          {item.message_count > 1 ? 's' : ''} ·{' '}
                          {item.tool_call_count} tool call
                          {item.tool_call_count > 1 ? 's' : ''}
                          {item.tool_error_count > 0 && (
                            <span className="text-red-600 ml-1">
                              · {item.tool_error_count} erreur
                              {item.tool_error_count > 1 ? 's' : ''}
                            </span>
                          )}
                          {item.summarized_until_turn !== null &&
                            item.summarized_until_turn !== undefined && (
                              <span className="text-slate-400 ml-1">
                                · summary up to turn{' '}
                                {item.summarized_until_turn}
                              </span>
                            )}
                        </p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-slate-400 flex-shrink-0 mt-1.5" />
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-xs text-slate-600">
          <span>
            Page {page + 1} / {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Précédent
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Suivant
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

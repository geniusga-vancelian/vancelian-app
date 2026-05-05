/**
 * Section "Conversations IA" intégrée à la fiche customer admin.
 *
 * Source : `GET /api/admin/assistance/conversations?person_id=<personId>`
 * (read-only, cf. `services/assistance/admin_conversations_router.py`).
 *
 * Affiche un compteur global + les 3 dernières conversations + un lien vers
 * la page de monitoring détaillée. Snapshot à l'ouverture, pas de polling.
 */
'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ArrowRight, MessageCircle, AlertTriangle, RefreshCw } from 'lucide-react'

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

interface Props {
  personId: string
}

export function AssistanceConversationsSection({ personId }: Props) {
  const [data, setData] = useState<ListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `/api/admin/assistance/conversations?person_id=${encodeURIComponent(
          personId,
        )}&limit=3`,
        { cache: 'no-store' },
      )
      if (!res.ok) {
        // 404 = pas de pe_client = jamais utilisé l'app, pas une vraie erreur.
        if (res.status === 404) {
          setData({
            items: [],
            total: 0,
            limit: 3,
            offset: 0,
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
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personId])

  return (
    <Card className="border-slate-200 scroll-mt-4 shadow-sm">
      <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-3 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-semibold tracking-wide text-slate-800 uppercase flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-slate-500" />
          Conversations IA
        </CardTitle>
        <Button
          size="sm"
          variant="ghost"
          onClick={load}
          disabled={loading}
          className="h-7 px-2 text-xs"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent className="pt-4 text-sm text-slate-700">
        {error ? (
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertTriangle className="h-4 w-4" />
            <span>Erreur de chargement : {error}</span>
          </div>
        ) : loading && !data ? (
          <p className="text-xs text-slate-500">Chargement…</p>
        ) : !data || data.total === 0 ? (
          <p className="text-xs text-slate-500">
            Aucune conversation IA pour ce client.
          </p>
        ) : (
          <div className="space-y-3">
            {/* Compteurs globaux */}
            <div className="flex flex-wrap gap-2 text-xs text-slate-600">
              <Badge variant="secondary" className="font-normal">
                {data.total} conversation{data.total > 1 ? 's' : ''}
              </Badge>
              <Badge variant="secondary" className="font-normal">
                {data.total_messages} message{data.total_messages > 1 ? 's' : ''}
              </Badge>
              <Badge variant="secondary" className="font-normal">
                {data.total_tool_calls} tool call
                {data.total_tool_calls > 1 ? 's' : ''}
              </Badge>
              {data.total_tool_errors > 0 && (
                <Badge
                  variant="destructive"
                  className="font-normal bg-red-100 text-red-700 hover:bg-red-100"
                >
                  {data.total_tool_errors} erreur
                  {data.total_tool_errors > 1 ? 's' : ''}
                </Badge>
              )}
              {data.last_activity_at && (
                <span className="text-slate-500">
                  · dernière activité {formatDate(data.last_activity_at)}
                </span>
              )}
            </div>

            {/* Liste des 3 dernières */}
            <ul className="divide-y divide-slate-100 border border-slate-100 rounded-md">
              {data.items.map((item) => {
                const topic = renderTopic(item.current_topic)
                return (
                  <li key={item.id}>
                    <Link
                      href={`/admin/customers/${personId}/assistance/conversations/${item.id}`}
                      className="flex items-start gap-3 px-3 py-2.5 hover:bg-slate-50 transition-colors"
                    >
                      <span
                        className={`mt-1.5 inline-block h-2 w-2 rounded-full flex-shrink-0 ${
                          item.status === 'active'
                            ? 'bg-emerald-500'
                            : 'bg-slate-300'
                        }`}
                        title={item.status}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-800 truncate">
                          {item.title || 'Conversation sans titre'}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5 truncate">
                          {formatDate(item.last_message_at)} ·{' '}
                          {item.message_count} turn
                          {item.message_count > 1 ? 's' : ''} ·{' '}
                          {item.tool_call_count} tool
                          {item.tool_call_count > 1 ? 's' : ''}
                          {item.tool_error_count > 0 && (
                            <span className="text-red-600 ml-1">
                              · {item.tool_error_count} err
                            </span>
                          )}
                          {topic && (
                            <span className="ml-1 text-indigo-600">
                              · {topic}
                            </span>
                          )}
                        </p>
                      </div>
                      <ArrowRight className="h-4 w-4 text-slate-400 flex-shrink-0 mt-1" />
                    </Link>
                  </li>
                )
              })}
            </ul>

            {data.total > 3 && (
              <div className="pt-1">
                <Link
                  href={`/admin/customers/${personId}/assistance/conversations`}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1"
                >
                  Voir toutes les conversations ({data.total})
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

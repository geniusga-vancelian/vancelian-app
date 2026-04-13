'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface TimelineEvent {
  id: string
  event_type: string
  event_status: string | null
  created_at: string | null
  payload_json: Record<string, unknown>
  label_fr?: string
  badge_variant?: string
}

function badgeClass(variant: string | undefined) {
  switch (variant) {
    case 'success':
      return 'bg-emerald-100 text-emerald-800'
    case 'danger':
      return 'bg-red-100 text-red-800'
    case 'warning':
      return 'bg-amber-100 text-amber-900'
    case 'neutral':
      return 'bg-gray-100 text-gray-700'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

export default function RegistrationSessionDetailPage() {
  const params = useParams()
  const id = (params?.id as string | undefined) ?? ''
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [replay, setReplay] = useState<Record<string, unknown> | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetch(`${BACKEND}/api/admin/registration/sessions/${id}`).then(r => {
        if (!r.ok) throw new Error('Session introuvable')
        return r.json()
      }),
      fetch(`${BACKEND}/api/admin/registration/sessions/${id}/execution-events`).then(r => r.json()),
      fetch(`${BACKEND}/api/admin/registration/sessions/${id}/replay`).then(r => r.json()),
    ])
      .then(([d, ev, rp]) => {
        setDetail(d)
        setEvents(ev.events || [])
        setReplay(rp)
        setErr(null)
      })
      .catch(e => setErr(String(e.message || e)))
  }, [id])

  if (err) {
    return (
      <div>
        <p className="text-red-600">{err}</p>
        <Link href="/admin/registration/sessions">
          <Button variant="outline" className="mt-4">
            Retour liste
          </Button>
        </Link>
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="flex justify-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  const summary = (detail.summary || {}) as Record<string, number | null>
  const stepStates = (detail.step_states || []) as Array<Record<string, unknown>>
  const valFails = (detail.validation_failures || []) as unknown[]
  const blocked = (detail.blocked_events || []) as unknown[]
  const ruleBatches = (detail.rule_evaluation_batches || []) as unknown[]
  const collected = (detail.collected_data_snapshot || {}) as Record<string, unknown>
  const projection = detail.projection as Record<string, unknown> | null
  const screensViewed = (detail.screens_viewed || []) as string[]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Session {id.slice(0, 8)}…</h1>
          <p className="text-sm text-gray-500 font-mono">{id}</p>
        </div>
        <Link href="/admin/registration/sessions">
          <Button variant="outline" size="sm">
            Liste
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Résumé</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 text-sm">
          <div>
            <span className="text-gray-500">Statut</span>
            <div>
              <Badge>{String(detail.session_status)}</Badge>
            </div>
          </div>
          <div>
            <span className="text-gray-500">Juridiction</span>
            <div>{String(detail.jurisdiction || '—')}</div>
          </div>
          <div>
            <span className="text-gray-500">Flow</span>
            <div>
              {(detail.flow as { name?: string; version?: number } | undefined)?.name || '—'} v
              {(detail.flow as { version?: number } | undefined)?.version ?? '—'}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Person / Client</span>
            <div className="font-mono text-xs break-all">
              {String(detail.person_id || '—')} / {String(detail.client_id || '—')}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Créée / MAJ</span>
            <div className="text-xs">
              {String(detail.created_at || '—')}
              <br />
              {String(detail.updated_at || '—')}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Stats replay</span>
            <div className="text-xs space-y-1">
              <div>Écrans vus : {summary.screens_viewed_count ?? '—'}</div>
              <div>Soumissions : {summary.submits_count ?? '—'}</div>
              <div>Échecs validation : {summary.validation_failures_count ?? '—'}</div>
              <div>Blocages : {summary.blocked_steps_count ?? '—'}</div>
              <div>Durée (s) : {summary.duration_seconds ?? '—'}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Étapes (état session)</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-sm space-y-2">
            {stepStates.length === 0 && <li className="text-gray-500">Aucun enregistrement</li>}
            {stepStates.map((s, i) => (
              <li key={i} className="flex flex-wrap gap-2 border-b border-gray-100 pb-2">
                <span className="font-mono text-xs">{String(s.step_id)}</span>
                <Badge variant="outline">{String(s.status)}</Badge>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Parcours (écrans vus)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1">
            {screensViewed.length === 0 && <span className="text-gray-500 text-sm">—</span>}
            {screensViewed.map(sk => (
              <Badge key={sk} variant="secondary">
                {sk}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Timeline des événements</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 max-h-[480px] overflow-y-auto">
          {events.map(ev => (
            <div
              key={ev.id}
              className="border border-gray-100 rounded-md p-3 text-sm bg-white"
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <Badge className={badgeClass(ev.badge_variant)}>{ev.label_fr || ev.event_type}</Badge>
                <span className="text-xs text-gray-400">{ev.created_at}</span>
              </div>
              <div className="text-xs font-mono text-gray-600">{ev.event_type}</div>
              <pre className="text-xs mt-2 bg-gray-50 p-2 rounded overflow-x-auto max-h-32">
                {JSON.stringify(ev.payload_json, null, 2)}
              </pre>
            </div>
          ))}
        </CardContent>
      </Card>

      {valFails.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Échecs de validation</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-red-50 p-3 rounded overflow-x-auto">
              {JSON.stringify(valFails, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {blocked.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Blocages</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-amber-50 p-3 rounded overflow-x-auto">
              {JSON.stringify(blocked, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {ruleBatches.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Évaluations de règles (lots)</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-slate-50 p-3 rounded overflow-x-auto max-h-64">
              {JSON.stringify(ruleBatches, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Données collectées (snapshot brut)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-gray-500 mb-2">
            Données en base session — à manipuler selon politique interne (RGPD).
          </p>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto max-h-48">
            {JSON.stringify(collected, null, 2)}
          </pre>
        </CardContent>
      </Card>

      {projection && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Projection</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-emerald-50 p-3 rounded overflow-x-auto">
              {JSON.stringify(projection, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {replay && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Replay JSON complet</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto max-h-96">
              {JSON.stringify(replay, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

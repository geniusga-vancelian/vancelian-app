'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface SessionRow {
  id: string
  short_id: string
  status: string
  flow_name: string | null
  flow_version: number
  jurisdiction_code: string | null
  person_id: string | null
  client_id: string | null
  current_step_key: string | null
  current_screen_key: string | null
  progress_percent: number
  created_at: string | null
  updated_at: string | null
}

interface Jurisdiction {
  id: string
  code: string
  name: string
}

interface Flow {
  id: string
  name: string
  version: number
}

function statusBadge(status: string) {
  if (status === 'completed') return 'bg-emerald-100 text-emerald-800'
  if (status === 'in_progress') return 'bg-blue-50 text-blue-800'
  return 'bg-gray-100 text-gray-700'
}

export default function RegistrationSessionsPage() {
  const [items, setItems] = useState<SessionRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [jurisdictionId, setJurisdictionId] = useState<string>('all')
  const [flowId, setFlowId] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([])
  const [flows, setFlows] = useState<Flow[]>([])

  const query = useMemo(() => {
    const p = new URLSearchParams()
    p.set('limit', '50')
    if (statusFilter !== 'all') p.set('status', statusFilter)
    if (jurisdictionId !== 'all') p.set('jurisdiction_id', jurisdictionId)
    if (flowId !== 'all') p.set('flow_id', flowId)
    return p.toString()
  }, [statusFilter, jurisdictionId, flowId])

  useEffect(() => {
    Promise.all([
      fetch(`${BACKEND}/api/admin/registration/jurisdictions`).then(r => r.json()),
      fetch(`${BACKEND}/api/admin/registration/flows`).then(r => r.json()),
    ])
      .then(([j, f]) => {
        setJurisdictions(j)
        setFlows(f)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    fetch(`${BACKEND}/api/admin/registration/sessions?${query}`)
      .then(r => r.json())
      .then(data => {
        setItems(data.items || [])
        setTotal(data.total ?? 0)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [query])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return items
    return items.filter(
      s =>
        s.id.toLowerCase().includes(q) ||
        (s.person_id && s.person_id.toLowerCase().includes(q)) ||
        (s.flow_name && s.flow_name.toLowerCase().includes(q))
    )
  }, [items, search])

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sessions d&apos;inscription</h1>
          <p className="text-sm text-gray-500">
            {total} session(s) — lecture seule (support / conformité)
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/admin/registration">
            <Button variant="outline" size="sm">
              Flows
            </Button>
          </Link>
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Filtres</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 items-end">
          <div className="w-40">
            <label className="text-xs text-gray-500 block mb-1">Statut</label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="in_progress">En cours</SelectItem>
                <SelectItem value="completed">Terminé</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="w-48">
            <label className="text-xs text-gray-500 block mb-1">Juridiction</label>
            <Select value={jurisdictionId} onValueChange={setJurisdictionId}>
              <SelectTrigger>
                <SelectValue placeholder="Juridiction" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes</SelectItem>
                {jurisdictions.map(j => (
                  <SelectItem key={j.id} value={j.id}>
                    {j.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-56">
            <label className="text-xs text-gray-500 block mb-1">Flow</label>
            <Select value={flowId} onValueChange={setFlowId}>
              <SelectTrigger>
                <SelectValue placeholder="Flow" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                {flows.map(f => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.name} v{f.version}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-gray-500 block mb-1">Recherche (id, person, flow)</label>
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Filtrer côté client…"
            />
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.length === 0 && (
            <p className="text-sm text-gray-500">Aucune session pour ces filtres.</p>
          )}
          {filtered.map(s => (
            <Card key={s.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="py-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-medium">{s.short_id}…</span>
                    <Badge className={statusBadge(s.status)}>{s.status}</Badge>
                    <Badge variant="outline">{s.jurisdiction_code || '—'}</Badge>
                  </div>
                  <div className="text-sm text-gray-700">
                    {s.flow_name || 'Flow'} <span className="text-gray-500">v{s.flow_version}</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    Étape {s.current_step_key || '—'} · Écran {s.current_screen_key || '—'} ·{' '}
                    {s.progress_percent}%
                  </div>
                  {(s.person_id || s.client_id) && (
                    <div className="text-xs text-gray-500 font-mono">
                      {s.person_id && <>person {s.person_id.slice(0, 8)}… </>}
                      {s.client_id && <>client {s.client_id.slice(0, 8)}…</>}
                    </div>
                  )}
                </div>
                <div className="text-xs text-gray-400 sm:text-right">
                  {s.created_at && <div>créée {new Date(s.created_at).toLocaleString()}</div>}
                  {s.updated_at && <div>maj {new Date(s.updated_at).toLocaleString()}</div>}
                  <Link href={`/admin/registration/sessions/${s.id}`}>
                    <Button size="sm" className="mt-2" variant="secondary">
                      Détail
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

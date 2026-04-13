'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

type Row = {
  timestamp: string | null
  user_id: number | null
  rule_name: string | null
  action: string | null
  route: string | null
  risk_score: number | null
  event_type: string
  metadata: Record<string, unknown>
}

export default function RiskLogsPage() {
  const [items, setItems] = useState<Row[]>([])
  const [note, setNote] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [rule, setRule] = useState('')
  const [action, setAction] = useState('')
  const ruleRef = useRef(rule)
  const actionRef = useRef(action)
  ruleRef.current = rule
  actionRef.current = action

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const sp = new URLSearchParams()
      sp.set('limit', '100')
      if (ruleRef.current.trim()) sp.set('rule', ruleRef.current.trim())
      if (actionRef.current.trim()) sp.set('action', actionRef.current.trim())
      const res = await fetch(`/api/admin/risk/logs?${sp.toString()}`, {
        credentials: 'include',
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)
      const data = await res.json()
      setItems(data.items || [])
      setNote(data.note || '')
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 max-w-3xl">
        Événements issus de <code className="bg-gray-100 px-1">auth_security_events</code> (types
        contenant « risk »). {note}
      </p>
      <div className="flex flex-wrap gap-2 items-end">
        <label className="text-sm">
          Règle (contient)
          <input
            className="block border rounded px-2 py-1 mt-1 w-40"
            value={rule}
            onChange={(e) => setRule(e.target.value)}
          />
        </label>
        <label className="text-sm">
          Action (contient)
          <input
            className="block border rounded px-2 py-1 mt-1 w-40"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="rounded bg-gray-900 text-white px-3 py-1 text-sm"
          onClick={() => load()}
        >
          Filtrer
        </button>
      </div>
      {err && <p className="text-red-600 text-sm">{err}</p>}
      {loading ? (
        <p>Chargement…</p>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-200 bg-white text-sm">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-100 text-left">
                <th className="p-2">Date</th>
                <th className="p-2">User</th>
                <th className="p-2">Règle</th>
                <th className="p-2">Action</th>
                <th className="p-2">Route</th>
                <th className="p-2">Score</th>
                <th className="p-2">event_type</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r, i) => (
                <tr key={i} className="border-t border-gray-100">
                  <td className="p-2 whitespace-nowrap">
                    {r.timestamp ? new Date(r.timestamp).toLocaleString('fr-FR') : '—'}
                  </td>
                  <td className="p-2">{r.user_id ?? '—'}</td>
                  <td className="p-2">{r.rule_name || '—'}</td>
                  <td className="p-2">{r.action || '—'}</td>
                  <td className="p-2 max-w-xs truncate">{r.route || '—'}</td>
                  <td className="p-2">{r.risk_score ?? '—'}</td>
                  <td className="p-2 text-xs text-gray-600">{r.event_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && (
            <p className="p-4 text-gray-500">Aucun événement — activer la persistance SIEM ou élargir les filtres.</p>
          )}
        </div>
      )}
    </div>
  )
}

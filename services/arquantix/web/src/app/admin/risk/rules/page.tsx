'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'

type Rule = {
  id: string
  name: string | null
  priority: number
  action: string
  is_active: boolean
  ruleset: string
  version: number
  updated_at: string | null
}

type Settings = {
  dry_run: boolean
  dry_run_source: string
  device_risk_rules_ruleset: string
  redis_override_available: boolean
}

export default function RiskRulesListPage() {
  const [rules, setRules] = useState<Rule[]>([])
  const [ruleset, setRuleset] = useState('')
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [savingDry, setSavingDry] = useState(false)
  const rulesetRef = useRef(ruleset)
  rulesetRef.current = ruleset

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const rs = rulesetRef.current.trim()
      const q = rs ? `?ruleset=${encodeURIComponent(rs)}` : ''
      const [r, s] = await Promise.all([
        fetch(`/api/admin/risk/rules${q}`, { credentials: 'include' }),
        fetch(`/api/admin/risk/settings`, { credentials: 'include' }),
      ])
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
      if (!s.ok) throw new Error('settings')
      setRules(await r.json())
      setSettings(await s.json())
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const toggle = async (id: string, next: boolean) => {
    setErr(null)
    const res = await fetch(`/api/admin/risk/rules/${id}`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: next }),
    })
    if (!res.ok) {
      setErr((await res.json().catch(() => ({}))).detail || res.statusText)
      return
    }
    load()
  }

  const setDryRun = async (enabled: boolean) => {
    setSavingDry(true)
    setErr(null)
    try {
      const res = await fetch(`/api/admin/risk/settings/dry-run`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || res.statusText)
      }
      await load()
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Impossible (Redis requis pour override)')
    } finally {
      setSavingDry(false)
    }
  }

  const panic = async () => {
    if (
      !confirm(
        'Désactiver toutes les règles dynamiques (is_active=false) pour ce filtre ruleset ?'
      )
    )
      return
    const q = ruleset.trim() ? `?ruleset=${encodeURIComponent(ruleset.trim())}` : ''
    const res = await fetch(`/api/admin/risk/rules/disable-all${q}`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!res.ok) setErr('Échec désactivation')
    else load()
  }

  return (
    <div className="space-y-6">
      {settings && (
        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
          <span className="font-medium">Dry-run global</span>
          {settings.dry_run ? (
            <span className="rounded bg-amber-200 px-2 py-0.5 text-amber-900">
              Simulation only (no blocking)
            </span>
          ) : (
            <span className="rounded bg-gray-200 px-2 py-0.5">Production</span>
          )}
          <span className="text-gray-600">source: {settings.dry_run_source}</span>
          {settings.redis_override_available ? (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.dry_run}
                disabled={savingDry}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              Activer dry-run (Redis)
            </label>
          ) : (
            <span className="text-gray-500">Override Redis indisponible — variable env</span>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ruleset</label>
          <input
            className="border rounded px-2 py-1 w-48"
            placeholder="default"
            value={ruleset}
            onChange={(e) => setRuleset(e.target.value)}
          />
        </div>
        <button
          type="button"
          className="rounded bg-gray-900 text-white px-3 py-1 text-sm"
          onClick={() => load()}
        >
          Filtrer
        </button>
        <button
          type="button"
          className="rounded border border-red-300 text-red-700 px-3 py-1 text-sm"
          onClick={panic}
        >
          Désactiver toutes les règles
        </button>
      </div>

      {err && <p className="text-red-600 text-sm">{err}</p>}
      {loading ? (
        <p>Chargement…</p>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-100 text-left">
                <th className="p-2">Actif</th>
                <th className="p-2">Nom</th>
                <th className="p-2">Priorité</th>
                <th className="p-2">Action</th>
                <th className="p-2">Ruleset</th>
                <th className="p-2">Version</th>
                <th className="p-2">Maj</th>
                <th className="p-2"></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((row) => (
                <tr key={row.id} className="border-t border-gray-100">
                  <td className="p-2">
                    <input
                      type="checkbox"
                      checked={row.is_active}
                      onChange={() => toggle(row.id, !row.is_active)}
                    />
                  </td>
                  <td className="p-2 font-medium">{row.name || '—'}</td>
                  <td className="p-2">{row.priority}</td>
                  <td className="p-2">
                    <span
                      className={
                        row.action === 'BLOCK'
                          ? 'text-red-700 font-semibold'
                          : row.action === 'STEP_UP'
                            ? 'text-amber-700'
                            : ''
                      }
                    >
                      {row.action}
                    </span>
                  </td>
                  <td className="p-2">{row.ruleset}</td>
                  <td className="p-2">{row.version}</td>
                  <td className="p-2 text-gray-500">
                    {row.updated_at
                      ? new Date(row.updated_at).toLocaleString('fr-FR')
                      : '—'}
                  </td>
                  <td className="p-2">
                    <Link
                      className="text-blue-600 hover:underline"
                      href={`/admin/risk/rules/${row.id}`}
                    >
                      Éditer
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

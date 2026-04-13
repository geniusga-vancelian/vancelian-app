'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'

type Rule = {
  id: string
  name: string | null
  priority: number
  conditions: Record<string, unknown>
  action: string
  enabled: boolean
  is_active: boolean
  ruleset: string
  version: number
}

export default function RiskRuleEditPage() {
  const params = useParams()
  const router = useRouter()
  const id = params?.id as string
  const [rule, setRule] = useState<Rule | null>(null)
  const [jsonText, setJsonText] = useState('{}')
  const [jsonErr, setJsonErr] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [sim, setSim] = useState({
    user_id: 1,
    device_id: 'test-device',
    action_type: 'wallet_transfer',
    country: 'FR',
    amount: '',
    device_trust_level: 'HIGH',
    simulate_mode: 'runtime' as 'runtime' | 'isolated',
    baseline_override_json: '',
    profile_override_json: '',
    now_utc: '',
    simulation_seed: '',
    deterministic: false,
  })
  const [simOut, setSimOut] = useState<Record<string, unknown> | null>(null)
  const [valOut, setValOut] = useState<{ valid: boolean; error?: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const res = await fetch(`/api/admin/risk/rules/${id}`, { credentials: 'include' })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText)
      const r: Rule = await res.json()
      setRule(r)
      setJsonText(JSON.stringify(r.conditions || {}, null, 2))
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const onJsonChange = (v: string) => {
    setJsonText(v)
    try {
      JSON.parse(v)
      setJsonErr(null)
    } catch {
      setJsonErr('JSON invalide')
    }
  }

  const validate = async () => {
    setValOut(null)
    let conditions: Record<string, unknown>
    try {
      conditions = JSON.parse(jsonText)
    } catch {
      setValOut({ valid: false, error: 'JSON invalide' })
      return
    }
    const res = await fetch(`/api/admin/risk/rules/validate`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conditions }),
    })
    setValOut(await res.json())
  }

  const simulate = async () => {
    setSimOut(null)
    let conditions: Record<string, unknown>
    try {
      conditions = JSON.parse(jsonText)
    } catch {
      setSimOut({ error: 'JSON conditions invalide' })
      return
    }
    const amount = sim.amount.trim() ? parseFloat(sim.amount.replace(',', '.')) : undefined
    let baseline_override: Record<string, unknown> | undefined
    if (sim.simulate_mode === 'isolated' && sim.baseline_override_json.trim()) {
      try {
        baseline_override = JSON.parse(sim.baseline_override_json) as Record<string, unknown>
      } catch {
        setSimOut({ error: 'baseline_override JSON invalide' })
        return
      }
    }
    let profile_override: Record<string, unknown> | undefined
    if (sim.simulate_mode === 'isolated' && sim.profile_override_json.trim()) {
      try {
        profile_override = JSON.parse(sim.profile_override_json) as Record<string, unknown>
      } catch {
        setSimOut({ error: 'profile_override JSON invalide' })
        return
      }
    }
    const isolatedExtra =
      sim.simulate_mode === 'isolated'
        ? {
            ...(baseline_override ? { baseline_override } : {}),
            ...(profile_override ? { profile_override } : {}),
            ...(sim.now_utc.trim() ? { now_utc: sim.now_utc.trim() } : {}),
            ...(sim.simulation_seed.trim()
              ? { simulation_seed: parseInt(sim.simulation_seed, 10) }
              : {}),
            ...(sim.deterministic ? { deterministic: true } : {}),
          }
        : {}
    const res = await fetch(`/api/admin/risk/rules/simulate`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rule_id: id,
        conditions,
        user_id: Number(sim.user_id) || 1,
        device_id: sim.device_id,
        action_type: sim.action_type,
        country: sim.country || null,
        amount_eur: amount,
        device_trust_level: sim.device_trust_level,
        simulate_mode: sim.simulate_mode,
        ...isolatedExtra,
      }),
    })
    setSimOut(await res.json())
  }

  const save = async () => {
    if (!rule) return
    let conditions: Record<string, unknown>
    try {
      conditions = JSON.parse(jsonText)
    } catch {
      setErr('Conditions JSON invalides')
      return
    }
    if (rule.action === 'BLOCK') {
      if (!confirm('Cette règle peut bloquer des utilisateurs en production. Confirmer ?')) return
    }
    const action = rule.action
    const res = await fetch(`/api/admin/risk/rules/${id}`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: rule.name,
        priority: rule.priority,
        action,
        is_active: rule.is_active,
        ruleset: rule.ruleset,
        conditions,
      }),
    })
    if (!res.ok) {
      setErr((await res.json().catch(() => ({}))).detail || 'Erreur sauvegarde')
      return
    }
    router.refresh()
    load()
  }

  const duplicate = async () => {
    const res = await fetch(`/api/admin/risk/rules/${id}/duplicate`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!res.ok) {
      setErr('Duplication échouée')
      return
    }
    const created: Rule = await res.json()
    router.push(`/admin/risk/rules/${created.id}`)
  }

  if (loading || !rule) {
    return <p className="text-sm text-gray-600">{loading ? 'Chargement…' : err || 'Introuvable'}</p>
  }

  return (
    <div className="space-y-8 max-w-4xl">
      {err && <p className="text-red-600 text-sm">{err}</p>}

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm">
          <span className="text-gray-600">Nom</span>
          <input
            className="mt-1 w-full border rounded px-2 py-1"
            value={rule.name || ''}
            onChange={(e) => setRule({ ...rule, name: e.target.value })}
          />
        </label>
        <label className="block text-sm">
          <span className="text-gray-600">Priorité</span>
          <input
            type="number"
            className="mt-1 w-full border rounded px-2 py-1"
            value={rule.priority}
            onChange={(e) => setRule({ ...rule, priority: parseInt(e.target.value, 10) || 0 })}
          />
        </label>
        <label className="block text-sm">
          <span className="text-gray-600">Action</span>
          <select
            id="actionSel"
            className="mt-1 w-full border rounded px-2 py-1"
            value={rule.action}
            onChange={(e) => setRule({ ...rule, action: e.target.value })}
          >
            <option value="ALLOW">ALLOW</option>
            <option value="STEP_UP">STEP_UP</option>
            <option value="BLOCK">BLOCK</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="text-gray-600">Ruleset</span>
          <input
            className="mt-1 w-full border rounded px-2 py-1"
            value={rule.ruleset}
            onChange={(e) => setRule({ ...rule, ruleset: e.target.value })}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={rule.is_active}
            onChange={(e) => setRule({ ...rule, is_active: e.target.checked })}
          />
          is_active
        </label>
        <div className="text-sm text-gray-500">Version {rule.version}</div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <h2 className="font-semibold">Conditions (JSON)</h2>
          <button
            type="button"
            className="text-sm text-blue-600 hover:underline"
            onClick={() => setJsonText((t) => JSON.stringify(JSON.parse(t || '{}'), null, 2))}
          >
            Formater
          </button>
        </div>
        {jsonErr && <p className="text-amber-700 text-sm mb-1">{jsonErr}</p>}
        <textarea
          className="w-full h-56 font-mono text-sm border rounded p-2"
          value={jsonText}
          onChange={(e) => onJsonChange(e.target.value)}
        />
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            className="rounded border px-3 py-1 text-sm"
            onClick={validate}
          >
            Validate Rule
          </button>
          {valOut && (
            <span className={valOut.valid ? 'text-green-700 text-sm' : 'text-red-600 text-sm'}>
              {valOut.valid ? 'Valide' : valOut.error || 'Invalide'}
            </span>
          )}
        </div>
      </div>

      <div className="border rounded p-4 bg-white space-y-3">
        <h2 className="font-semibold">Test this rule (simulate)</h2>
        <div className="text-sm space-y-2">
          <label className="block">
            <span className="text-gray-600">simulate_mode</span>
            <select
              className="mt-1 w-full max-w-xs border rounded px-2 py-1"
              value={sim.simulate_mode}
              onChange={(e) =>
                setSim({ ...sim, simulate_mode: e.target.value as 'runtime' | 'isolated' })
              }
            >
              <option value="runtime">Runtime</option>
              <option value="isolated">Isolated</option>
            </select>
          </label>
          {sim.simulate_mode === 'isolated' && (
            <p className="text-xs text-gray-600 max-w-xl">
              Deterministic simulation. No Redis cache, no persisted baseline, no side effects.
            </p>
          )}
          {sim.simulate_mode === 'isolated' && (
            <details className="border rounded p-2 bg-gray-50">
              <summary className="cursor-pointer text-gray-700 font-medium">
                baseline_override (JSON, optional)
              </summary>
              <textarea
                className="mt-2 w-full font-mono text-xs border rounded p-2 h-32"
                placeholder='{"avg_hour_of_day": 10.5, "baseline_sample_count": 50, ...}'
                value={sim.baseline_override_json}
                onChange={(e) => setSim({ ...sim, baseline_override_json: e.target.value })}
              />
            </details>
          )}
          {sim.simulate_mode === 'isolated' && (
            <details className="border rounded p-2 bg-gray-50">
              <summary className="cursor-pointer text-gray-700 font-medium">
                profile_override (F.5.2, JSON, optional)
              </summary>
              <textarea
                className="mt-2 w-full font-mono text-xs border rounded p-2 h-28"
                placeholder='{"is_known_device": true, "last_country": "FR", "last_ip": "1.2.3.4", "device_count_24h": 1}'
                value={sim.profile_override_json}
                onChange={(e) => setSim({ ...sim, profile_override_json: e.target.value })}
              />
            </details>
          )}
          {sim.simulate_mode === 'isolated' && (
            <div className="grid gap-2 md:grid-cols-2 text-xs max-w-2xl">
              <label>
                now_utc (ISO, optional)
                <input
                  className="mt-1 w-full border rounded px-2 py-1 font-mono"
                  placeholder="2026-01-01T12:00:00Z"
                  value={sim.now_utc}
                  onChange={(e) => setSim({ ...sim, now_utc: e.target.value })}
                />
              </label>
              <label>
                simulation_seed (optional)
                <input
                  className="mt-1 w-full border rounded px-2 py-1"
                  placeholder="12345"
                  value={sim.simulation_seed}
                  onChange={(e) => setSim({ ...sim, simulation_seed: e.target.value })}
                />
              </label>
              <label className="flex items-center gap-2 md:col-span-2">
                <input
                  type="checkbox"
                  checked={sim.deterministic}
                  onChange={(e) => setSim({ ...sim, deterministic: e.target.checked })}
                />
                deterministic (horloge implicite désactivée si now_utc / champs heure absents)
              </label>
            </div>
          )}
        </div>
        <div className="grid gap-2 md:grid-cols-2 text-sm">
          <label>
            user_id
            <input
              type="number"
              className="w-full border rounded px-2 py-1"
              value={sim.user_id}
              onChange={(e) => setSim({ ...sim, user_id: Number(e.target.value) })}
            />
          </label>
          <label>
            device_id
            <input
              className="w-full border rounded px-2 py-1"
              value={sim.device_id}
              onChange={(e) => setSim({ ...sim, device_id: e.target.value })}
            />
          </label>
          <label>
            action_type
            <input
              className="w-full border rounded px-2 py-1"
              value={sim.action_type}
              onChange={(e) => setSim({ ...sim, action_type: e.target.value })}
            />
          </label>
          <label>
            country
            <input
              className="w-full border rounded px-2 py-1"
              value={sim.country}
              onChange={(e) => setSim({ ...sim, country: e.target.value })}
            />
          </label>
          <label>
            amount (EUR)
            <input
              className="w-full border rounded px-2 py-1"
              value={sim.amount}
              onChange={(e) => setSim({ ...sim, amount: e.target.value })}
            />
          </label>
          <label>
            device_trust_level
            <select
              className="w-full border rounded px-2 py-1"
              value={sim.device_trust_level}
              onChange={(e) => setSim({ ...sim, device_trust_level: e.target.value })}
            >
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
          </label>
        </div>
        <button
          type="button"
          className="rounded bg-gray-900 text-white px-3 py-1 text-sm"
          onClick={simulate}
        >
          Simuler
        </button>
        {simOut && (
          <div className="mt-3 text-sm space-y-2 border-t pt-3">
            {sim.simulate_mode === 'isolated' && !('error' in simOut && simOut.error) && (
              <div className="flex flex-wrap gap-2 items-center">
                <span className="rounded bg-violet-100 text-violet-900 px-2 py-0.5 text-xs font-medium">
                  Isolated
                </span>
                {typeof simOut.used_cache === 'boolean' && (
                  <span className="rounded bg-slate-100 text-slate-800 px-2 py-0.5 text-xs">
                    used_cache={String(simOut.used_cache)}
                  </span>
                )}
                {typeof simOut.used_baseline === 'boolean' && (
                  <span className="rounded bg-slate-100 text-slate-800 px-2 py-0.5 text-xs">
                    used_baseline={String(simOut.used_baseline)}
                  </span>
                )}
                {typeof simOut.used_profile_override === 'boolean' && (
                  <span className="rounded bg-slate-100 text-slate-800 px-2 py-0.5 text-xs">
                    used_profile_override={String(simOut.used_profile_override)}
                  </span>
                )}
              </div>
            )}
            <pre className="bg-gray-50 p-2 rounded overflow-x-auto text-xs">
              {JSON.stringify(simOut, null, 2)}
            </pre>
            {Array.isArray(simOut.matched_conditions) && (
              <div>
                <span className="font-medium">Matched:</span>
                <ul className="list-disc pl-5">
                  {(simOut.matched_conditions as string[]).map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
            {Array.isArray(simOut.risk_reason) && simOut.risk_reason.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {(simOut.risk_reason as string[]).map((r) => (
                  <span key={r} className="rounded bg-blue-100 text-blue-900 px-2 py-0.5 text-xs">
                    {r}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded bg-blue-700 text-white px-4 py-2 text-sm"
          onClick={save}
        >
          Enregistrer
        </button>
        <button type="button" className="rounded border px-4 py-2 text-sm" onClick={duplicate}>
          Duplicate rule
        </button>
        <a href="/admin/risk/rules" className="text-sm text-gray-600 underline self-center">
          Retour liste
        </a>
      </div>
    </div>
  )
}

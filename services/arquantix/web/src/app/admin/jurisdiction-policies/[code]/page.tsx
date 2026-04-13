'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface CountryRow {
  country_iso2: string
  display_name_en: string
  phone_country_code: string
  allow_residence: boolean
  allow_phone_country_code: boolean
  allow_nationality: boolean
  is_default_residence: boolean
  is_default_phone: boolean
  position: number
}

interface AdminJurisdictionRow {
  id: string
  code: string
  name: string
}

interface AdminRegistrationFlowRow {
  id: string
  jurisdiction_id: string
  name: string
  version: number
  status: string
}

interface DetailResponse {
  jurisdiction: { code: string; name: string }
  summary: {
    residence_country_count: number
    phone_country_count: number
    nationality_country_count: number
  }
  settings: {
    inherit_phone_countries_from_residence: boolean
    default_residence_iso2: string | null
    default_phone_iso2: string | null
  }
  countries: CountryRow[]
}

export default function JurisdictionPolicyDetailPage() {
  const params = useParams()
  const code = decodeURIComponent((params?.code as string | undefined) ?? '')
  const [detail, setDetail] = useState<DetailResponse | null>(null)
  const [rows, setRows] = useState<CountryRow[]>([])
  const [inherit, setInherit] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [registrationFlows, setRegistrationFlows] = useState<AdminRegistrationFlowRow[]>([])
  const [registrationFlowsLoading, setRegistrationFlowsLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const r = await fetch(`${BACKEND}/api/admin/jurisdiction-policies/${encodeURIComponent(code)}`)
      if (!r.ok) throw new Error(await r.text())
      const d: DetailResponse = await r.json()
      setDetail(d)
      setRows(d.countries.map(c => ({ ...c, allow_nationality: c.allow_nationality ?? false })))
      setInherit(!!d.settings.inherit_phone_countries_from_residence)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [code])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!code) return
    setRegistrationFlowsLoading(true)
    Promise.all([
      fetch(`${BACKEND}/api/admin/registration/jurisdictions`).then(r => r.json()),
      fetch(`${BACKEND}/api/admin/registration/flows`).then(r => r.json()),
    ])
      .then(([juris, flows]) => {
        const j = (juris as AdminJurisdictionRow[]).find(
          x => x.code.toUpperCase() === code.toUpperCase(),
        )
        if (!j) {
          setRegistrationFlows([])
          return
        }
        setRegistrationFlows(
          (flows as AdminRegistrationFlowRow[]).filter(f => f.jurisdiction_id === j.id),
        )
      })
      .catch(() => setRegistrationFlows([]))
      .finally(() => setRegistrationFlowsLoading(false))
  }, [code])

  const patchSettings = async (body: Record<string, unknown>) => {
    setSaving(true)
    setMsg(null)
    setErr(null)
    try {
      const r = await fetch(
        `${BACKEND}/api/admin/jurisdiction-policies/${encodeURIComponent(code)}/settings`,
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
      )
      if (!r.ok) throw new Error(await r.text())
      const d: DetailResponse = await r.json()
      setDetail(d)
      setRows(d.countries.map(c => ({ ...c, allow_nationality: c.allow_nationality ?? false })))
      setInherit(!!d.settings.inherit_phone_countries_from_residence)
      setMsg('Settings saved.')
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const saveCountries = async () => {
    setSaving(true)
    setMsg(null)
    setErr(null)
    try {
      const payload = {
        rows: rows.map((r, i) => ({
          country_iso2: r.country_iso2,
          allow_residence: r.allow_residence,
          allow_phone_country_code: r.allow_phone_country_code,
          allow_nationality: r.allow_nationality,
          is_default_residence: r.is_default_residence,
          is_default_phone: r.is_default_phone,
          position: r.position ?? i,
        })),
      }
      const res = await fetch(
        `${BACKEND}/api/admin/jurisdiction-policies/${encodeURIComponent(code)}/countries`,
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
      )
      if (!res.ok) throw new Error(await res.text())
      const d: DetailResponse = await res.json()
      setDetail(d)
      setRows(d.countries.map(c => ({ ...c, allow_nationality: c.allow_nationality ?? false })))
      setMsg('Country policies saved.')
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const applyPreset = async (preset: string) => {
    setSaving(true)
    setMsg(null)
    setErr(null)
    try {
      const r = await fetch(
        `${BACKEND}/api/admin/jurisdiction-policies/${encodeURIComponent(code)}/apply-preset`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ preset }) },
      )
      if (!r.ok) throw new Error(await r.text())
      const d: DetailResponse = await r.json()
      setDetail(d)
      setRows(d.countries.map(c => ({ ...c, allow_nationality: c.allow_nationality ?? false })))
      setInherit(!!d.settings.inherit_phone_countries_from_residence)
      setMsg(`Preset « ${preset} » applied.`)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const setDefaultResidence = (iso2: string) => {
    setRows(prev => prev.map(r => ({
      ...r,
      is_default_residence: r.country_iso2 === iso2 && r.allow_residence,
    })))
  }

  const setDefaultPhone = (iso2: string) => {
    setRows(prev => prev.map(r => ({
      ...r,
      is_default_phone: r.country_iso2 === iso2
        && (inherit ? r.allow_residence : r.allow_phone_country_code),
    })))
  }

  const residenceOptions = rows.filter(r => r.allow_residence)
  const phoneOptions = inherit
    ? residenceOptions
    : rows.filter(r => r.allow_phone_country_code)

  if (loading || !detail) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-bold text-gray-900">{detail.jurisdiction.name}</h1>
            <Badge variant="outline" className="font-mono">{detail.jurisdiction.code}</Badge>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {String(detail.summary.residence_country_count ?? 0)} résidence ·{' '}
            {String(detail.summary.phone_country_count ?? 0)} téléphone ·{' '}
            {String(detail.summary.nationality_country_count ?? 0)} nationalité
          </p>
          <p className="text-xs text-gray-500 max-w-xl">
            Résidence et téléphone dépendent de la juridiction. La nationalité peut rester plus large (liste distincte).
          </p>
        </div>
        <Link href="/admin/jurisdiction-policies">
          <Button variant="outline" size="sm">Back to list</Button>
        </Link>
      </div>

      {err && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800 whitespace-pre-wrap">{err}</div>}
      {msg && <div className="p-3 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-900">{msg}</div>}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Flux d’inscription (registration)</CardTitle>
          <p className="text-xs text-gray-500 font-normal mt-1">
            Ajoutez des écrans Notifications ou Face ID dans l’éditeur de flux : boutons « + Notifications » et « + Face ID », puis placez l’étape dans le parcours. L’app enregistre le choix au tap sur le bouton (valeur booléenne sur <span className="font-mono">decision_slug</span>).
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {registrationFlowsLoading ? (
            <p className="text-sm text-gray-500">Chargement des flux…</p>
          ) : registrationFlows.length === 0 ? (
            <p className="text-sm text-gray-600">
              Aucun flux d’inscription rattaché à cette juridiction. Créez-en un depuis{' '}
              <Link href="/admin/registration" className="text-blue-600 underline">Registration Flows</Link>.
            </p>
          ) : (
            <ul className="space-y-2">
              {registrationFlows.map(f => (
                <li
                  key={f.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border border-gray-200 bg-gray-50/80 px-3 py-2"
                >
                  <div>
                    <div className="font-medium text-sm text-gray-900">{f.name}</div>
                    <div className="text-xs text-gray-500 font-mono">
                      v{f.version} · {f.status}
                    </div>
                  </div>
                  <Link href={`/admin/registration/flows/${f.id}/edit`}>
                    <Button size="sm" variant="outline" className="w-full sm:w-auto">
                      Éditer le flux
                    </Button>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-medium text-sm">Inherit phone list from residence</div>
              <p className="text-xs text-gray-500">
                Si activé, les indicatifs autorisés suivent les pays « résidence » (sauf overrides futurs côté flags téléphone).
              </p>
            </div>
            <Switch
              checked={inherit}
              onCheckedChange={v => {
                setInherit(v)
                patchSettings({ inherit_phone_countries_from_residence: v })
              }}
              disabled={saving}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <div className="text-xs font-medium text-gray-600 mb-1">Default residence (ISO2)</div>
              <Select
                value={detail.settings.default_residence_iso2 ?? '_none'}
                onValueChange={v => patchSettings({ default_residence_iso2: v === '_none' ? null : v })}
                disabled={saving || residenceOptions.length === 0}
              >
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">— none —</SelectItem>
                  {residenceOptions.map(r => (
                    <SelectItem key={r.country_iso2} value={r.country_iso2}>
                      {r.country_iso2} — {r.display_name_en}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-xs font-medium text-gray-600 mb-1">Default phone (ISO2)</div>
              <Select
                value={detail.settings.default_phone_iso2 ?? '_none'}
                onValueChange={v => patchSettings({ default_phone_iso2: v === '_none' ? null : v })}
                disabled={saving || phoneOptions.length === 0}
              >
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">— none —</SelectItem>
                  {phoneOptions.map(r => (
                    <SelectItem key={r.country_iso2} value={r.country_iso2}>
                      {r.country_iso2} — {r.display_name_en}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Bulk actions (explicit presets)</CardTitle>
          <p className="text-xs text-gray-500 font-normal">
            Les presets sont déterministes côté serveur (listes EU/UAE explicites, pas d’inférence magique).
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={saving} onClick={() => applyPreset('eu_explicit')}>Load EU preset</Button>
          <Button size="sm" variant="outline" disabled={saving} onClick={() => applyPreset('eu_from_directory')}>EU from directory</Button>
          <Button size="sm" variant="outline" disabled={saving} onClick={() => applyPreset('uae_explicit')}>Load UAE preset</Button>
          <Button size="sm" variant="outline" disabled={saving} onClick={() => applyPreset('mirror_phone_to_residence')}>Set phone = residence</Button>
          <Button size="sm" variant="outline" disabled={saving} onClick={() => applyPreset('apply_residence_to_phone')}>Expand phone for residence</Button>
          <Button size="sm" variant="destructive" disabled={saving} onClick={() => applyPreset('clear')}>Clear all</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 flex flex-row items-center justify-between">
          <CardTitle className="text-base">Country policy table</CardTitle>
          <Button size="sm" disabled={saving} onClick={saveCountries}>Save changes</Button>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs text-gray-600">
                <th className="px-2 py-2">Country</th>
                <th className="px-2 py-2">ISO2</th>
                <th className="px-2 py-2">Dial</th>
                <th className="px-2 py-2 text-center">Residence</th>
                <th className="px-2 py-2 text-center">Phone</th>
                <th className="px-2 py-2 text-center">Nationality</th>
                <th className="px-2 py-2 text-center">Def. res.</th>
                <th className="px-2 py-2 text-center">Def. phone</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.country_iso2} className="border-b border-gray-100">
                  <td className="px-2 py-2">{r.display_name_en}</td>
                  <td className="px-2 py-2 font-mono">{r.country_iso2}</td>
                  <td className="px-2 py-2 font-mono text-gray-600">{r.phone_country_code}</td>
                  <td className="px-2 py-2 text-center">
                    <Switch
                      checked={r.allow_residence}
                      onCheckedChange={v => {
                        setRows(prev => prev.map(x => x.country_iso2 === r.country_iso2
                          ? {
                              ...x,
                              allow_residence: v,
                              is_default_residence: v ? x.is_default_residence : false,
                            }
                          : x))
                      }}
                    />
                  </td>
                  <td className="px-2 py-2 text-center">
                    <Switch
                      checked={r.allow_phone_country_code}
                      disabled={inherit}
                      onCheckedChange={v => {
                        setRows(prev => prev.map(x => x.country_iso2 === r.country_iso2
                          ? {
                              ...x,
                              allow_phone_country_code: v,
                              is_default_phone: v ? x.is_default_phone : false,
                            }
                          : x))
                      }}
                    />
                  </td>
                  <td className="px-2 py-2 text-center">
                    <Switch
                      checked={r.allow_nationality}
                      onCheckedChange={v => {
                        setRows(prev => prev.map(x => x.country_iso2 === r.country_iso2
                          ? { ...x, allow_nationality: v }
                          : x))
                      }}
                    />
                  </td>
                  <td className="px-2 py-2 text-center">
                    <input
                      type="radio"
                      name="defres"
                      checked={r.is_default_residence}
                      disabled={!r.allow_residence}
                      onChange={() => setDefaultResidence(r.country_iso2)}
                    />
                  </td>
                  <td className="px-2 py-2 text-center">
                    <input
                      type="radio"
                      name="defphone"
                      checked={r.is_default_phone}
                      disabled={inherit ? !r.allow_residence : !r.allow_phone_country_code}
                      onChange={() => setDefaultPhone(r.country_iso2)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && (
            <p className="p-4 text-sm text-gray-500">Aucun pays — utilisez un preset ou importez via API.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

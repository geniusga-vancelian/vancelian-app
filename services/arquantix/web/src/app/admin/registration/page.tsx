'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface JurisdictionPolicySummary {
  residence_country_count: number
  phone_country_count: number
  nationality_country_count: number
  default_residence_iso2: string | null
  default_phone_iso2: string | null
  inherit_phone_countries_from_residence: boolean
  has_policy_rows: boolean
}

interface Flow {
  id: string
  jurisdiction_id: string
  name: string
  version: number
  status: string
  entrypoint_type: string
  published_at: string | null
  can_publish?: boolean
  health_error_count?: number
  health_warning_count?: number
  jurisdiction_policy_summary?: JurisdictionPolicySummary | null
}

interface Jurisdiction {
  id: string
  code: string
  name: string
  is_active: boolean
}

export default function RegistrationAdminPage() {
  const [flows, setFlows] = useState<Flow[]>([])
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${BACKEND}/api/admin/registration/flows?include_health=true`).then(r => r.json()),
      fetch(`${BACKEND}/api/admin/registration/jurisdictions`).then(r => r.json()),
    ])
      .then(([f, j]) => {
        setFlows(f)
        setJurisdictions(j)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const getJurisdiction = (jid: string) =>
    jurisdictions.find(j => j.id === jid)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Registration Flows</h1>
          <p className="text-sm text-gray-500">
            {flows.length} flows across {jurisdictions.length} jurisdictions
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/jurisdiction-policies">
            <Button variant="default" size="sm">Jurisdiction Policies</Button>
          </Link>
          <Link href="/admin/country-directory">
            <Button variant="outline" size="sm">Country Directory</Button>
          </Link>
          <Link href="/admin/registration/field-definitions">
            <Button variant="outline" size="sm">Field Definitions Catalog</Button>
          </Link>
          <Link href="/admin/registration/sessions">
            <Button variant="outline" size="sm">Sessions (audit)</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {flows.map(flow => {
          const j = getJurisdiction(flow.jurisdiction_id)
          return (
            <Card key={flow.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <CardTitle className="text-base">{flow.name}</CardTitle>
                  <div className="flex flex-wrap gap-1 justify-end">
                    <Badge className={
                      flow.status === 'active' ? 'bg-green-100 text-green-700'
                      : flow.status === 'draft' ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-gray-100 text-gray-600'
                    }>
                      {flow.status}
                    </Badge>
                    {flow.can_publish !== undefined && !flow.can_publish && (
                      <Badge className="bg-red-50 text-red-700 border border-red-200" variant="outline">Blocked</Badge>
                    )}
                    {flow.can_publish !== undefined && flow.can_publish && (flow.health_warning_count ?? 0) > 0 && (
                      <Badge className="bg-amber-50 text-amber-900 border border-amber-200" variant="outline">
                        {flow.health_warning_count} warnings
                      </Badge>
                    )}
                    {flow.can_publish !== undefined && flow.can_publish && (flow.health_warning_count ?? 0) === 0 && (
                      <Badge className="bg-emerald-50 text-emerald-800 border border-emerald-200" variant="outline">Ready</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>Jurisdiction</span>
                    <Badge variant="outline">{j?.code || '—'}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Version</span>
                    <span className="font-mono">v{flow.version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Type</span>
                    <span>{flow.entrypoint_type}</span>
                  </div>
                  {(flow.health_error_count != null || flow.health_warning_count != null) && (
                    <div className="flex justify-between text-xs">
                      <span>Health</span>
                      <span className="font-mono text-gray-700">
                        {flow.health_error_count ?? 0} err · {flow.health_warning_count ?? 0} warn
                      </span>
                    </div>
                  )}
                  {flow.jurisdiction_policy_summary && (
                    <div className="mt-2 rounded-md border border-gray-200 bg-gray-50/80 px-2 py-2 text-xs text-gray-700 space-y-1">
                      <div className="font-semibold text-gray-800">Jurisdiction policy</div>
                      <div className="flex justify-between gap-2">
                        <span>Residence countries</span>
                        <span className="font-mono">{flow.jurisdiction_policy_summary.residence_country_count}</span>
                      </div>
                      <div className="flex justify-between gap-2">
                        <span>Phone countries</span>
                        <span className="font-mono">{flow.jurisdiction_policy_summary.phone_country_count}</span>
                      </div>
                      <div className="flex justify-between gap-2">
                        <span>Nationality countries</span>
                        <span className="font-mono">{flow.jurisdiction_policy_summary.nationality_country_count ?? 0}</span>
                      </div>
                      <div className="flex justify-between gap-2">
                        <span>Default phone</span>
                        <span className="font-mono">{flow.jurisdiction_policy_summary.default_phone_iso2 ?? '—'}</span>
                      </div>
                      {flow.jurisdiction_policy_summary.inherit_phone_countries_from_residence && (
                        <Badge variant="outline" className="text-[10px] mt-1">Phone inherits from residence</Badge>
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-4 flex flex-col gap-2">
                  {j && (
                    <Link href={`/admin/jurisdiction-policies/${encodeURIComponent(j.code)}`}>
                      <Button size="sm" variant="secondary" className="w-full">Edit jurisdiction policy</Button>
                    </Link>
                  )}
                  <div className="flex gap-2">
                  <Link href={`/admin/registration/flows/${flow.id}/edit`} className="flex-1">
                    <Button size="sm" variant="outline" className="w-full">Edit</Button>
                  </Link>
                  <Link href={`/admin/registration/flows/${flow.id}/preview`} className="flex-1">
                    <Button size="sm" className="w-full">Preview</Button>
                  </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

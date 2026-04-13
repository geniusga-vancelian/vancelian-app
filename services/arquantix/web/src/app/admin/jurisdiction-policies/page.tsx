'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface Row {
  jurisdiction_id: string
  code: string
  name: string
  is_active: boolean
  residence_country_count: number
  phone_country_count: number
  nationality_country_count: number
  default_residence_iso2: string | null
  default_phone_iso2: string | null
  inherit_phone_countries_from_residence: boolean
  has_policy_rows: boolean
}

export default function JurisdictionPoliciesListPage() {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/jurisdiction-policies`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: Row[]) => {
        setRows(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(e => {
        setError((e as Error).message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jurisdiction policies</h1>
          <p className="text-sm text-gray-500">
            Pays de résidence et indicatifs téléphone par juridiction (source de vérité : base de données).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/country-directory">
            <Button variant="outline" size="sm">Country directory</Button>
          </Link>
          <Link href="/admin/registration">
            <Button variant="outline" size="sm">Registration flows</Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {rows.map(row => (
          <Card key={row.code} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-base font-semibold">{row.name}</CardTitle>
                <Badge variant="outline" className="font-mono">{row.code}</Badge>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-gray-600 space-y-2">
              <div className="flex justify-between">
                <span>Residence countries</span>
                <span className="font-mono">{row.residence_country_count}</span>
              </div>
              <div className="flex justify-between">
                <span>Phone countries</span>
                <span className="font-mono">{row.phone_country_count}</span>
              </div>
              <div className="flex justify-between">
                <span>Nationality countries</span>
                <span className="font-mono">{row.nationality_country_count ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Default residence</span>
                <span className="font-mono">{row.default_residence_iso2 ?? '—'}</span>
              </div>
              <div className="flex justify-between">
                <span>Default phone</span>
                <span className="font-mono">{row.default_phone_iso2 ?? '—'}</span>
              </div>
              {row.inherit_phone_countries_from_residence && (
                <Badge variant="outline" className="text-[10px]">Phone ← residence</Badge>
              )}
              {!row.has_policy_rows && (
                <p className="text-xs text-amber-800 bg-amber-50 border border-amber-100 rounded px-2 py-1">
                  Aucune ligne de policy — utilisez les presets ou importez des pays.
                </p>
              )}
              <Link href={`/admin/jurisdiction-policies/${encodeURIComponent(row.code)}`}>
                <Button size="sm" className="w-full mt-2">Edit</Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

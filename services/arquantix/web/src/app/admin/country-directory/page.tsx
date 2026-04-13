'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface CountryRow {
  iso2: string
  iso3: string
  display_name_en: string
  display_name_fr: string
  phone_country_code: string
  is_active: boolean
}

export default function CountryDirectoryPage() {
  const [rows, setRows] = useState<CountryRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/country-directory`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: CountryRow[]) => {
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
          <h1 className="text-2xl font-bold text-gray-900">Country directory</h1>
          <p className="text-sm text-gray-500">
            Référentiel global (lecture seule pour l’instant). Les policies juridictionnelles référencent ces codes ISO2.
          </p>
        </div>
        <Link href="/admin/jurisdiction-policies">
          <Button variant="outline" size="sm">Jurisdiction policies</Button>
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{rows.length} countries</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs text-gray-600">
                <th className="px-3 py-2 font-medium">ISO2</th>
                <th className="px-3 py-2 font-medium">ISO3</th>
                <th className="px-3 py-2 font-medium">Name (EN)</th>
                <th className="px-3 py-2 font-medium">Name (FR)</th>
                <th className="px-3 py-2 font-medium">Dial</th>
                <th className="px-3 py-2 font-medium">Active</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.iso2} className="border-b border-gray-100 hover:bg-gray-50/80">
                  <td className="px-3 py-2 font-mono">{r.iso2}</td>
                  <td className="px-3 py-2 font-mono text-gray-600">{r.iso3}</td>
                  <td className="px-3 py-2">{r.display_name_en}</td>
                  <td className="px-3 py-2 text-gray-600">{r.display_name_fr}</td>
                  <td className="px-3 py-2 font-mono">{r.phone_country_code}</td>
                  <td className="px-3 py-2">
                    {r.is_active
                      ? <Badge className="bg-green-100 text-green-800">yes</Badge>
                      : <Badge variant="outline">no</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}

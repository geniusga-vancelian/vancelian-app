'use client'

import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface FieldDef {
  id: string
  slug: string
  slug_snake: string
  field_name_en: string
  label: string
  field_type: string
  category: string | null
  is_active: boolean
  component_type_default: string | null
  required_default: boolean | null
  options: unknown[] | null
  usage_count: number
}

export default function FieldDefinitionsPage() {
  const [fields, setFields] = useState<FieldDef[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterCategory, setFilterCategory] = useState('')

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/registration/field-definitions`)
      .then(r => r.json())
      .then(d => { setFields(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const categories = useMemo(() =>
    [...new Set(fields.map(f => f.category).filter(Boolean))] as string[],
  [fields])

  const fieldTypes = useMemo(() =>
    [...new Set(fields.map(f => f.field_type).filter(Boolean))] as string[],
  [fields])

  const filtered = useMemo(() => {
    let result = fields
    if (search) {
      const s = search.toLowerCase()
      result = result.filter(f =>
        f.slug.toLowerCase().includes(s) ||
        f.label.toLowerCase().includes(s) ||
        f.field_name_en.toLowerCase().includes(s)
      )
    }
    if (filterType) result = result.filter(f => f.field_type === filterType)
    if (filterCategory) result = result.filter(f => f.category === filterCategory)
    return result
  }, [fields, search, filterType, filterCategory])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Field Definitions</h1>
          <p className="text-sm text-gray-500">
            {fields.length} fields defined — {fields.filter(f => f.is_active).length} active
          </p>
        </div>
        <Link href="/admin/registration">
          <Button variant="outline" size="sm">← Back to Flows</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="Search by slug, label…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All types</option>
          {fieldTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Slug</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Label</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Component</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Required</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Usages</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(f => (
                <tr key={f.id} className="border-b hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{f.slug}</td>
                  <td className="px-4 py-3 text-gray-900">{f.label}</td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="text-xs">{f.field_type}</Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{f.category || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{f.component_type_default || '—'}</td>
                  <td className="px-4 py-3 text-center">
                    {f.required_default === true ? '✓' : f.required_default === false ? '—' : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge className={f.usage_count > 0 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}>
                      {f.usage_count}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge className={f.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
                      {f.is_active ? 'active' : 'inactive'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/admin/registration/field-definitions/${f.id}`}>
                      <Button size="sm" variant="outline">View</Button>
                    </Link>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                    No field definitions found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}

'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

interface Usage {
  component_id: string
  component_type: string
  binding_slug: string | null
  screen_title: string | null
  step_title: string | null
  flow_name: string | null
  flow_id: string | null
  flow_status: string | null
}

interface FieldDetail {
  id: string
  slug: string
  slug_snake: string
  field_name_en: string
  label: string
  field_type: string
  category: string | null
  is_active: boolean
  ui_label: string | null
  component_type_default: string | null
  required_default: boolean | null
  options: unknown[] | null
  created_at: string | null
  updated_at: string | null
  usages: Usage[]
  usage_count: number
}

export default function FieldDefinitionDetailPage() {
  const params = useParams()
  const fieldId = (params?.id as string | undefined) ?? ''

  const [field, setField] = useState<FieldDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editLabel, setEditLabel] = useState('')
  const [editComponent, setEditComponent] = useState('')
  const [editRequired, setEditRequired] = useState(false)
  const [editActive, setEditActive] = useState(true)

  const load = useCallback(() => {
    fetch(`${BACKEND}/api/admin/registration/field-definitions/${fieldId}`)
      .then(r => r.json())
      .then(d => {
        setField(d)
        setEditLabel(d.ui_label || '')
        setEditComponent(d.component_type_default || '')
        setEditRequired(d.required_default || false)
        setEditActive(d.is_active)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [fieldId])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setSaving(true)
    try {
      await fetch(`${BACKEND}/api/admin/registration/field-definitions/${fieldId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ui_label: editLabel || null,
          component_type_default: editComponent || null,
          required_default: editRequired,
          is_active: editActive,
        }),
      })
      load()
    } finally {
      setSaving(false)
    }
  }

  if (loading || !field) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{field.label}</h1>
            <Badge className="bg-indigo-100 text-indigo-800 border border-indigo-200">
              Client profile field
            </Badge>
          </div>
          <p className="text-sm text-gray-500 font-mono">{field.slug}</p>
          <p className="text-xs text-gray-600 mt-2 max-w-xl">
            This catalog entry represents a piece of client data collected during registration. Input and compliance widgets on flows must reference a field definition so bindings stay aligned with the profile model.
          </p>
        </div>
        <Link href="/admin/registration/field-definitions">
          <Button variant="outline" size="sm">← Back to Catalog</Button>
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Info card */}
        <Card>
          <CardHeader><CardTitle className="text-base">Field Information</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Slug</span>
              <span className="font-mono">{field.slug}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Snake slug</span>
              <span className="font-mono">{field.slug_snake}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Name (EN)</span>
              <span>{field.field_name_en}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Field type</span>
              <Badge variant="outline">{field.field_type}</Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Default widget</span>
              <span className="font-mono text-xs">{field.component_type_default || '—'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Required by default</span>
              <Badge variant="outline" className={field.required_default ? 'border-amber-300 text-amber-800' : ''}>
                {field.required_default === true ? 'yes' : field.required_default === false ? 'no' : '—'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Category</span>
              <span>{field.category || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Status</span>
              <Badge className={field.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}>
                {field.is_active ? 'active' : 'inactive'}
              </Badge>
            </div>
            {field.options && (
              <div>
                <span className="text-gray-500 block mb-1">Options</span>
                <pre className="bg-gray-50 rounded p-2 text-xs overflow-auto max-h-40">
                  {JSON.stringify(field.options, null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit card */}
        <Card>
          <CardHeader><CardTitle className="text-base">Edit Metadata</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">UI Label</label>
              <input
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
                value={editLabel}
                onChange={e => setEditLabel(e.target.value)}
                placeholder={field.field_name_en}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Default Component Type</label>
              <select
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm"
                value={editComponent}
                onChange={e => setEditComponent(e.target.value)}
              >
                <option value="">None</option>
                <option value="text_input">text_input</option>
                <option value="phone_input">phone_input</option>
                <option value="select">select</option>
                <option value="country_picker">country_picker</option>
                <option value="date_picker">date_picker</option>
                <option value="checkbox">checkbox</option>
                <option value="multi_select">multi_select</option>
              </select>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editRequired} onChange={e => setEditRequired(e.target.checked)} />
                Required by default
              </label>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editActive} onChange={e => setEditActive(e.target.checked)} />
                Active
              </label>
            </div>
            <Button className="w-full" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : 'Save Changes'}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Usages */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">
            Usages ({field.usage_count})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {field.usages.length === 0 ? (
            <p className="text-sm text-gray-400">This field is not used in any flow.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Flow</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Status</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Step</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Screen</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Component</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Binding</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {field.usages.map((u, i) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2">{u.flow_name || '—'}</td>
                    <td className="px-3 py-2">
                      {u.flow_status && (
                        <Badge className={
                          u.flow_status === 'active' ? 'bg-green-100 text-green-700'
                          : u.flow_status === 'draft' ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-500'
                        }>{u.flow_status}</Badge>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-600">{u.step_title || '—'}</td>
                    <td className="px-3 py-2 text-gray-600">{u.screen_title || '—'}</td>
                    <td className="px-3 py-2 text-xs font-mono">{u.component_type}</td>
                    <td className="px-3 py-2 text-xs font-mono text-gray-500">{u.binding_slug || '—'}</td>
                    <td className="px-3 py-2">
                      {u.flow_id && (
                        <Link href={`/admin/registration/flows/${u.flow_id}/edit`}>
                          <Button size="sm" variant="outline">Edit Flow</Button>
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

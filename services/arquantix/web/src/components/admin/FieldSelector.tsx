'use client'

import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface FieldDefinition {
  id: string
  slug: string
  field_name_en: string
  field_type: string
  category: string
  is_active: boolean
}

interface FieldSelectorProps {
  selected: string[]
  onSelect: (slug: string) => void
  onRemove: (slug: string) => void
  multiple?: boolean
}

const ALL_SENTINEL = '__all__'

export function FieldSelector({ selected, onSelect, onRemove, multiple = true }: FieldSelectorProps) {
  const [fields, setFields] = useState<FieldDefinition[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')

  useEffect(() => {
    fetchFields()
  }, [])

  const fetchFields = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('is_active', 'true')
      if (categoryFilter) params.append('category', categoryFilter)
      if (searchQuery) params.append('search', searchQuery)

      const response = await fetch(`/api/admin/field-definitions?${params.toString()}`, {
        credentials: 'include',
      })
      const data = await response.json()

      if (response.ok) {
        setFields(Array.isArray(data) ? data : (data.fields || []))
      }
    } catch (error) {
      console.error('Error fetching fields:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFields()
  }, [categoryFilter, searchQuery])

  const categories = Array.from(new Set(fields.map(f => f.category).filter(Boolean)))

  const filteredFields = fields.filter(field => {
    if (selected.includes(field.slug)) return false
    if (searchQuery && !field.slug.toLowerCase().includes(searchQuery.toLowerCase()) && 
        !field.field_name_en.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    return true
  })

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search fields..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select 
          value={categoryFilter || ALL_SENTINEL} 
          onValueChange={(v) => setCategoryFilter(v === ALL_SENTINEL ? '' : v)}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_SENTINEL}>All Categories</SelectItem>
            {categories.map(cat => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 p-2 bg-gray-50 rounded">
          {selected.map(slug => {
            const field = fields.find(f => f.slug === slug)
            return (
              <div key={slug} className="flex items-center gap-1 px-2 py-1 bg-white border rounded">
                <span className="text-sm">{field?.field_name_en || slug}</span>
                <button
                  onClick={() => onRemove(slug)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      <div className="border rounded-md max-h-64 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500">Loading...</div>
        ) : filteredFields.length === 0 ? (
          <div className="p-4 text-center text-gray-500">No fields found</div>
        ) : (
          <div className="divide-y">
            {filteredFields.map(field => (
              <button
                key={field.id}
                onClick={() => onSelect(field.slug)}
                className="w-full text-left p-3 hover:bg-gray-50 flex items-center justify-between"
              >
                <div>
                  <div className="font-medium text-sm">{field.field_name_en}</div>
                  <div className="text-xs text-gray-500">{field.slug}</div>
                </div>
                <div className="text-xs text-gray-400">{field.field_type}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

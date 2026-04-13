'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Plus, Search, Filter, Globe, FileText, Shield, AlertCircle, Trash2 } from 'lucide-react'
import { REGULATORY_JURISDICTIONS, getJurisdictionLabel } from '@/lib/admin/jurisdictions'

interface JurisdictionConfig {
  id: string
  jurisdiction: string
  purpose: string
  version: number
  status: 'draft' | 'active' | 'archived'
  config_json: any
  created_at: string
  updated_at: string
}

const ALL_SENTINEL = '__all__'

export default function JurisdictionConfigsPage() {
  const router = useRouter()
  const [configs, setConfigs] = useState<JurisdictionConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterJurisdiction, setFilterJurisdiction] = useState<string>('')
  const [filterPurpose, setFilterPurpose] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [configToDelete, setConfigToDelete] = useState<JurisdictionConfig | null>(null)

  useEffect(() => {
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
          return
        }
        fetchConfigs()
      })
      .catch(() => {
        router.push('/admin/login')
      })
  }, [router])

  const fetchConfigs = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (filterJurisdiction) params.append('jurisdiction', filterJurisdiction)
      if (filterPurpose) params.append('purpose', filterPurpose)
      if (filterStatus) params.append('status', filterStatus)

      const url = `/api/admin/jurisdiction-configs${params.toString() ? `?${params.toString()}` : ''}`
      const response = await fetch(url, {
        credentials: 'include',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to fetch configs')
      }

      let filtered = Array.isArray(data) ? data : (data.configs || [])
      
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        filtered = filtered.filter((config: JurisdictionConfig) =>
          config.jurisdiction.toLowerCase().includes(query) ||
          config.purpose.toLowerCase().includes(query) ||
          config.status.toLowerCase().includes(query)
        )
      }

      setConfigs(filtered)
    } catch (error: any) {
      console.error('Error fetching configs:', error)
      const errorMessage = error.message || 'Failed to load configs'
      setError(errorMessage)
      toastError(errorMessage)
      setConfigs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConfigs()
  }, [filterJurisdiction, filterPurpose, filterStatus])

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      draft: 'bg-yellow-100 text-yellow-800',
      active: 'bg-green-100 text-green-800',
      archived: 'bg-gray-100 text-gray-800',
    }
    return variants[status] || 'bg-gray-100 text-gray-800'
  }

  const getPurposeIcon = (purpose: string) => {
    if (purpose === 'KYC') return FileText
    if (purpose === 'AML_RISK') return Shield
    return Globe
  }

  const handleDeleteClick = (config: JurisdictionConfig) => {
    setConfigToDelete(config)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!configToDelete) return

    try {
      const response = await fetch(`/api/admin/jurisdiction-configs/${configToDelete.id}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to delete config' }))
        throw new Error(errorData.error || errorData.detail || 'Failed to delete config')
      }

      toastSuccess('Config deleted successfully')
      setDeleteDialogOpen(false)
      setConfigToDelete(null)
      fetchConfigs() // Refresh the list
    } catch (error: any) {
      console.error('Error deleting config:', error)
      toastError(error.message || 'Failed to delete config')
    }
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Jurisdiction Configs</h1>
        <div className="text-gray-500">Chargement...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Jurisdiction Configs</h1>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Error loading configs</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={fetchConfigs}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Jurisdiction Configs</h1>
        <Button onClick={() => router.push('/admin/jurisdiction-configs/new')}>
          <Plus className="w-4 h-4 mr-2" />
          Create Config
        </Button>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    fetchConfigs()
                  }}
                  className="pl-8"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Jurisdiction
              </label>
              <Select 
                value={filterJurisdiction || ALL_SENTINEL} 
                onValueChange={(v) => setFilterJurisdiction(v === ALL_SENTINEL ? '' : v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_SENTINEL}>All</SelectItem>
                  {REGULATORY_JURISDICTIONS.map((j) => (
                    <SelectItem key={j.value} value={j.value}>
                      {j.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Purpose
              </label>
              <Select 
                value={filterPurpose || ALL_SENTINEL} 
                onValueChange={(v) => setFilterPurpose(v === ALL_SENTINEL ? '' : v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_SENTINEL}>All</SelectItem>
                  <SelectItem value="KYC">KYC</SelectItem>
                  <SelectItem value="AML_RISK">AML_RISK</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <Select 
                value={filterStatus || ALL_SENTINEL} 
                onValueChange={(v) => setFilterStatus(v === ALL_SENTINEL ? '' : v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_SENTINEL}>All</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configs List */}
      {configs.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Globe className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No configs found</h3>
            <p className="text-gray-600 mb-4">
              Create your first jurisdiction config to get started
            </p>
            <Button onClick={() => router.push('/admin/jurisdiction-configs/new')}>
              <Plus className="w-4 h-4 mr-2" />
              Create Config
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {configs.map((config) => {
            const PurposeIcon = getPurposeIcon(config.purpose)
            return (
              <Card key={config.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <PurposeIcon className="w-5 h-5 text-gray-600" />
                        <CardTitle className="text-lg">{getJurisdictionLabel(config.jurisdiction)}</CardTitle>
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={getStatusBadge(config.status)}>
                          {config.status}
                        </Badge>
                        <Badge variant="outline">v{config.version}</Badge>
                      </div>
                      <p className="text-sm text-gray-600">{config.purpose}</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="text-sm text-gray-500">
                      Created: {new Date(config.created_at).toLocaleDateString()}
                    </div>
                    <div className="pt-2 border-t flex items-center justify-between">
                      <Link
                        href={`/admin/jurisdiction-configs/${config.id}`}
                        className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                      >
                        Edit →
                      </Link>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(config)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Jurisdiction Config"
        description={
          configToDelete
            ? `Are you sure you want to delete "${getJurisdictionLabel(configToDelete.jurisdiction)}" (${configToDelete.purpose}, v${configToDelete.version})? This action cannot be undone.`
            : 'Are you sure you want to delete this config?'
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDeleteConfirm}
        destructive={true}
      />
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { KYCBuilder } from '@/components/admin/KYCBuilder'
import { AMLRiskBuilder } from '@/components/admin/AMLRiskBuilder'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Save, ArrowLeft, Send, AlertCircle } from 'lucide-react'
import { REGULATORY_JURISDICTIONS, isKnownJurisdiction, getJurisdictionLabel } from '@/lib/admin/jurisdictions'

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

export default function JurisdictionConfigEditPage() {
  const router = useRouter()
  const params = useParams()
  const configId = (params?.id as string | undefined) ?? ''
  const isNew = configId === 'new'

  const [loading, setLoading] = useState(!isNew)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [showPublishDialog, setShowPublishDialog] = useState(false)

  const [jurisdiction, setJurisdiction] = useState('')
  const [purpose, setPurpose] = useState<'KYC' | 'AML_RISK'>('KYC')
  const [configJson, setConfigJson] = useState<any>(null)

  useEffect(() => {
    if (isNew) {
      setConfigJson({
        jurisdiction: '',
        purpose: 'KYC',
        version: 1,
        status: 'draft',
        steps: [],
        entry_rules: null,
      })
      setLoading(false)
    } else {
      fetchConfig()
    }
  }, [configId, isNew])

  const fetchConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/admin/jurisdiction-configs/${configId}`, {
        credentials: 'include',
      })

      let data: any = {}
      try {
        const text = await response.text()
        if (text) {
          data = JSON.parse(text)
        }
      } catch (parseError) {
        console.error('Failed to parse response JSON:', parseError)
        data = { error: 'parse_error', detail: 'Failed to parse server response' }
      }

      if (!response.ok) {
        // Extract error details from backend response
        const errorMsg = data.detail?.message || data.detail?.detail || data.detail || data.error || data.message || 'Failed to fetch config'
        const errorDetails = data.detail?.details || (data.details ? [data.details] : [])
        const traceId = data.detail?.trace_id || data.trace_id
        
        let fullError = errorMsg
        if (errorDetails && errorDetails.length > 0) {
          fullError += `: ${errorDetails.map((d: any) => d.message || d).join(', ')}`
        }
        if (traceId) {
          fullError += ` (trace_id: ${traceId})`
        }
        
        throw new Error(fullError)
      }

      setJurisdiction(data.jurisdiction)
      setPurpose(data.purpose as 'KYC' | 'AML_RISK')
      // Ensure config_json has the right structure
      const configJsonData = data.config_json || {}
      if (data.purpose === 'KYC') {
        setConfigJson({
          ...configJsonData,
          jurisdiction: data.jurisdiction,
          purpose: data.purpose,
          version: data.version,
          status: data.status,
          steps: configJsonData.steps || [],
          entry_rules: configJsonData.entry_rules || null,
        })
      } else {
        setConfigJson({
          ...configJsonData,
          jurisdiction: data.jurisdiction,
          purpose: data.purpose,
          version: data.version,
          status: data.status,
          rules: configJsonData.rules || [],
          outputs: configJsonData.outputs || {
            min_score: 0,
            max_score: 100,
            tiers: [],
          },
        })
      }
    } catch (error: any) {
      console.error('Error fetching config:', error)
      const errorMessage = error.message || 'Failed to load config'
      setError(errorMessage)
      toastError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!jurisdiction || !purpose || !configJson) {
      toastError('Please fill in all required fields')
      return
    }

    setSaving(true)
    try {
      // Build config_json according to purpose
      let configJsonPayload: any
      if (purpose === 'KYC') {
        configJsonPayload = {
          jurisdiction,
          purpose,
          version: isNew ? 1 : configJson.version,
          status: 'draft',
          steps: configJson.steps || [],
          entry_rules: configJson.entry_rules || null,
        }
      } else {
        configJsonPayload = {
          jurisdiction,
          purpose,
          version: isNew ? 1 : configJson.version,
          status: 'draft',
          rules: configJson.rules || [],
          outputs: configJson.outputs || {
            min_score: 0,
            max_score: 100,
            tiers: [],
          },
        }
      }

      const payload = {
        jurisdiction,
        purpose,
        config_json: configJsonPayload,
      }

      const url = isNew
        ? '/api/admin/jurisdiction-configs'
        : `/api/admin/jurisdiction-configs/${configId}`

      const method = isNew ? 'POST' : 'PUT'

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to save config')
      }

      toastSuccess(isNew ? 'Config created successfully' : 'Config updated successfully')
      
      if (isNew) {
        router.push(`/admin/jurisdiction-configs/${data.id}`)
      } else {
        await fetchConfig()
      }
    } catch (error: any) {
      console.error('Error saving config:', error)
      toastError(error.message || 'Failed to save config')
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!configId || configId === 'new') {
      toastError('Please save the config first')
      return
    }

    setPublishing(true)
    try {
      const response = await fetch(`/api/admin/jurisdiction-configs/${configId}/publish`, {
        method: 'POST',
        credentials: 'include',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to publish config')
      }

      toastSuccess('Config published successfully')
      setShowPublishDialog(false)
      await fetchConfig()
    } catch (error: any) {
      console.error('Error publishing config:', error)
      toastError(error.message || 'Failed to publish config')
    } finally {
      setPublishing(false)
    }
  }

  if (loading) {
    return (
      <div>
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push('/admin/jurisdiction-configs')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <h1 className="text-3xl font-bold text-gray-900">Error</h1>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Error loading config</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={fetchConfig}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!configJson) {
    return (
      <div>
        <div className="text-gray-500">No config data</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.push('/admin/jurisdiction-configs')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <h1 className="text-3xl font-bold text-gray-900">
            {isNew ? 'Create Jurisdiction Config' : 'Edit Jurisdiction Config'}
          </h1>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleSave} disabled={saving}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save'}
          </Button>
          {!isNew && (
            <Button
              onClick={() => setShowPublishDialog(true)}
              disabled={publishing || configJson.status === 'active'}
              variant="default"
            >
              <Send className="w-4 h-4 mr-2" />
              Publish
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Jurisdiction *
              </label>
              {!isNew && !isKnownJurisdiction(jurisdiction) ? (
                <div className="flex items-center gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                  <AlertCircle className="w-4 h-4 text-yellow-600" />
                  <span className="text-sm text-yellow-800">
                    {getJurisdictionLabel(jurisdiction)} (read-only)
                  </span>
                </div>
              ) : (
                <Select value={jurisdiction} onValueChange={setJurisdiction} disabled={!isNew}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select regulatory scope" />
                  </SelectTrigger>
                  <SelectContent>
                    {REGULATORY_JURISDICTIONS.map((j) => (
                      <SelectItem key={j.value} value={j.value}>
                        {j.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Purpose *
              </label>
              <Select
                value={purpose}
                onValueChange={(value: 'KYC' | 'AML_RISK') => {
                  setPurpose(value)
                  if (value === 'KYC') {
                    setConfigJson({
                      jurisdiction,
                      purpose: 'KYC',
                      version: configJson.version || 1,
                      status: 'draft',
                      steps: [],
                      entry_rules: null,
                    })
                  } else {
                    setConfigJson({
                      jurisdiction,
                      purpose: 'AML_RISK',
                      version: configJson.version || 1,
                      status: 'draft',
                      rules: [],
                      outputs: {
                        min_score: 0,
                        max_score: 100,
                        tiers: [],
                      },
                    })
                  }
                }}
                disabled={!isNew}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="KYC">KYC</SelectItem>
                  <SelectItem value="AML_RISK">AML_RISK</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          {!isNew && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Version
                </label>
                <Input value={configJson.version || 1} disabled />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <Input value={configJson.status || 'draft'} disabled />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          {purpose === 'KYC' ? (
            <KYCBuilder
              steps={configJson.steps || []}
              onChange={(steps) => setConfigJson({ ...configJson, steps })}
            />
          ) : (
            <AMLRiskBuilder
              config={{
                rules: configJson.rules || [],
                outputs: configJson.outputs || {
                  min_score: 0,
                  max_score: 100,
                  tiers: [],
                },
              }}
              onChange={(amlConfig) => {
                setConfigJson({
                  ...configJson,
                  rules: amlConfig.rules,
                  outputs: amlConfig.outputs,
                })
              }}
            />
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={showPublishDialog}
        onOpenChange={setShowPublishDialog}
        onConfirm={handlePublish}
        title="Publish Config"
        description="This will set this config as active and archive any previous active config for the same jurisdiction and purpose. Are you sure?"
        confirmLabel="Publish"
        cancelLabel="Cancel"
        destructive={false}
      />
    </div>
  )
}

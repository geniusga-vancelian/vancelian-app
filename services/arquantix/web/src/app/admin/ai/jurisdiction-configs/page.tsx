'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChatStudio } from '@/components/ai-jurisdiction-configs/ChatStudio'
import { validateJurisdictionConfig } from '@/components/ai-jurisdiction-configs/api'
import { REGULATORY_JURISDICTIONS } from '@/lib/admin/jurisdictions'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { CheckCircle2, Save, Send, Copy, AlertCircle } from 'lucide-react'

// Slug alias mapping (must match backend SLUG_ALIASES)
// Note: These map FROM alias TO canonical slug
const SLUG_ALIASES: Record<string, string> = {
  nationality: 'nationality',
  'nationality-primary': 'nationality',
  'residential-address-line1': 'residential-address-line-1',
  'residential-address-city': 'residential-city',
  'residential-address-country': 'residential-country',
  'residential-address-postal-code': 'residential-postal-code', // Map to canonical
  'tax-residency-country-primary': 'tax-residency-country',
  'tax-identification-number': 'tax-id-number',
  'investment-objective': 'investment-objectives',
  'occupation-title': 'occupation',
}

function normalizeConfigForBackend(rawSpec: any, purpose: 'KYC' | 'AML_RISK'): any {
  if (!rawSpec || typeof rawSpec !== 'object') {
    return rawSpec
  }

  const normalized = JSON.parse(JSON.stringify(rawSpec)) // Deep clone

  // Ensure required top-level fields
  if (!normalized.jurisdiction) {
    normalized.jurisdiction = ''
  }
  if (!normalized.purpose) {
    normalized.purpose = purpose
  }
  if (normalized.version === undefined || normalized.version === null) {
    normalized.version = 1
  }
  if (!normalized.status) {
    normalized.status = 'draft'
  }
  if (purpose === 'KYC' && normalized.entry_rules === undefined) {
    normalized.entry_rules = null
  }

  if (purpose === 'KYC') {
    // Normalize steps -> blocks -> conditions
    for (const step of normalized.steps || []) {
      for (const block of step.blocks || []) {
        // Normalize conditions: null -> []
        if (block.conditions === null || block.conditions === undefined) {
          block.conditions = []
        } else if (!Array.isArray(block.conditions)) {
          block.conditions = []
        }

        // Normalize each condition
        const normalizedConditions: any[] = []
        for (const cond of block.conditions || []) {
          if (!cond || typeof cond !== 'object' || !cond.when || !cond.then) {
            continue
          }

          const when: any = { ...cond.when }
          const thenList: any[] = []

          // Normalize when clause: field_slug -> field, operator -> op
          if (when.field_slug !== undefined) {
            when.field = when.field_slug
            delete when.field_slug
          }
          if (when.operator !== undefined) {
            when.op = when.operator
            delete when.operator
          }

          // Normalize then actions: target -> block_id/field based on action
          for (const thenItem of cond.then || []) {
            if (!thenItem || typeof thenItem !== 'object' || !thenItem.action) {
              continue
            }

            const action = thenItem.action
            const normalizedThen: any = { action }

            if (thenItem.target !== undefined) {
              if (action === 'show_block' || action === 'hide_block') {
                normalizedThen.block_id = thenItem.target
              } else if (action === 'require_field' || action === 'optional_field') {
                normalizedThen.field = thenItem.target
              } else {
                normalizedThen.target = thenItem.target
              }
            } else if (thenItem.block_id !== undefined) {
              normalizedThen.block_id = thenItem.block_id
            } else if (thenItem.field !== undefined) {
              normalizedThen.field = thenItem.field
            } else if (thenItem.step_id !== undefined) {
              normalizedThen.step_id = thenItem.step_id
            }

            thenList.push(normalizedThen)
          }

          normalizedConditions.push({
            when,
            then: thenList,
          })
        }

        block.conditions = normalizedConditions

        // Map slug aliases in fields array
        const normalizedFields: string[] = []
        for (const fieldSlug of block.fields || []) {
          if (typeof fieldSlug === 'string' && SLUG_ALIASES[fieldSlug]) {
            normalizedFields.push(SLUG_ALIASES[fieldSlug])
          } else {
            normalizedFields.push(fieldSlug)
          }
        }
        block.fields = normalizedFields
      }
    }
  }

  return normalized
}

function collectFieldSlugsFromConfig(config: any, purpose: 'KYC' | 'AML_RISK'): string[] {
  const slugs: Set<string> = new Set()

  if (purpose === 'KYC') {
    for (const step of config.steps || []) {
      for (const block of step.blocks || []) {
        // Collect from fields array
        for (const fieldSlug of block.fields || []) {
          if (typeof fieldSlug === 'string') {
            slugs.add(fieldSlug)
          }
        }

        // Collect from conditions (supports both normalized and Pydantic formats)
        for (const cond of block.conditions || []) {
          if (cond.when) {
            // Support both field (normalized) and field_slug (Pydantic)
            if (cond.when.field) {
              slugs.add(cond.when.field)
            }
            if (cond.when.field_slug) {
              slugs.add(cond.when.field_slug)
            }
          }
          for (const thenItem of cond.then || []) {
            if (thenItem.field) {
              slugs.add(thenItem.field)
            }
          }
        }
      }
    }
  } else if (purpose === 'AML_RISK') {
    for (const rule of config.rules || []) {
      if (rule.when?.field_slug) {
        slugs.add(rule.when.field_slug)
      }
    }
  }

  return Array.from(slugs)
}

function collectFieldSlugsFromConfigPydantic(config: any, purpose: 'KYC' | 'AML_RISK'): string[] {
  const slugs: Set<string> = new Set()

  if (purpose === 'KYC') {
    for (const step of config.steps || []) {
      for (const block of step.blocks || []) {
        // Collect from fields array
        for (const fieldSlug of block.fields || []) {
          if (typeof fieldSlug === 'string') {
            slugs.add(fieldSlug)
          }
        }

        // Collect from conditions (Pydantic format: field_slug)
        for (const cond of block.conditions || []) {
          if (cond.when?.field_slug) {
            slugs.add(cond.when.field_slug)
          }
          // Also check target in then actions (for require_field/optional_field)
          for (const thenItem of cond.then || []) {
            if (thenItem.action === 'require_field' || thenItem.action === 'optional_field') {
              if (thenItem.target && typeof thenItem.target === 'string') {
                slugs.add(thenItem.target)
              }
            }
          }
        }
      }
    }
  } else if (purpose === 'AML_RISK') {
    for (const rule of config.rules || []) {
      if (rule.when?.field_slug) {
        slugs.add(rule.when.field_slug)
      }
    }
  }

  return Array.from(slugs)
}

export default function AIJurisdictionConfigsPage() {
  const router = useRouter()
  const [jurisdiction, setJurisdiction] = useState<string>('')
  const [purpose, setPurpose] = useState<'KYC' | 'AML_RISK'>('KYC')
  const [spec, setSpec] = useState<any>(null)
  const [validatedSpec, setValidatedSpec] = useState<any>(null)
  const [assistantText, setAssistantText] = useState<string>('')
  const [validationResult, setValidationResult] = useState<{ ok: boolean; errors: string[] } | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isPublishing, setIsPublishing] = useState(false)
  const [savedConfigId, setSavedConfigId] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [createErrorDetails, setCreateErrorDetails] = useState<{
    error?: string
    details?: any[]
    trace_id?: string
    message?: string
  } | null>(null)
  const [fieldDefinitions, setFieldDefinitions] = useState<Set<string>>(new Set())
  const [invalidSlugs, setInvalidSlugs] = useState<string[]>([])

  // Load field definitions once
  useEffect(() => {
    async function loadFieldDefinitions() {
      try {
        const response = await fetch('/api/admin/field-definitions?is_active=true', {
          credentials: 'include',
        })
        if (response.ok) {
          const data = await response.json()
          const slugs = new Set<string>()
          for (const field of data || []) {
            if (field.slug) {
              slugs.add(field.slug)
            }
          }
          setFieldDefinitions(slugs)
        }
      } catch (error) {
        console.error('Failed to load field definitions:', error)
      }
    }
    loadFieldDefinitions()
  }, [])

  const handleConfigGenerated = (newSpec: any, newAssistantText: string) => {
    setSpec(newSpec)
    setAssistantText(newAssistantText)
    setValidationResult(null)
    setValidatedSpec(null)
    setCreateError(null)
    setCreateErrorDetails(null)
    setInvalidSlugs([])
  }

  const normalizeSpec = (rawSpec: any): any => {
    if (!rawSpec || typeof rawSpec !== 'object') {
      return rawSpec
    }

    const normalized = { ...rawSpec }

    // Inject missing top-level fields for KYC/AML_RISK
    if (purpose === 'KYC') {
      if (!normalized.jurisdiction) {
        normalized.jurisdiction = jurisdiction
      }
      if (!normalized.purpose) {
        normalized.purpose = 'KYC'
      }
      if (normalized.version === undefined || normalized.version === null) {
        normalized.version = 1
      }
      if (!normalized.status) {
        normalized.status = 'draft'
      }
      if (normalized.entry_rules === undefined) {
        normalized.entry_rules = null
      }
    } else if (purpose === 'AML_RISK') {
      if (!normalized.jurisdiction) {
        normalized.jurisdiction = jurisdiction
      }
      if (!normalized.purpose) {
        normalized.purpose = 'AML_RISK'
      }
      if (normalized.version === undefined || normalized.version === null) {
        normalized.version = 1
      }
    }

    return normalized
  }

  const handleValidate = async () => {
    if (!spec || !jurisdiction) {
      toastError('Please generate a config first')
      return
    }

    setIsValidating(true)
    try {
      // Normalize spec before validation
      const normalized = normalizeSpec(spec)

      const result = await validateJurisdictionConfig({
        jurisdiction,
        purpose,
        spec: normalized,
      })

      setValidationResult(result)

      if (result.ok) {
        toastSuccess('Configuration is valid')
        if (result.normalized_spec) {
          setValidatedSpec(result.normalized_spec)
          setSpec(result.normalized_spec)
        } else {
          setValidatedSpec(normalized)
          setSpec(normalized)
        }
      } else {
        toastError(`Validation failed: ${result.errors.join(', ')}`)
        setValidatedSpec(null)
      }
    } catch (error: any) {
      console.error('Validation error:', error)
      toastError(error.message || 'Failed to validate config')
    } finally {
      setIsValidating(false)
    }
  }

  const handleCreateDraft = async () => {
    if (!spec || !jurisdiction) {
      toastError('Please generate a config first')
      return
    }

    if (!validationResult || !validationResult.ok) {
      toastError('Please validate the config first')
      return
    }

    setIsSaving(true)
    setCreateError(null)
    setCreateErrorDetails(null)
    setInvalidSlugs([])

    try {
      // Use validated spec (which is normalized) or normalize current spec
      let draftSpec = validatedSpec || normalizeSpec(spec)

      // Convert to Pydantic format for backend (detect format and convert only if needed)
      const configJsonForBackend = JSON.parse(JSON.stringify(draftSpec))
      
      // Ensure required top-level fields
      if (!configJsonForBackend.jurisdiction) {
        configJsonForBackend.jurisdiction = jurisdiction
      }
      if (!configJsonForBackend.purpose) {
        configJsonForBackend.purpose = purpose
      }
      if (configJsonForBackend.version === undefined || configJsonForBackend.version === null) {
        configJsonForBackend.version = 1
      }
      if (!configJsonForBackend.status) {
        configJsonForBackend.status = 'draft'
      }
      if (purpose === 'KYC' && configJsonForBackend.entry_rules === undefined) {
        configJsonForBackend.entry_rules = null
      }

      if (purpose === 'KYC') {
        // Convert conditions to Pydantic format (field -> field_slug, op -> operator, block_id/field -> target)
        // Only convert if format is normalized (has field/op), not if already Pydantic (has field_slug/operator)
        for (const step of configJsonForBackend.steps || []) {
          for (const block of step.blocks || []) {
            // Ensure conditions is array
            if (!Array.isArray(block.conditions)) {
              block.conditions = []
            }

            for (const cond of block.conditions || []) {
              if (!cond || !cond.when) continue
              
              const when = cond.when
              
              // Convert field -> field_slug ONLY if field exists and field_slug doesn't
              if (when.field !== undefined && when.field_slug === undefined) {
                when.field_slug = when.field
                delete when.field
              }
              
              // Convert op -> operator ONLY if op exists and operator doesn't
              if (when.op !== undefined && when.operator === undefined) {
                when.operator = when.op
                delete when.op
              }

              // Convert then actions
              if (Array.isArray(cond.then)) {
                for (const thenItem of cond.then) {
                  if (!thenItem || !thenItem.action) continue
                  
                  // Convert block_id -> target for show_block/hide_block
                  if ((thenItem.action === 'show_block' || thenItem.action === 'hide_block') && 
                      thenItem.block_id !== undefined && thenItem.target === undefined) {
                    thenItem.target = thenItem.block_id
                    delete thenItem.block_id
                  }
                  
                  // Convert field -> target for require_field/optional_field
                  if ((thenItem.action === 'require_field' || thenItem.action === 'optional_field') &&
                      thenItem.field !== undefined && thenItem.target === undefined) {
                    thenItem.target = thenItem.field
                    delete thenItem.field
                  }
                }
              }
            }
          }
        }
      }

      // Safety check: validate field slugs exist in catalog
      if (fieldDefinitions.size > 0) {
        const slugsInConfig = collectFieldSlugsFromConfigPydantic(configJsonForBackend, purpose)
        const missingSlugs = slugsInConfig.filter((slug) => !fieldDefinitions.has(slug))

        if (missingSlugs.length > 0) {
          setInvalidSlugs(missingSlugs)
          setCreateError(
            `Invalid field slugs found: ${missingSlugs.join(', ')}. Please ensure all fields exist in the catalog.`
          )
          toastError(`Invalid field slugs: ${missingSlugs.join(', ')}`)
          return
        }
      }

      const response = await fetch('/api/admin/jurisdiction-configs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          jurisdiction,
          purpose,
          config_json: configJsonForBackend,
        }),
      })

      // Parse response JSON safely
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
        // Extract error details from response
        const errorDetails: {
          error?: string
          details?: any[]
          trace_id?: string
          message?: string
          detail?: any
        } = {}

        // Handle FastAPI error format: { detail: { error: "...", details: [...], trace_id: "..." } }
        if (data.detail && typeof data.detail === 'object') {
          errorDetails.error = data.detail.error || data.error || 'unknown_error'
          errorDetails.details = data.detail.details || (Array.isArray(data.detail) ? data.detail : [])
          errorDetails.trace_id = data.detail.trace_id
          errorDetails.message = data.detail.message || data.detail.detail || data.message
        } else {
          // Fallback: direct error fields
          errorDetails.error = data.error || 'unknown_error'
          errorDetails.details = data.details || (data.detail && typeof data.detail === 'string' ? [data.detail] : [])
          errorDetails.trace_id = data.trace_id
          errorDetails.message = data.message || data.detail || 'Failed to create draft'
        }

        // Log full error to console
        console.error('Create Draft API Error:', {
          status: response.status,
          statusText: response.statusText,
          errorDetails,
          fullResponse: data,
        })

        // Set error state
        setCreateErrorDetails(errorDetails)
        const errorMsg = errorDetails.message || errorDetails.error || 'Failed to create draft'
        setCreateError(errorMsg)
        toastError(errorMsg)
        return
      }

      setSavedConfigId(data.id)
      setCreateError(null)
      setCreateErrorDetails(null)
      setInvalidSlugs([])
      toastSuccess('Draft created successfully')
      router.push(`/admin/jurisdiction-configs/${data.id}`)
    } catch (error: any) {
      console.error('Error creating draft:', error)
      const errorMsg = error.message || 'Failed to create draft'
      setCreateErrorDetails({
        error: 'network_error',
        message: errorMsg,
      })
      setCreateError(errorMsg)
      toastError(errorMsg)
    } finally {
      setIsSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!savedConfigId) {
      toastError('Please save as draft first')
      return
    }

    setIsPublishing(true)
    try {
      const response = await fetch(`/api/admin/jurisdiction-configs/${savedConfigId}/publish`, {
        method: 'POST',
        credentials: 'include',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || data.detail || 'Failed to publish config')
      }

      toastSuccess('Config published successfully')
      router.push(`/admin/jurisdiction-configs/${savedConfigId}`)
    } catch (error: any) {
      console.error('Error publishing config:', error)
      toastError(error.message || 'Failed to publish config')
    } finally {
      setIsPublishing(false)
    }
  }

  const handleCopyJSON = () => {
    if (!spec) return
    navigator.clipboard.writeText(JSON.stringify(spec, null, 2))
    toastSuccess('JSON copied to clipboard')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4">
        <h1 className="text-3xl font-bold text-gray-900">AI Jurisdiction Config Builder</h1>
        <div className="flex gap-2">
          {spec && (
            <>
              <Button onClick={handleValidate} disabled={isValidating} variant="outline">
                <CheckCircle2 className="w-4 h-4 mr-2" />
                {isValidating ? 'Validating...' : 'Validate'}
              </Button>
              <Button
                onClick={handleCreateDraft}
                disabled={isSaving || !validationResult || !validationResult.ok || invalidSlugs.length > 0}
              >
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? 'Saving...' : 'Create Draft'}
              </Button>
              {savedConfigId && (
                <Button onClick={handlePublish} disabled={isPublishing} variant="default">
                  <Send className="w-4 h-4 mr-2" />
                  {isPublishing ? 'Publishing...' : 'Publish'}
                </Button>
              )}
              <Button onClick={handleCopyJSON} variant="outline">
                <Copy className="w-4 h-4 mr-2" />
                Copy JSON
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Jurisdiction *</label>
              <Select value={jurisdiction} onValueChange={setJurisdiction}>
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
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Purpose *</label>
              <Select value={purpose} onValueChange={(v) => setPurpose(v as 'KYC' | 'AML_RISK')}>
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
        </CardContent>
      </Card>

      {/* Main Content */}
      <div className="h-[calc(100vh-20rem)] grid grid-cols-[minmax(400px,45%)_minmax(500px,55%)] gap-6">
        {/* Left: Chat */}
        <div className="h-full">
          <ChatStudio
            jurisdiction={jurisdiction}
            purpose={purpose}
            onConfigGenerated={handleConfigGenerated}
          />
        </div>

        {/* Right: Preview + Validation */}
        <div className="h-full flex flex-col space-y-4">
          {/* JSON Preview */}
          <Card className="flex-1 flex flex-col min-h-0">
            <CardHeader>
              <CardTitle>Draft Preview</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto">
              {spec ? (
                <pre className="text-xs bg-gray-50 p-4 rounded border overflow-auto">
                  {JSON.stringify(spec, null, 2)}
                </pre>
              ) : (
                <div className="text-center text-gray-500 mt-8">
                  <p>No configuration generated yet</p>
                  <p className="text-xs mt-2">Start a conversation to generate a config</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Validation Panel */}
          {validationResult && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {validationResult.ok ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600" />
                  )}
                  Validation Result
                </CardTitle>
              </CardHeader>
              <CardContent>
                {validationResult.ok ? (
                  <div className="text-sm text-green-600">✓ Configuration is valid</div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-red-600">Errors:</div>
                    <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                      {validationResult.errors.map((error, idx) => (
                        <li key={idx}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Invalid Slugs Panel */}
          {invalidSlugs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  Invalid Field Slugs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-red-600">
                  <p className="font-medium mb-2">The following field slugs are not in the catalog:</p>
                  <ul className="list-disc list-inside space-y-1">
                    {invalidSlugs.map((slug, idx) => (
                      <li key={idx}>{slug}</li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs">Please ensure all fields exist in the field definitions catalog.</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Create Error Panel */}
          {createError && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  Create Draft Error
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm text-red-600">
                  {/* Error message */}
                  <div className="font-medium">{createError}</div>

                  {/* Error details if available */}
                  {createErrorDetails && (
                    <div className="space-y-2">
                      {/* Error code */}
                      {createErrorDetails.error && (
                        <div>
                          <span className="font-semibold">Error Code:</span>{' '}
                          <code className="bg-red-50 px-1 rounded">{createErrorDetails.error}</code>
                        </div>
                      )}

                      {/* Trace ID */}
                      {createErrorDetails.trace_id && (
                        <div>
                          <span className="font-semibold">Trace ID:</span>{' '}
                          <code className="bg-red-50 px-1 rounded text-xs">{createErrorDetails.trace_id}</code>
                        </div>
                      )}

                      {/* Details list */}
                      {createErrorDetails.details && createErrorDetails.details.length > 0 && (
                        <div>
                          <div className="font-semibold mb-1">Details:</div>
                          <ul className="list-disc list-inside space-y-1 ml-2">
                            {createErrorDetails.details.map((detail: any, idx: number) => {
                              if (typeof detail === 'string') {
                                return <li key={idx}>{detail}</li>
                              } else if (detail && typeof detail === 'object') {
                                const field = detail.field || detail.loc || 'unknown'
                                const message = detail.message || detail.msg || JSON.stringify(detail)
                                return (
                                  <li key={idx}>
                                    <span className="font-mono text-xs">{field}:</span> {message}
                                  </li>
                                )
                              }
                              return <li key={idx}>{JSON.stringify(detail)}</li>
                            })}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

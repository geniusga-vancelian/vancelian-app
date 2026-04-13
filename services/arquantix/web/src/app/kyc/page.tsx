'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle, Upload } from 'lucide-react'

interface FieldDefinition {
  id: string
  slug: string
  field_name_en: string
  field_type: string
  category: string
  is_active: boolean
}

interface Step {
  step_id: string
  title_en: string
  description_en?: string
  blocks: Array<{
    block_id: string
    fields: string[]
    layout: string
    required: boolean
    conditions?: any[]
  }>
}

interface NextStepResponse {
  config_id: string
  version: number
  step: Step | null
  completion: {
    completed: boolean
    total_steps: number
    completed_steps: number
  }
}

export default function KYCPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  
  const [personId, setPersonId] = useState<string>('')
  const [jurisdiction, setJurisdiction] = useState<string>('')
  const [fieldDefinitions, setFieldDefinitions] = useState<Map<string, FieldDefinition>>(new Map())
  const [step, setStep] = useState<Step | null>(null)
  const [completion, setCompletion] = useState<{ completed: boolean; total_steps: number; completed_steps: number } | null>(null)
  const [values, setValues] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  // Initialize from URL params
  useEffect(() => {
    const urlPersonId = searchParams?.get('person_id')
    const urlJurisdiction = searchParams?.get('jurisdiction')
    
    if (urlPersonId && urlJurisdiction) {
      setPersonId(urlPersonId)
      setJurisdiction(urlJurisdiction)
    }
  }, [searchParams])

  // Load field definitions once
  useEffect(() => {
    if (personId && jurisdiction) {
      loadFieldDefinitions()
    }
  }, [personId, jurisdiction])

  // Load next step when person_id and jurisdiction are set
  useEffect(() => {
    if (personId && jurisdiction && fieldDefinitions.size > 0) {
      loadNextStep()
    }
  }, [personId, jurisdiction, fieldDefinitions.size])

  const loadFieldDefinitions = async () => {
    try {
      const response = await fetch('/api/client/field-definitions?is_active=true')
      if (!response.ok) {
        throw new Error('Failed to load field definitions')
      }
      const fields: FieldDefinition[] = await response.json()
      const map = new Map<string, FieldDefinition>()
      fields.forEach((field) => {
        map.set(field.slug, field)
      })
      setFieldDefinitions(map)
    } catch (err: any) {
      setError(err.message || 'Failed to load field definitions')
    }
  }

  const loadNextStep = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(
        `/api/client/onboarding/next-step?person_id=${encodeURIComponent(personId)}&jurisdiction=${encodeURIComponent(jurisdiction)}`
      )
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || data.detail || 'Failed to load next step')
      }

      const data: NextStepResponse = await response.json()
      setStep(data.step)
      setCompletion(data.completion)
      
      if (data.step) {
        setProgress(50)
      } else if (data.completion.completed) {
        setProgress(100)
      } else {
        setProgress(0)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load next step')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = () => {
    if (!personId.trim() || !jurisdiction.trim()) {
      setError('Please enter both Person ID and Jurisdiction')
      return
    }
    router.push(`/kyc?person_id=${encodeURIComponent(personId.trim())}&jurisdiction=${encodeURIComponent(jurisdiction.trim())}`)
  }

  const handleSubmit = async () => {
    if (!step) return

    setSubmitting(true)
    setError(null)

    try {
      const response = await fetch('/api/client/onboarding/submit-step', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          person_id: personId,
          jurisdiction,
          step_id: step.step_id,
          values,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || data.detail || 'Failed to submit step')
      }

      const data = await response.json()
      
      // Clear values for next step
      setValues({})
      
      // Update step and completion
      setStep(data.next_step || null)
      setCompletion(data.completion)
      
      if (data.completion.completed) {
        setProgress(100)
      } else if (data.next_step) {
        setProgress(50)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to submit step')
    } finally {
      setSubmitting(false)
    }
  }

  const handleValueChange = (fieldSlug: string, value: any) => {
    setValues((prev) => ({
      ...prev,
      [fieldSlug]: value,
    }))
  }

  const renderField = (fieldSlug: string, required: boolean) => {
    const fieldDef = fieldDefinitions.get(fieldSlug)
    if (!fieldDef) {
      return (
        <div key={fieldSlug} className="text-sm text-gray-500">
          Unknown field: {fieldSlug}
        </div>
      )
    }

    const label = fieldDef.field_name_en
    const value = values[fieldSlug] ?? ''

    switch (fieldDef.field_type) {
      case 'string':
      case 'email':
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldSlug}
              type={fieldDef.field_type === 'email' ? 'email' : 'text'}
              value={value}
              onChange={(e) => handleValueChange(fieldSlug, e.target.value)}
              required={required}
            />
          </div>
        )

      case 'date':
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldSlug}
              type="date"
              value={value}
              onChange={(e) => handleValueChange(fieldSlug, e.target.value)}
              required={required}
            />
          </div>
        )

      case 'datetime':
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldSlug}
              type="datetime-local"
              value={value}
              onChange={(e) => handleValueChange(fieldSlug, e.target.value)}
              required={required}
            />
          </div>
        )

      case 'number':
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldSlug}
              type="number"
              value={value}
              onChange={(e) => handleValueChange(fieldSlug, e.target.value ? Number(e.target.value) : '')}
              required={required}
            />
          </div>
        )

      case 'boolean':
        return (
          <div key={fieldSlug} className="flex items-center space-x-2">
            <Checkbox
              id={fieldSlug}
              checked={value === true || value === 'true'}
              onCheckedChange={(checked) => handleValueChange(fieldSlug, checked)}
              required={required}
            />
            <Label htmlFor={fieldSlug} className="cursor-pointer">
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
          </div>
        )

      case 'enum':
        // For enum, we don't have options in field_definitions, so use Input with placeholder
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldSlug}
              type="text"
              value={value}
              onChange={(e) => handleValueChange(fieldSlug, e.target.value)}
              placeholder="Enter value"
              required={required}
            />
          </div>
        )

      case 'file':
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <div className="space-y-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  handleValueChange(fieldSlug, 'PENDING_UPLOAD')
                }}
                disabled={submitting}
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload
              </Button>
              {value === 'PENDING_UPLOAD' && (
                <Alert variant="default" className="text-sm">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>
                    File upload is not yet implemented. Placeholder value stored.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </div>
        )

      default:
        return (
          <div key={fieldSlug} className="space-y-2">
            <Label htmlFor={fieldSlug}>
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldSlug}
              type="text"
              value={value}
              onChange={(e) => handleValueChange(fieldSlug, e.target.value)}
              required={required}
            />
          </div>
        )
    }
  }

  // Show initial form if no person_id/jurisdiction
  if (!personId || !jurisdiction) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Start KYC Journey</CardTitle>
            <CardDescription>Enter your Person ID and Jurisdiction to begin</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="w-4 h-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="person_id">Person ID *</Label>
              <Input
                id="person_id"
                type="text"
                value={personId}
                onChange={(e) => setPersonId(e.target.value)}
                placeholder="Enter Person ID (UUID)"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jurisdiction">Jurisdiction *</Label>
              <Input
                id="jurisdiction"
                type="text"
                value={jurisdiction}
                onChange={(e) => setJurisdiction(e.target.value)}
                placeholder="e.g., Arquantix_UAE_DIFC_cat4_crowdfunding"
              />
            </div>
            <Button onClick={handleStart} className="w-full">
              Start
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show completion screen
  if (completion?.completed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>KYC Completed</CardTitle>
            <CardDescription>You have successfully completed the KYC process.</CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={100} className="mb-4" />
            <p className="text-sm text-gray-600">
              All required information has been submitted and verified.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show loading state
  if (loading || fieldDefinitions.size === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-400" />
          <p className="text-sm text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Show step form
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="w-4 h-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Step Card */}
        {step && (
          <Card>
            <CardHeader>
              <CardTitle>{step.title_en}</CardTitle>
              {step.description_en && (
                <CardDescription>{step.description_en}</CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-6">
              {step.blocks.map((block) => (
                <Card key={block.block_id} className="bg-gray-50">
                  <CardContent className="pt-6">
                    <div
                      className={
                        block.layout === 'two_columns'
                          ? 'grid grid-cols-1 md:grid-cols-2 gap-4'
                          : 'space-y-4'
                      }
                    >
                      {block.fields.map((fieldSlug) =>
                        renderField(fieldSlug, block.required)
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}

              <div className="flex justify-end pt-4">
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="min-w-[120px]"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    'Continue'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

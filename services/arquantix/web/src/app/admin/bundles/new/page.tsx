'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { ArrowLeft, Plus, Trash2, CheckCircle2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'

interface Instrument {
  id: number
  symbol: string
  name: string | null
  asset_class: string
}

interface Bundle {
  id: number
  name: string
  asset_class: string
  type: string
}

interface Component {
  component_type: 'instrument' | 'bundle'
  instrument_code?: string
  child_bundle_id?: number
  weight: number
  position_order?: number
}

interface ValidationError {
  field: string
  message: string
  index?: number
}

export default function NewBundlePage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [assetClass, setAssetClass] = useState<'crypto' | 'etf' | 'equity' | 'commodities' | 'index' | 'forex' | ''>('')
  const [bundleType, setBundleType] = useState<'fixed_instruments' | 'composite_fixed' | 'dynamic'>('fixed_instruments')
  const [description, setDescription] = useState('')
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [bundles, setBundles] = useState<Bundle[]>([])
  const [components, setComponents] = useState<Component[]>([])
  const [dynamicRuleJson, setDynamicRuleJson] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingInstruments, setIsLoadingInstruments] = useState(false)
  const [isValidatingRule, setIsValidatingRule] = useState(false)
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])

  useEffect(() => {
    if (assetClass) {
      loadInstruments()
      if (bundleType === 'composite_fixed') {
        loadBundles()
      }
    }
  }, [assetClass, bundleType])

  const loadInstruments = async () => {
    if (!assetClass) return

    try {
      setIsLoadingInstruments(true)
      const response = await fetch(`/api/bundles/asset-classes/${assetClass}/instruments`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to load instruments' }))
        const errorMessage = errorData.error || errorData.detail || `Failed to load instruments (${response.status})`
        throw new Error(errorMessage)
      }

      const data = await response.json()
      setInstruments(data || [])
    } catch (error: any) {
      console.error('Load instruments error:', error)
      toast.error(error.message || 'Failed to load instruments')
    } finally {
      setIsLoadingInstruments(false)
    }
  }

  const loadBundles = async () => {
    if (!assetClass) return

    try {
      const response = await fetch(`/api/bundles?asset_class=${assetClass}&active=true`)
      if (!response.ok) {
        throw new Error('Failed to load bundles')
      }

      const data = await response.json()
      setBundles(data)
    } catch (error: any) {
      console.error('Load bundles error:', error)
      toast.error(error.message || 'Failed to load bundles')
    }
  }

  const addComponent = () => {
    setComponents([...components, { component_type: 'instrument', weight: 0 }])
  }

  const removeComponent = (index: number) => {
    setComponents(components.filter((_, i) => i !== index))
  }

  const updateComponent = (index: number, field: keyof Component, value: any) => {
    const updated = [...components]
    updated[index] = { ...updated[index], [field]: value }
    
    // Clear opposite field when type changes
    if (field === 'component_type') {
      if (value === 'instrument') {
        updated[index].child_bundle_id = undefined
      } else {
        updated[index].instrument_code = undefined
      }
    }
    
    setComponents(updated)
  }

  const calculateTotal = () => {
    return components.reduce((sum, comp) => sum + (comp.weight || 0), 0)
  }

  const validateWeights = () => {
    const total = calculateTotal()
    return Math.abs(total - 100) <= 0.01
  }

  const validateRuleJson = async () => {
    if (!dynamicRuleJson.trim()) {
      toast.error('Rule JSON is required for dynamic bundles')
      return
    }

    try {
      setIsValidatingRule(true)
      const parsed = JSON.parse(dynamicRuleJson)
      
      // Basic validation
      if (parsed.type !== 'weights') {
        toast.error('Rule type must be "weights"')
        return
      }
      
      if (!parsed.post || parsed.post.op !== 'normalize_to_one') {
        toast.error('Rule must include post.normalize_to_one')
        return
      }
      
      if (!parsed.items || !Array.isArray(parsed.items) || parsed.items.length === 0) {
        toast.error('Rule must have a non-empty items array')
        return
      }
      
      toast.success('Rule JSON is valid')
    } catch (error: any) {
      toast.error(`Invalid JSON: ${error.message}`)
    } finally {
      setIsValidatingRule(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name || !assetClass) {
      toast.error('Name and Asset Class are required')
      return
    }

    if (bundleType === 'fixed_instruments' && components.some(c => c.component_type === 'bundle')) {
      toast.error('Fixed instruments bundles cannot contain child bundles')
      return
    }

    if (components.length === 0) {
      toast.error('At least one component is required')
      return
    }

    // Validate XOR
    for (const comp of components) {
      if (comp.component_type === 'instrument' && !comp.instrument_code) {
        toast.error('Instrument code is required for instrument components')
        return
      }
      if (comp.component_type === 'bundle' && !comp.child_bundle_id) {
        toast.error('Child bundle is required for bundle components')
        return
      }
      if (comp.weight <= 0) {
        toast.error('All weights must be > 0')
        return
      }
    }

    if (!validateWeights()) {
      toast.error(`Weights must sum to 100% (current: ${calculateTotal().toFixed(2)}%)`)
      return
    }

    if (bundleType === 'dynamic' && !dynamicRuleJson.trim()) {
      toast.error('Dynamic rule JSON is required for dynamic bundles')
      return
    }

    try {
      setIsLoading(true)

      const payload: any = {
        name,
        asset_class: assetClass,
        type: bundleType,
        description: description || null,
        is_active: true,
        components: components.map((comp, idx) => {
          const component: any = {
            component_type: comp.component_type,
            weight: comp.weight,
            position_order: idx,
          }
          
          // Only include the relevant field based on component_type
          if (comp.component_type === 'instrument') {
            if (comp.instrument_code) {
              component.instrument_code = comp.instrument_code
            }
          } else if (comp.component_type === 'bundle') {
            if (comp.child_bundle_id) {
              component.child_bundle_id = comp.child_bundle_id
            }
          }
          
          return component
        }),
      }

      if (bundleType === 'dynamic') {
        try {
          payload.dynamic_rule = {
            rule_type: 'formula_dsl',
            rule_json: JSON.parse(dynamicRuleJson),
          }
        } catch (e) {
          toast.error('Invalid dynamic rule JSON')
          return
        }
      }

      const response = await fetch('/api/bundles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const error = await response.json()
        console.error('Bundle create error response:', error)
        
        // Parse FastAPI 422 validation errors
        if (response.status === 422 && error.detail && Array.isArray(error.detail)) {
          const parsedErrors = parseFastAPIValidationErrors(error.detail)
          setValidationErrors(parsedErrors)
          
          // Also show a toast with summary
          if (parsedErrors.length > 0) {
            const firstError = parsedErrors[0]
            const errorSummary = parsedErrors.length === 1
              ? formatErrorDisplay(firstError)
              : `${parsedErrors.length} validation errors found. See details below.`
            toast.error(errorSummary, { duration: 5000 })
          } else {
            toast.error('Validation failed. Please check the form.')
          }
          
          // Scroll to top to show errors
          window.scrollTo({ top: 0, behavior: 'smooth' })
          return
        }
        
        // Fallback for other error formats
        let errorMessage = 'Failed to create bundle'
        if (error.error) {
          errorMessage = error.error
        } else if (error.detail) {
          if (Array.isArray(error.detail)) {
            errorMessage = error.detail.map((err: any) => 
              `${err.loc?.join('.') || 'field'}: ${err.msg || err.message || 'Invalid'}`
            ).join(', ')
          } else if (typeof error.detail === 'string') {
            errorMessage = error.detail
          }
        }
        
        setValidationErrors([])
        throw new Error(errorMessage)
      }
      
      // Clear validation errors on success
      setValidationErrors([])

      toast.success('Bundle created successfully')
      router.push('/admin/bundles')
    } catch (error: any) {
      console.error('Create bundle error:', error)
      toast.error(error.message || 'Failed to create bundle')
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Parse FastAPI validation errors (422 format)
   * Converts FastAPI error array to structured ValidationError array
   */
  function parseFastAPIValidationErrors(details: any[]): ValidationError[] {
    return details.map((err: any) => {
      const loc = err.loc || []
      const msg = err.msg || err.message || 'Invalid value'
      
      // Extract component index if present (e.g., ["body", "components", 1, "instrument_code"])
      let index: number | undefined
      let field = 'unknown'
      
      // Look for "components" in location and get the next item (should be index)
      const componentsIndex = loc.findIndex((item: any) => item === 'components')
      if (componentsIndex !== -1 && componentsIndex + 1 < loc.length) {
        const potentialIndex = loc[componentsIndex + 1]
        if (typeof potentialIndex === 'number') {
          index = potentialIndex
        }
      }
      
      // Extract field name (last item in loc that's not a number)
      const fieldParts = loc.filter((item: any, idx: number) => {
        // Skip "body", "components", and numeric indices
        if (item === 'body' || item === 'components') return false
        if (idx > 0 && loc[idx - 1] === 'components' && typeof item === 'number') return false
        return true
      })
      field = fieldParts[fieldParts.length - 1] || 'field'
      
      // Format field name nicely (snake_case to Title Case)
      const formattedField = field
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (l: string) => l.toUpperCase())
      
      return {
        field: formattedField,
        message: msg,
        index: index !== undefined ? index : undefined,
      }
    })
  }
  
  /**
   * Format a single error for display
   */
  function formatErrorDisplay(error: ValidationError): string {
    if (error.index !== undefined) {
      return `Component ${error.index + 1}: ${error.field} - ${error.message}`
    }
    return `${error.field}: ${error.message}`
  }

  const total = calculateTotal()
  const isTotalValid = validateWeights()

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link href="/admin/bundles" className="flex items-center text-gray-600 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Bundles
      </Link>

      <h1 className="text-2xl font-bold mb-6">Create Bundle</h1>

      {/* Validation Errors Display */}
      {validationErrors.length > 0 && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start">
            <XCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 mb-2">
                Validation Errors ({validationErrors.length})
              </h3>
              <ul className="space-y-2">
                {validationErrors.map((error, idx) => (
                  <li key={idx} className="text-sm text-red-700">
                    {error.index !== undefined ? (
                      <>
                        <span className="font-medium">Component {error.index + 1}</span>
                        <span className="text-red-600"> • {error.field}</span>
                      </>
                    ) : (
                      <span className="font-medium">{error.field}</span>
                    )}
                    <span className="text-red-600">: {error.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Bundle Name */}
        <div>
          <Label htmlFor="name">Bundle Name *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Crypto Equal Weight"
            required
          />
        </div>

        {/* Description */}
        <div>
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description of this bundle"
            rows={3}
          />
        </div>

        {/* Asset Class */}
        <div>
          <Label htmlFor="assetClass">Asset Class *</Label>
          <Select value={assetClass} onValueChange={(v: any) => setAssetClass(v)}>
            <SelectTrigger>
              <SelectValue placeholder="Select asset class" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="crypto">Crypto</SelectItem>
              <SelectItem value="etf">ETF</SelectItem>
              <SelectItem value="equity">Equity</SelectItem>
              <SelectItem value="commodities">Commodities</SelectItem>
              <SelectItem value="index">Index</SelectItem>
              <SelectItem value="forex">Forex</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Bundle Type */}
        <div>
          <Label htmlFor="bundleType">Bundle Type *</Label>
          <Select value={bundleType} onValueChange={(v: any) => setBundleType(v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="fixed_instruments">Fixed Instruments</SelectItem>
              <SelectItem value="composite_fixed">Composite Fixed (bundles of bundles)</SelectItem>
              <SelectItem value="dynamic">Dynamic (rule-based weights)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Components */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label>Allocations *</Label>
            <div className="flex items-center gap-2">
              <span className={`text-sm ${isTotalValid ? 'text-green-600' : 'text-red-600'}`}>
                Total: {total.toFixed(2)}%
              </span>
              <Button type="button" variant="outline" size="sm" onClick={addComponent}>
                <Plus className="w-4 h-4 mr-1" />
                Add
              </Button>
            </div>
          </div>

          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Item</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Weight %</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500"></th>
                </tr>
              </thead>
              <tbody>
                {components.map((comp, idx) => (
                  <tr key={idx} className="border-t">
                    <td className="px-3 py-2">
                      <Select
                        value={comp.component_type}
                        onValueChange={(v: 'instrument' | 'bundle') => updateComponent(idx, 'component_type', v)}
                        disabled={bundleType === 'fixed_instruments'}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="instrument">Instrument</SelectItem>
                          {bundleType !== 'fixed_instruments' && (
                            <SelectItem value="bundle">Bundle</SelectItem>
                          )}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-3 py-2">
                      {comp.component_type === 'instrument' ? (
                        <Select
                          value={comp.instrument_code || ''}
                          onValueChange={(v) => updateComponent(idx, 'instrument_code', v)}
                          disabled={isLoadingInstruments}
                        >
                          <SelectTrigger className="w-48">
                            <SelectValue placeholder="Select instrument" />
                          </SelectTrigger>
                          <SelectContent>
                            {instruments.map((inst) => (
                              <SelectItem key={inst.id} value={inst.symbol}>
                                {inst.symbol} {inst.name && `(${inst.name})`}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Select
                          value={comp.child_bundle_id?.toString() || ''}
                          onValueChange={(v) => updateComponent(idx, 'child_bundle_id', parseInt(v))}
                        >
                          <SelectTrigger className="w-48">
                            <SelectValue placeholder="Select bundle" />
                          </SelectTrigger>
                          <SelectContent>
                            {bundles.map((bundle) => (
                              <SelectItem key={bundle.id} value={bundle.id.toString()}>
                                {bundle.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        max="100"
                        value={comp.weight}
                        onChange={(e) => updateComponent(idx, 'weight', parseFloat(e.target.value) || 0)}
                        className="w-24"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeComponent(idx)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {components.length === 0 && (
            <p className="text-sm text-gray-500 mt-2">No components added yet. Click "Add" to add one.</p>
          )}

          {!isTotalValid && components.length > 0 && (
            <p className="text-sm text-red-600 mt-2">
              Weights must sum to exactly 100% (current: {total.toFixed(2)}%)
            </p>
          )}
        </div>

        {/* Dynamic Rule JSON */}
        {bundleType === 'dynamic' && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>Dynamic Rule JSON *</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={validateRuleJson}
                disabled={isValidatingRule || !dynamicRuleJson.trim()}
              >
                Validate Rule
              </Button>
            </div>
            <Textarea
              value={dynamicRuleJson}
              onChange={(e) => setDynamicRuleJson(e.target.value)}
              placeholder='{"type": "weights", "items": [...], "post": {"op": "normalize_to_one"}}'
              rows={12}
              className="font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Rule must include post.normalize_to_one for explicit normalization
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading || !isTotalValid}>
            {isLoading ? 'Creating...' : 'Create Bundle'}
          </Button>
        </div>
      </form>
    </div>
  )
}

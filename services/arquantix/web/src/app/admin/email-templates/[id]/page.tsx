'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import Link from 'next/link'
import { toastSuccess, toastError } from '@/lib/admin/toast'

interface EmailTemplateEntity {
  id: string
  slug: string
  name: string
  description: string | null
  theme: string
  status: 'DRAFT' | 'VALIDATED'
  heroPolicy: 'REQUIRED' | 'OPTIONAL'
  headerModuleId: string
  footerModuleId: string
  bodyStarterModuleId: string | null
  fixedModuleIds: any[] | null
  bodyTemplate: any
  lockPolicy: any
  headerModule: {
    id: string
    slug: string
    name: string
    moduleType: string
    status: string
  }
  footerModule: {
    id: string
    slug: string
    name: string
    moduleType: string
    status: string
  }
  updatedAt: string
  createdAt: string
}

export default function EmailTemplateDetailPage() {
  const router = useRouter()
  const params = useParams()
  const templateId = (params?.id as string | undefined) ?? ''

  const [template, setTemplate] = useState<EmailTemplateEntity | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isValidating, setIsValidating] = useState(false)

  useEffect(() => {
    if (templateId) {
      loadTemplate()
    }
  }, [templateId])

  const loadTemplate = async () => {
    try {
      const response = await fetch(`/api/admin/email-templates/${templateId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch template')
      }
      const data = await response.json()
      setTemplate(data)
    } catch (error) {
      console.error('Error loading template:', error)
      toastError('Failed to load template')
    } finally {
      setIsLoading(false)
    }
  }

  const handleValidate = async () => {
    if (!template) return

    setIsValidating(true)
    try {
      const response = await fetch(`/api/admin/email-templates/${templateId}/validate`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to validate')
      }

      toastSuccess('Template validated. Editing is now locked.')
      loadTemplate() // Reload to get updated status
    } catch (error) {
      console.error('Error validating template:', error)
      toastError(error instanceof Error ? error.message : 'Failed to validate template')
    } finally {
      setIsValidating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading template...</div>
      </div>
    )
  }

  if (!template) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <div className="text-gray-500 mb-4">Template not found</div>
        <Link
          href="/admin/email-templates"
          className="text-gray-900 hover:text-gray-700 flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to templates
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/admin/email-templates"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{template.name}</h1>
            <p className="text-sm text-gray-500">{template.slug}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 text-sm font-medium rounded ${
              template.status === 'VALIDATED'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}
          >
            {template.status}
          </span>
          {template.status === 'DRAFT' && (
            <button
              onClick={handleValidate}
              disabled={isValidating}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {isValidating ? 'Validating...' : 'Validate Template'}
            </button>
          )}
        </div>
      </div>

      {/* Template Details */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
        {/* Basic Info */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Template Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ID</label>
              <div className="text-sm text-gray-900 font-mono">{template.id}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
              <div className="text-sm text-gray-900">{template.slug}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Theme</label>
              <div className="text-sm text-gray-900">{template.theme}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hero Policy</label>
              <div className="text-sm text-gray-900">
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                  {template.heroPolicy}
                </span>
              </div>
            </div>
            {template.description && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <div className="text-sm text-gray-900">{template.description}</div>
              </div>
            )}
          </div>
        </div>

        {/* Modules */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Modules</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Header Module</label>
              <Link
                href={`/admin/email-modules/${template.headerModule.id}`}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                {template.headerModule.name}
                <span className="text-xs text-gray-500">({template.headerModule.slug})</span>
              </Link>
              <div className="text-xs text-gray-500 mt-1">
                Type: {template.headerModule.moduleType} | Status: {template.headerModule.status}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Footer Module</label>
              <Link
                href={`/admin/email-modules/${template.footerModule.id}`}
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                {template.footerModule.name}
                <span className="text-xs text-gray-500">({template.footerModule.slug})</span>
              </Link>
              <div className="text-xs text-gray-500 mt-1">
                Type: {template.footerModule.moduleType} | Status: {template.footerModule.status}
              </div>
            </div>
            {template.bodyStarterModuleId && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Body Starter Module</label>
                <div className="text-sm text-gray-600">ID: {template.bodyStarterModuleId}</div>
                <div className="text-xs text-gray-500 mt-1">
                  This module initializes the body spec when creating a new email with this template
                </div>
              </div>
            )}
            {template.fixedModuleIds && Array.isArray(template.fixedModuleIds) && template.fixedModuleIds.length > 0 && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Fixed Modules</label>
                <div className="text-sm text-gray-600">
                  {template.fixedModuleIds.map((id: string, idx: number) => (
                    <span key={idx} className="mr-2 font-mono text-xs">{id}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Body Template Structure */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Body Template Structure</h2>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="space-y-4">
              {template.bodyTemplate?.core_blocks && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Core Blocks</label>
                  <div className="space-y-2">
                    {template.bodyTemplate.core_blocks.map((block: any, idx: number) => (
                      <div key={idx} className="text-sm bg-white p-2 rounded border border-gray-200">
                        <span className="font-medium">{block.type}</span>
                        {block.variant && <span className="text-gray-500"> ({block.variant})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {template.bodyTemplate?.optional_slots && Object.keys(template.bodyTemplate.optional_slots).length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Optional Slots</label>
                  <div className="space-y-2">
                    {Object.entries(template.bodyTemplate.optional_slots).map(([key, value]: [string, any]) => (
                      <div key={key} className="text-sm bg-white p-2 rounded border border-gray-200">
                        <span className="font-medium">{key}</span>
                        {value.max && <span className="text-gray-500"> (max: {value.max})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Lock Policy */}
        {template.lockPolicy && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Lock Policy</h2>
            <div className="bg-gray-50 rounded-lg p-4">
              <pre className="text-xs text-gray-700 overflow-auto">
                {JSON.stringify(template.lockPolicy, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="pt-4 border-t border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Created</label>
              <div className="text-sm text-gray-500">
                {new Date(template.createdAt).toLocaleString()}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Updated</label>
              <div className="text-sm text-gray-500">
                {new Date(template.updatedAt).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      {template.status === 'VALIDATED' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            This template is validated and its structure is locked. It can be used in the AI Email Builder.
          </p>
        </div>
      )}
    </div>
  )
}










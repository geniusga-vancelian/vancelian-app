'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChatStudio } from '@/components/ai-email/ChatStudio'
import { EmailOutput } from '@/components/ai-email/EmailOutput'
import { BlockEditor } from '@/components/ai-email/BlockEditor/BlockEditor'
import { EmailSpec } from '@/components/ai-email/types'
import { buildMjml } from '@/lib/ai-email/buildMjml'
import { toastSuccess, toastError } from '@/lib/admin/toast'

type EditMode = 'ai' | 'manual'

export default function AIEmailBuilderPage() {
  const router = useRouter()
  const [spec, setSpec] = useState<EmailSpec | null>(null)
  const [mjml, setMjml] = useState('')
  const [html, setHtml] = useState('')
  const [editMode, setEditMode] = useState<EditMode>('ai')
  const [templateId, setTemplateId] = useState<string>('welcome_v1')
  const [templateSource, setTemplateSource] = useState<'hardcoded' | 'db'>('hardcoded')
  const [headerModuleName, setHeaderModuleName] = useState<string | undefined>()
  const [footerModuleName, setFooterModuleName] = useState<string | undefined>()
  const [isSaving, setIsSaving] = useState(false)

  const handleEmailGenerated = (
    newSpec: EmailSpec,
    newMjml: string,
    newHtml: string,
    assistantText: string
  ) => {
    // Log in dev mode
    if (process.env.NODE_ENV === 'development') {
      console.log('[AI Email Builder] Email generated:', {
        hasSpec: !!newSpec,
        hasMjml: !!newMjml,
        hasHtml: !!newHtml,
        htmlLength: newHtml?.length || 0,
        htmlStart: newHtml?.substring(0, 100) || 'no html',
      })
    }
    
    setSpec(newSpec)
    setMjml(newMjml)
    setHtml(newHtml || '') // Ensure html is never null/undefined
  }

  const handleManualUpdate = async (updatedSpec: EmailSpec) => {
    setSpec(updatedSpec)
    // Rebuild MJML and HTML
    try {
      const newMjml = buildMjml(updatedSpec)
      // Compile MJML via API route (server-side)
      const response = await fetch('/api/ai/email/compile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mjml: newMjml }),
      })

      if (!response.ok) {
        throw new Error('Failed to compile MJML')
      }

      const { html: newHtml } = await response.json()
      setMjml(newMjml)
      setHtml(newHtml)
    } catch (error) {
      console.error('Failed to rebuild email:', error)
    }
  }

  const handleTemplateChange = async (newTemplateId: string, newTemplateSource: 'hardcoded' | 'db') => {
    setTemplateId(newTemplateId)
    setTemplateSource(newTemplateSource)
    
    // If DB template, load module names
    if (newTemplateSource === 'db') {
      try {
        const response = await fetch(`/api/admin/email-templates?status=VALIDATED`)
        if (response.ok) {
          const templates = await response.json()
          // For DB templates, templateId is the slug
          const template = templates.find((t: any) => t.slug === newTemplateId || t.id === newTemplateId)
          if (template) {
            setHeaderModuleName(template.headerModule?.name || 'header_default')
            setFooterModuleName(template.footerModule?.name || 'footer_default')
          } else {
            // Fallback names if template not found
            setHeaderModuleName('header_default')
            setFooterModuleName('footer_default')
          }
        }
      } catch (error) {
        console.error('Failed to load template details:', error)
        // Fallback on error
        setHeaderModuleName('header_default')
        setFooterModuleName('footer_default')
      }
    } else {
      setHeaderModuleName(undefined)
      setFooterModuleName(undefined)
    }
  }

  const handleSaveDraft = async () => {
    if (!spec) {
      toastError('No email to save')
      return
    }

    setIsSaving(true)
    try {
      const name = `Email - ${new Date().toLocaleDateString()}`
      const response = await fetch('/api/admin/emails', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          templateId: templateId || 'welcome_v1',
          locale: spec.locale || 'fr',
          spec: {
            ...spec,
            theme: spec.theme || 'arquantix_v1',
            preheader: spec.preheader === undefined || spec.preheader === '' ? null : spec.preheader,
            locale: spec.locale || 'fr',
          },
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        console.error('Save draft error response:', error)
        console.error('Response status:', response.status)
        // Show detailed error message
        const errorMessage = error.details 
          ? `${error.error || error.message}\nDetails: ${JSON.stringify(error.details, null, 2)}`
          : error.error || error.message || 'Failed to save draft'
        throw new Error(errorMessage)
      }

      const email = await response.json()
      toastSuccess('Draft saved successfully')
      router.push(`/admin/emails/${email.id}`)
    } catch (error) {
      console.error('Error saving draft:', error)
      toastError(error instanceof Error ? error.message : 'Failed to save draft')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header with Save Draft */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Edit Mode:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setEditMode('ai')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                editMode === 'ai'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              AI Copilot
            </button>
            <button
              onClick={() => setEditMode('manual')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                editMode === 'manual'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Manual Edit
            </button>
          </div>
        </div>
        {spec && (
          <button
            onClick={handleSaveDraft}
            disabled={isSaving}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? 'Saving...' : 'Save Draft'}
          </button>
        )}
      </div>

      {editMode === 'ai' ? (
        <div className="h-[calc(100vh-12rem)] grid grid-cols-[minmax(320px,45%)_minmax(420px,55%)] gap-6">
          <div className="h-full">
            <ChatStudio 
              onEmailGenerated={handleEmailGenerated}
              onTemplateChange={handleTemplateChange}
            />
          </div>
          <div className="h-full">
            <EmailOutput 
              spec={spec} 
              mjml={mjml} 
              html={html}
              templateSource={templateSource}
              templateId={templateId}
              headerModuleName={headerModuleName}
              footerModuleName={footerModuleName}
            />
          </div>
        </div>
      ) : (
        <div className="h-[calc(100vh-12rem)] grid grid-cols-[minmax(400px,50%)_minmax(400px,50%)] gap-6">
          <div className="h-full overflow-y-auto">
            {spec ? (
              <BlockEditor spec={spec} onUpdate={handleManualUpdate} />
            ) : (
              <div className="text-center text-gray-500 mt-8">
                <p>No email loaded. Switch to AI Copilot mode to generate an email first.</p>
              </div>
            )}
          </div>
          <div className="h-full">
            <EmailOutput 
              spec={spec} 
              mjml={mjml} 
              html={html}
              templateSource={templateSource}
              templateId={templateId}
              headerModuleName={headerModuleName}
              footerModuleName={footerModuleName}
            />
          </div>
        </div>
      )}
    </div>
  )
}


'use client'

import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { EmailSpec } from './types'
import { HtmlViewer } from './HtmlViewer'

type ViewMode = 'desktop' | 'mobile' | 'code'

interface EmailOutputProps {
  spec: EmailSpec | null
  mjml: string
  html: string
  templateSource?: 'hardcoded' | 'db'
  templateId?: string
  headerModuleName?: string
  footerModuleName?: string
}

export function EmailOutput({ 
  spec, 
  mjml, 
  html, 
  templateSource, 
  templateId,
  headerModuleName,
  footerModuleName,
}: EmailOutputProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('desktop')
  const [copied, setCopied] = useState<'html' | 'mjml' | null>(null)

  const handleCopy = async (type: 'html' | 'mjml') => {
    const text = type === 'html' ? html : mjml
    try {
      await navigator.clipboard.writeText(text)
      setCopied(type)
      setTimeout(() => setCopied(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  if (!spec) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500">No email generated yet. Start a conversation to create an email.</p>
      </div>
    )
  }

  // Ensure we have valid HTML
  const displayHtml = html && html.trim() ? html : 
    '<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Email Preview</title></head><body style="padding:40px;font-family:Arial,sans-serif;margin:0;background:#f4f4f4;"><div style="max-width:600px;margin:0 auto;background:white;padding:20px;border-radius:8px;"><p style="color:#666;">Email preview will appear here once generated.</p></div></body></html>'

  return (
    <div className="h-full flex flex-col bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">Email Output</h2>
        </div>

        {/* Badges showing module vs AI sources (only for DB templates) */}
        {templateSource === 'db' && (headerModuleName || footerModuleName) && (
          <div className="mb-3 flex flex-wrap gap-2 text-xs">
            {headerModuleName && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                Header: {headerModuleName} (module)
              </span>
            )}
            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded">
              Body: AI
            </span>
            {footerModuleName && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                Footer: {footerModuleName} (module)
              </span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          {viewMode === 'code' && (
            <div className="flex gap-2">
              <button
                onClick={() => handleCopy('mjml')}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-white rounded transition-colors"
              >
                {copied === 'mjml' ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>Copy MJML</span>
                  </>
                )}
              </button>
              <button
                onClick={() => handleCopy('html')}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-white rounded transition-colors"
              >
                {copied === 'html' ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>Copy HTML</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* View mode switcher */}
        <div className="flex gap-2">
          {(['desktop', 'mobile', 'code'] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-4 py-1.5 text-sm font-medium rounded transition-colors ${
                viewMode === mode
                  ? 'bg-gray-900 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>

        {/* Subject & Preheader */}
        <div className="mt-3 space-y-1">
          <div className="text-sm">
            <span className="font-medium text-gray-700">Subject:</span>
            <span className="ml-2 text-gray-900">{spec.subject}</span>
          </div>
          {spec.preheader && (
            <div className="text-sm">
              <span className="font-medium text-gray-700">Preheader:</span>
              <span className="ml-2 text-gray-600">{spec.preheader}</span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto bg-gray-50 p-4">
        {viewMode === 'code' ? (
          <HtmlViewer html={html} title="HTML Code" />
        ) : (
          <div className="flex justify-center">
            <div
              className={`bg-white shadow-lg rounded ${
                viewMode === 'desktop' ? 'w-full max-w-[640px]' : 'w-full max-w-[375px]'
              }`}
            >
              {displayHtml ? (
                <iframe
                  key={`email-preview-${viewMode}`}
                  srcDoc={displayHtml}
                  sandbox="allow-same-origin"
                  className="w-full border-0 rounded"
                  style={{
                    height: 'calc(100vh - 300px)',
                    minHeight: '600px',
                    backgroundColor: '#f4f4f4',
                    display: 'block',
                  }}
                  title="Email Preview"
                  onLoad={(e) => {
                    // Debug log in dev mode
                    if (process.env.NODE_ENV === 'development') {
                      console.log('[EmailOutput] iframe loaded successfully', {
                        viewMode,
                        hasHtml: !!html,
                        htmlLength: html?.length || 0,
                        displayHtmlLength: displayHtml?.length || 0,
                      })
                    }
                  }}
                  onError={(e) => {
                    console.error('[EmailOutput] iframe error:', e)
                  }}
                />
              ) : (
                <div className="flex items-center justify-center h-full min-h-[600px] bg-gray-50">
                  <p className="text-gray-500">Unable to load email preview. Please check the HTML output.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


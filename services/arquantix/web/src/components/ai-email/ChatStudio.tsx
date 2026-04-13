'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, RotateCcw } from 'lucide-react'
import { VoiceRecorder } from './VoiceRecorder'
import { composeEmail, listEmailTemplates } from './api'
import { EmailSpec, EmailTemplate } from './types'
import { toastError, toastInfo } from '@/lib/admin/toast'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatStudioProps {
  onEmailGenerated: (spec: EmailSpec, mjml: string, html: string, assistantText: string) => void
  onTemplateChange?: (templateId: string, source: 'hardcoded' | 'db') => void
}

export function ChatStudio({ onEmailGenerated, onTemplateChange }: ChatStudioProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [previousSpec, setPreviousSpec] = useState<EmailSpec | null>(null)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('arquantix_ugg_v1')
  const [lockStructure, setLockStructure] = useState<boolean>(true)
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load templates on mount
  useEffect(() => {
    const loadTemplates = async () => {
      setIsLoadingTemplates(true)
      try {
        const loadedTemplates = await listEmailTemplates()
        if (loadedTemplates && loadedTemplates.length > 0) {
          setTemplates(loadedTemplates)
          if (!selectedTemplateId) {
            setSelectedTemplateId(loadedTemplates[0].id)
          }
        } else {
          // Fallback to UGG template if empty array
          const fallbackTemplates = [
            { id: 'arquantix_ugg_v1', name: 'Arquantix UGG v1', description: 'Single golden template based on UGG-style MJML. AI generates JSON only.', locked: false, source: 'hardcoded' as const },
          ]
          setTemplates(fallbackTemplates)
          if (!selectedTemplateId) {
            setSelectedTemplateId(fallbackTemplates[0].id)
          }
        }
      } catch (error) {
        console.error('Failed to load templates:', error)
        // Fallback to UGG template only
        const fallbackTemplates = [
          { id: 'arquantix_ugg_v1', name: 'Arquantix UGG v1', description: 'Single golden template based on UGG-style MJML. AI generates JSON only.', locked: false, source: 'hardcoded' as const },
        ]
        setTemplates(fallbackTemplates)
        if (!selectedTemplateId) {
          setSelectedTemplateId(fallbackTemplates[0].id)
        }
      } finally {
        setIsLoadingTemplates(false)
      }
    }
    loadTemplates()
  }, [])

  // Notify parent when template changes
  useEffect(() => {
    const selectedTemplate = templates.find((t) => t.id === selectedTemplateId)
    const source = selectedTemplate?.source || 'hardcoded'
    onTemplateChange?.(selectedTemplateId, source)
  }, [selectedTemplateId, templates, onTemplateChange])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      // Determine template source
      const selectedTemplate = templates.find((t) => t.id === selectedTemplateId)
      const templateSource = selectedTemplate?.source || 'hardcoded'

      const response = await composeEmail({
        prompt: userMessage,
        locale: 'en',
        previous_spec: previousSpec || undefined,
        templateId: selectedTemplateId,
        templateSource: templateSource,
        lockStructure: lockStructure,
      })

      let assistantMessage = response.assistant_text
      
      // Append warnings if any
      if (response.warnings && response.warnings.length > 0) {
        assistantMessage += '\n\n⚠️ Warnings:\n' + response.warnings.map((w: string) => `• ${w}`).join('\n')
        // Also show first warning as toast
        toastInfo(response.warnings[0])
      }
      
      setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage }])
      setPreviousSpec(response.spec)
      
      // Log HTML in dev mode for debugging
      if (process.env.NODE_ENV === 'development') {
        console.log('[ChatStudio] Email generated:', {
          hasSpec: !!response.spec,
          hasMjml: !!response.mjml,
          hasHtml: !!response.html,
          htmlLength: response.html?.length || 0,
          htmlPreview: response.html?.substring(0, 200) || 'no html',
        })
      }
      
      onEmailGenerated(response.spec, response.mjml, response.html, response.assistant_text)
    } catch (error) {
      console.error('Compose error:', error)
      
      // Extract error message properly
      let errorMessage = 'Failed to generate email'
      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (error && typeof error === 'object') {
        // Try to extract message from error object
        errorMessage = (error as any).message || (error as any).error || JSON.stringify(error)
      }
      
      toastError(errorMessage)
      
      // Show detailed error in chat if it's a backend error
      const isBackendError = errorMessage.toLowerCase().includes('backend') || errorMessage.toLowerCase().includes('unavailable')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: isBackendError
          ? `❌ Error: ${errorMessage}\n\nPlease ensure the FastAPI backend is running and accessible.`
          : `❌ Error: ${errorMessage}\n\nPlease try again or check the console for details.`
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleTranscript = (transcript: string) => {
    setInput(transcript)
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleReset = () => {
    setPreviousSpec(null)
    setMessages([])
    // Keep selected template
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-lg border border-gray-200">
      {/* Template Selector */}
      <div className="border-b border-gray-200 p-4 space-y-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Template
            </label>
            {isLoadingTemplates ? (
              <div className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-500 bg-gray-50">
                Loading templates...
              </div>
            ) : (
              <select
                value={selectedTemplateId || ''}
                onChange={(e) => {
                  const newId = e.target.value
                  setSelectedTemplateId(newId)
                  const selectedTemplate = templates.find((t) => t.id === newId)
                  const source = selectedTemplate?.source || 'hardcoded'
                  onTemplateChange?.(newId, source)
                }}
                disabled={isLoading || templates.length === 0}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50"
              >
                {templates.length === 0 ? (
                  <option value="">No templates available</option>
                ) : (
                  templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} {t.source === 'db' ? '(DB)' : ''}
                    </option>
                  ))
                )}
              </select>
            )}
            {templates.find((t) => t.id === selectedTemplateId)?.description && (
              <p className="text-xs text-gray-500 mt-1">
                {templates.find((t) => t.id === selectedTemplateId)?.description}
              </p>
            )}
            {templates.length > 0 && templates.filter(t => t.source === 'db').length === 0 && (
              <p className="text-xs text-amber-600 mt-1">
                ⚠️ No DB templates found. Run <code className="bg-amber-50 px-1 rounded">npm run seed:email</code> to create default templates.
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={lockStructure}
                onChange={(e) => setLockStructure(e.target.checked)}
                disabled={isLoading}
                className="rounded border-gray-300"
              />
              <span>Structure locked</span>
            </label>
            <button
              onClick={handleReset}
              disabled={isLoading}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
              title="Reset to template"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-sm">Start a conversation to create an email</p>
            <p className="text-xs mt-2">Try: "Create a welcome email for new users"</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-end gap-2">
          <VoiceRecorder onTranscript={handleTranscript} disabled={isLoading} />
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe the email you want to create..."
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent resize-none"
              disabled={isLoading}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="flex items-center justify-center w-10 h-10 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}

